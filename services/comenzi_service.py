import datetime
from core.database import DatabaseManager

class ComenziService:
    @staticmethod
    def get_produse_active():
        """Catalogul de produse active afisat vanzatorului la tejghea."""
        db = DatabaseManager.get_instance()
        return db.query("""
            SELECT p.id_produs, p.denumire, p.pret_vanzare, p.id_reteta, r.portii_baza
            FROM PRODUSE p
            JOIN RETETE r ON p.id_reteta = r.id_reteta
            WHERE p.activ = 1
            ORDER BY p.denumire ASC;
        """)

    @staticmethod
    def cauta_client(telefon: str):
        db = DatabaseManager.get_instance()
        return db.query_one("SELECT * FROM CLIENTI WHERE telefon = ?;", (telefon.strip(),))

    @staticmethod
    def get_clienti():
        db = DatabaseManager.get_instance()
        return db.query("SELECT * FROM CLIENTI ORDER BY nume ASC;")

    @staticmethod
    def adauga_sau_preia_client(nume: str, telefon: str):
        db = DatabaseManager.get_instance()
        telefon = telefon.strip()
        client = db.query_one("SELECT * FROM CLIENTI WHERE telefon = ?;", (telefon,))
        if client:
            return client['id_client']
        res = db.execute("INSERT INTO CLIENTI (nume, telefon) VALUES (?, ?);", (nume.strip(), telefon))
        return res['last_id']

    @staticmethod
    def plasare_comanda_tranzactionala(client_data: dict, produse_items: list, tip: str,
                                       text_personalizat: str, model_dorit: str,
                                       data_livrare: str, id_vanzator: int = 3):
        """
        Tranzactia de plasare comanda cu VERIFICARE ATOMICA a stocurilor tehnologice:
        Daca un singur ingredient este insuficient in INGREDIENTE.stoc_curent,
        tranzactia se anuleaza cu ROLLBACK si nu se salveaza nicio inregistrare!
        """
        db = DatabaseManager.get_instance()

        if not produse_items:
            return {"success": False, "error": "Comanda trebuie să conțină cel puțin un produs!"}

        if not data_livrare:
            data_livrare = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        def _tx(cursor):
            # 1. Identificare sau creare client
            id_client = client_data.get('id_client')
            if not id_client:
                tel = client_data.get('telefon', '').strip()
                cursor.execute("SELECT id_client FROM CLIENTI WHERE telefon = ?;", (tel,))
                row = cursor.fetchone()
                if row:
                    id_client = row[0]
                else:
                    cursor.execute("INSERT INTO CLIENTI (nume, telefon) VALUES (?, ?);",
                                   (client_data.get('nume', 'Client Tejghea').strip(), tel))
                    id_client = cursor.lastrowid

            # 2. Calculam totalul de materii prime necesare din fisele tehnologice
            necesar_ingrediente = {} # {id_ingredient: {"necesar": float, "nume": str, "um": str}}

            for item in produse_items:
                id_produs = int(item['id_produs'])
                cant_produs = int(item['cantitate'])

                # Aflam reteta asociata produsului
                cursor.execute("SELECT id_reteta, denumire FROM PRODUSE WHERE id_produs = ?;", (id_produs,))
                prod_row = cursor.fetchone()
                if not prod_row:
                    raise ValueError(f"Produsul cu ID {id_produs} nu există!")
                id_reteta = prod_row[0]

                # Ingredientele din reteta
                cursor.execute("""
                    SELECT ri.id_ingredient, i.nume, ri.cantitate, i.unitate_masura, i.stoc_curent
                    FROM RETETE_INGREDIENTE ri
                    JOIN INGREDIENTE i ON ri.id_ingredient = i.id_ingredient
                    WHERE ri.id_reteta = ?;
                """, (id_reteta,))
                ing_rows = cursor.fetchall()

                for ing in ing_rows:
                    ing_id = ing[0]
                    ing_nume = ing[1]
                    cant_per_buc = float(ing[2])
                    ing_um = ing[3]
                    stoc_disp = float(ing[4])

                    cant_totala = cant_per_buc * cant_produs
                    if ing_id not in necesar_ingrediente:
                        necesar_ingrediente[ing_id] = {
                            "nume": ing_nume,
                            "um": ing_um,
                            "necesar": 0.0,
                            "stoc_curent": stoc_disp
                        }
                    necesar_ingrediente[ing_id]["necesar"] += cant_totala

            # 3. Verificare atomica: stoc_curent >= necesar
            for ing_id, info in necesar_ingrediente.items():
                if info["stoc_curent"] < info["necesar"]:
                    # ROLLBACK automat prin ridicarea exceptiei
                    deficit = round(info["necesar"] - info["stoc_curent"], 3)
                    raise ValueError(
                        f"Stoc tehnologic insuficient pentru '{info['nume']}'! "
                        f"Necesar: {round(info['necesar'], 3)} {info['um']}, "
                        f"Disponibil: {round(info['stoc_curent'], 3)} {info['um']} "
                        f"(Deficit: {deficit} {info['um']}). Comanda a fost refuzată."
                    )

            # 4. Inserare comanda
            cursor.execute("""
                INSERT INTO COMENZI (data_livrare, tip, stare, text_personalizat, model_dorit, id_client)
                VALUES (?, ?, 'preluata', ?, ?, ?);
            """, (data_livrare, tip, text_personalizat, model_dorit, id_client))
            id_comanda = cursor.lastrowid

            # 5. Inserare detalii comanda si sarcini de productie pentru cofetari
            cursor.execute("SELECT id_utilizator FROM UTILIZATORI WHERE rol = 'cofetar' LIMIT 1;")
            cofetar_row = cursor.fetchone()
            id_cofetar_alocat = cofetar_row[0] if cofetar_row else 2

            data_prod = data_livrare[:10] if len(data_livrare) >= 10 else datetime.date.today().strftime('%Y-%m-%d')

            for item in produse_items:
                cursor.execute("""
                    INSERT INTO COMENZI_DETALII (id_comanda, id_produs, cantitate)
                    VALUES (?, ?, ?);
                """, (id_comanda, int(item['id_produs']), int(item['cantitate'])))
                id_detaliu = cursor.lastrowid

                # Sarcină de producție automată pentru laborator
                cursor.execute("""
                    INSERT INTO PRODUCTIE (stare, data_productie, id_detaliu, id_comanda, id_utilizator)
                    VALUES ('in_asteptare', ?, ?, ?, ?);
                """, (data_prod, id_detaliu, id_comanda, id_cofetar_alocat))

            return {"id_comanda": id_comanda, "mesaj": "Comanda a fost salvată cu succes și transmisă în laborator!"}

        return db.execute_transaction(_tx)

    @staticmethod
    def get_comenzi():
        """Lista tuturor comenzilor cu valoarea totala calculata (Interogarea 4.2)."""
        db = DatabaseManager.get_instance()
        return db.query("""
            SELECT c.id_comanda, c.data_livrare, c.tip, c.stare, c.text_personalizat, c.model_dorit,
                   cl.id_client, cl.nume AS client, cl.telefon AS telefon_client,
                   COALESCE(SUM(cd.cantitate * p.pret_vanzare), 0) AS valoare_totala,
                   COUNT(cd.id_detaliu) AS numar_articole
            FROM COMENZI c
            JOIN CLIENTI cl ON c.id_client = cl.id_client
            LEFT JOIN COMENZI_DETALII cd ON c.id_comanda = cd.id_comanda
            LEFT JOIN PRODUSE p ON cd.id_produs = p.id_produs
            GROUP BY c.id_comanda
            ORDER BY c.id_comanda DESC;
        """)

    @staticmethod
    def get_comanda_detalii(id_comanda: int):
        """Interogarea 3.4: Detalii comanda pentru productie."""
        db = DatabaseManager.get_instance()
        comanda = db.query_one("""
            SELECT c.id_comanda, c.data_livrare, c.tip, c.stare, c.text_personalizat, c.model_dorit,
                   cl.nume AS client, cl.telefon AS telefon_client
            FROM COMENZI c
            JOIN CLIENTI cl ON c.id_client = cl.id_client
            WHERE c.id_comanda = ?;
        """, (id_comanda,))

        if not comanda:
            return None

        articole = db.query("""
            SELECT cd.id_detaliu, p.id_produs, p.denumire AS produs, cd.cantitate, p.pret_vanzare,
                   (cd.cantitate * p.pret_vanzare) AS subtotal
            FROM COMENZI_DETALII cd
            JOIN PRODUSE p ON cd.id_produs = p.id_produs
            WHERE cd.id_comanda = ?;
        """, (id_comanda,))

        comanda['articole'] = articole
        comanda['valoare_totala'] = sum(a['subtotal'] for a in articole)
        return comanda
