import datetime
from core.database import DatabaseManager

class ProductieService:
    @staticmethod
    def get_sarcini_zi(data_productie: str = None):
        """Interogarea 3.1: Tabloul de Productie al zilei."""
        db = DatabaseManager.get_instance()
        params = []
        sql = """
            SELECT p.id_sarcina, p.stare AS stare_sarcina, prod.id_produs, prod.denumire AS produs,
                   cd.cantitate, c.id_comanda, cl.nume AS client, c.text_personalizat, c.model_dorit,
                   p.data_productie, u.nume AS cofetar, prod.id_reteta
            FROM PRODUCTIE p
            JOIN COMENZI_DETALII cd ON p.id_detaliu = cd.id_detaliu
            JOIN PRODUSE prod ON cd.id_produs = prod.id_produs
            JOIN COMENZI c ON p.id_comanda = c.id_comanda
            JOIN CLIENTI cl ON c.id_client = cl.id_client
            JOIN UTILIZATORI u ON p.id_utilizator = u.id_utilizator
        """
        if data_productie:
            sql += " WHERE p.data_productie = ? "
            params.append(data_productie)

        sql += " ORDER BY CASE p.stare WHEN 'in_lucru' THEN 1 WHEN 'in_asteptare' THEN 2 ELSE 3 END, p.id_sarcina ASC;"
        return db.query(sql, params)

    @staticmethod
    def schimba_stare_sarcina(id_sarcina: int, noua_stare: str):
        db = DatabaseManager.get_instance()
        return db.execute("UPDATE PRODUCTIE SET stare = ? WHERE id_sarcina = ?;", (noua_stare, id_sarcina))

    @staticmethod
    def finalizeaza_sarcina_fefo(id_sarcina: int):
        """
        Finalizarea unei sarcini de catre cofetar:
        1. Identifica reteta si cantitatea de preparate produse.
        2. Calculeaza necesarul total de ingrediente.
        3. Executa algoritmul FEFO (First-Expired, First-Out): scade automat din loturile active
           ordonate crescator dupa data expirarii (termenul cel mai apropiat).
        4. Triggerul bazei de date trg_after_update_lot actualizeaza automat INGREDIENTE.stoc_curent
           si declanseaza trg_check_cantitate_lot pentru a preveni stocurile negative.
        5. Daca toate sarcinile unei comenzi sunt gata, comanda devine 'finalizata'.
        """
        db = DatabaseManager.get_instance()

        def _tx(cursor):
            # 1. Informatii despre sarcina
            cursor.execute("""
                SELECT p.id_sarcina, p.id_comanda, p.stare, cd.id_produs, cd.cantitate, prod.id_reteta, prod.denumire
                FROM PRODUCTIE p
                JOIN COMENZI_DETALII cd ON p.id_detaliu = cd.id_detaliu
                JOIN PRODUSE prod ON cd.id_produs = prod.id_produs
                WHERE p.id_sarcina = ?;
            """, (id_sarcina,))
            sarcina = cursor.fetchone()
            if not sarcina:
                raise ValueError("Sarcina de producție nu există!")

            if sarcina[2] == 'gata':
                return {"already_done": True, "mesaj": "Sarcina este deja finalizată!"}

            id_comanda = sarcina[1]
            cantitate_produse = sarcina[4]
            id_reteta = sarcina[5]
            nume_produs = sarcina[6]

            # 2. Ingredientele retetei
            cursor.execute("""
                SELECT ri.id_ingredient, i.nume, ri.cantitate, i.unitate_masura
                FROM RETETE_INGREDIENTE ri
                JOIN INGREDIENTE i ON ri.id_ingredient = i.id_ingredient
                WHERE ri.id_reteta = ?;
            """, (id_reteta,))
            ingrediente = cursor.fetchall()

            istoric_consum = []

            # 3. Consum FEFO per ingredient
            for ing in ingrediente:
                id_ing = ing[0]
                nume_ing = ing[1]
                cant_per_buc = float(ing[2])
                um_ing = ing[3]

                total_de_scazut = cant_per_buc * cantitate_produse
                ramas_de_scazut = total_de_scazut

                # Selectam loturile active FEFO: ordonate crescator dupa data expirarii
                cursor.execute("""
                    SELECT id_lot, cantitate_ramasa, data_expirarii
                    FROM LOTURI
                    WHERE id_ingredient = ? AND cantitate_ramasa > 0
                    ORDER BY data_expirarii ASC;
                """, (id_ing,))
                loturi = cursor.fetchall()

                for lot in loturi:
                    if ramas_de_scazut <= 0.0001:
                        break

                    id_lot = lot[0]
                    cant_lot = float(lot[1])
                    exp_lot = lot[2]

                    scadere = min(ramas_de_scazut, cant_lot)
                    noua_cantitate = round(cant_lot - scadere, 3)

                    # Actualizarea lotului activeaza automat triggerul de actualizare stoc_curent
                    cursor.execute("""
                        UPDATE LOTURI SET cantitate_ramasa = ? WHERE id_lot = ?;
                    """, (noua_cantitate, id_lot))

                    ramas_de_scazut -= scadere
                    istoric_consum.append({
                        "ingredient": nume_ing,
                        "id_lot": id_lot,
                        "data_expirarii": exp_lot,
                        "cantitate_consumata": round(scadere, 3),
                        "unitate_masura": um_ing
                    })

                if ramas_de_scazut > 0.0001:
                    raise ValueError(
                        f"Nu există suficient stoc în loturi pentru ingredientul '{nume_ing}'! "
                        f"Mai sunt necesare {round(ramas_de_scazut, 3)} {um_ing}."
                    )

            # 4. Trecem sarcina in 'gata'
            cursor.execute("UPDATE PRODUCTIE SET stare = 'gata' WHERE id_sarcina = ?;", (id_sarcina,))

            # 5. Verificam daca toata comanda este gata
            cursor.execute("""
                SELECT COUNT(*) FROM PRODUCTIE WHERE id_comanda = ? AND stare != 'gata';
            """, (id_comanda,))
            ramase = cursor.fetchone()[0]

            comanda_finalizata = False
            if ramase == 0:
                cursor.execute("UPDATE COMENZI SET stare = 'finalizata' WHERE id_comanda = ?;", (id_comanda,))
                comanda_finalizata = True

            return {
                "id_sarcina": id_sarcina,
                "produs": nume_produs,
                "comanda_finalizata": comanda_finalizata,
                "consum_fefo": istoric_consum,
                "mesaj": f"Sarcina '{nume_produs}' finalizată! Ingredientele au fost scăzute conform algoritmului FEFO."
            }

        return db.execute_transaction(_tx)

    @staticmethod
    def get_incarcare_cofetari():
        """Interogarea 3.2: Incarcare Cofetari - Sarcini active in lucru per cofetar"""
        db = DatabaseManager.get_instance()
        return db.query("""
            SELECT u.id_utilizator, u.nume AS cofetar, COUNT(p.id_sarcina) AS sarcini_active
            FROM UTILIZATORI u
            LEFT JOIN PRODUCTIE p ON u.id_utilizator = p.id_utilizator AND p.stare != 'gata'
            WHERE u.rol = 'cofetar'
            GROUP BY u.id_utilizator, u.nume;
        """)

    @staticmethod
    def get_comenzi_custom():
        """Interogarea 3.3: Comenzi personalizate aflate in productie"""
        db = DatabaseManager.get_instance()
        return db.query("""
            SELECT c.id_comanda, cl.nume AS client, cl.telefon, c.text_personalizat,
                   c.model_dorit, c.data_livrare, c.stare
            FROM COMENZI c
            JOIN CLIENTI cl ON c.id_client = cl.id_client
            WHERE c.tip = 'custom' AND c.stare != 'finalizata'
            ORDER BY c.data_livrare ASC;
        """)

    @staticmethod
    def get_stadiu_sarcini():
        """Interogarea 3.5: Stadiul sarcinilor de productie per comanda"""
        db = DatabaseManager.get_instance()
        return db.query("""
            SELECT c.id_comanda, p.id_sarcina, p.stare AS stare_sarcina,
                   p.data_productie, u.nume AS cofetar_alocat, prod.denumire AS produs, cd.cantitate
            FROM PRODUCTIE p
            JOIN COMENZI c ON p.id_comanda = c.id_comanda
            JOIN COMENZI_DETALII cd ON p.id_detaliu = cd.id_detaliu
            JOIN PRODUSE prod ON cd.id_produs = prod.id_produs
            JOIN UTILIZATORI u ON p.id_utilizator = u.id_utilizator
            ORDER BY c.id_comanda DESC, p.id_sarcina ASC;
        """)
