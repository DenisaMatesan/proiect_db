from core.database import DatabaseManager

class ReteteService:
    @staticmethod
    def get_retete(stare: str = None):
        db = DatabaseManager.get_instance()
        params = []
        sql = """
            SELECT r.id_reteta, r.denumire, r.portii_baza, r.sursa, r.stare,
                   u.nume AS creator, COUNT(ri.id_ingredient) AS numar_ingrediente,
                   p.id_produs, p.pret_vanzare, p.activ AS produs_activ
            FROM RETETE r
            JOIN UTILIZATORI u ON r.id_utilizator = u.id_utilizator
            LEFT JOIN RETETE_INGREDIENTE ri ON r.id_reteta = ri.id_reteta
            LEFT JOIN PRODUSE p ON r.id_reteta = p.id_reteta
        """
        if stare:
            sql += " WHERE r.stare = ? "
            params.append(stare)
        sql += " GROUP BY r.id_reteta ORDER BY r.id_reteta DESC;"
        return db.query(sql, params)

    @staticmethod
    def get_reteta_detalii(id_reteta: int):
        """Interogarea 2.1: Descompunere Reteta - Ingrediente si cantitati"""
        db = DatabaseManager.get_instance()
        reteta = db.query_one("""
            SELECT r.id_reteta, r.denumire, r.portii_baza, r.sursa, r.stare,
                   u.nume AS creator, p.id_produs, p.pret_vanzare, p.activ
            FROM RETETE r
            JOIN UTILIZATORI u ON r.id_utilizator = u.id_utilizator
            LEFT JOIN PRODUSE p ON r.id_reteta = p.id_reteta
            WHERE r.id_reteta = ?;
        """, (id_reteta,))

        if not reteta:
            return None

        ingrediente = db.query("""
            SELECT i.id_ingredient, i.nume, ri.cantitate AS cantitate_baza,
                   i.unitate_masura, i.stoc_curent
            FROM RETETE_INGREDIENTE ri
            JOIN INGREDIENTE i ON ri.id_ingredient = i.id_ingredient
            WHERE ri.id_reteta = ?
            ORDER BY i.nume ASC;
        """, (id_reteta,))

        reteta['ingrediente'] = ingrediente
        return reteta

    @staticmethod
    def scale_reteta(id_reteta: int, portii_dorite: int):
        """
        Scalarea retetei:
        cantitate_necesara = cantitate * portii_dorite / portii_baza
        """
        reteta = ReteteService.get_reteta_detalii(id_reteta)
        if not reteta:
            return None

        portii_baza = reteta['portii_baza']
        if portii_baza <= 0:
            portii_baza = 1

        factor_scalare = float(portii_dorite) / float(portii_baza)
        reteta['portii_dorite'] = portii_dorite
        reteta['factor_scalare'] = factor_scalare

        for ing in reteta['ingrediente']:
            cant_scalata = round(float(ing['cantitate_baza']) * factor_scalare, 3)
            ing['cantitate_scalata'] = cant_scalata
            ing['stoc_suficient'] = ing['stoc_curent'] >= cant_scalata

        return reteta

    @staticmethod
    def aproba_reteta(id_reteta: int, pret_vanzare: float):
        """
        Aprobarea de catre Administrator:
        1. Trece RETETE.stare in 'aprobata'.
        2. Creeaza sau actualizeaza inregistrarea in entitatea PRODUSE cu activ = 1,
           facand noul desert vizibil pentru vanzatorii de la tejghea!
        """
        db = DatabaseManager.get_instance()
        reteta = db.query_one("SELECT * FROM RETETE WHERE id_reteta = ?;", (id_reteta,))
        if not reteta:
            raise ValueError("Rețeta nu a fost găsită!")

        def _tx(cursor):
            cursor.execute("UPDATE RETETE SET stare = 'aprobata' WHERE id_reteta = ?;", (id_reteta,))
            # Verificam daca exista deja in PRODUSE
            cursor.execute("SELECT id_produs FROM PRODUSE WHERE id_reteta = ?;", (id_reteta,))
            prod = cursor.fetchone()
            if prod:
                cursor.execute("""
                    UPDATE PRODUSE SET denumire = ?, pret_vanzare = ?, activ = 1 WHERE id_reteta = ?;
                """, (reteta['denumire'], pret_vanzare, id_reteta))
            else:
                cursor.execute("""
                    INSERT INTO PRODUSE (denumire, pret_vanzare, activ, id_reteta)
                    VALUES (?, ?, 1, ?);
                """, (reteta['denumire'], pret_vanzare, id_reteta))
            return True

        return db.execute_transaction(_tx)

    @staticmethod
    def trimite_la_verificare(id_reteta: int):
        """Cofetarul marcheaza reteta ca 'verificata' pentru a fi aprobata de Administrator."""
        db = DatabaseManager.get_instance()
        return db.execute("UPDATE RETETE SET stare = 'verificata' WHERE id_reteta = ?;", (id_reteta,))

    @staticmethod
    def get_retete_ai_flux():
        """Interogarea 2.2: Retete generate de AI in stadiu de verificare/ciorna pentru Administrator"""
        db = DatabaseManager.get_instance()
        return db.query("""
            SELECT r.id_reteta, r.denumire AS reteta_propusa, r.portii_baza,
                   u.nume AS cofetar_solicitant,
                   COALESCE(g.ingrediente_trimise, 'Ingrediente selectate în laborator') AS ingrediente_trimise,
                   r.stare,
                   COALESCE(g.data_generarii, datetime('now')) AS data_generarii,
                   COALESCE(g.id_generare, 0) AS id_generare
            FROM RETETE r
            JOIN UTILIZATORI u ON r.id_utilizator = u.id_utilizator
            LEFT JOIN GENERARI_AI g ON r.id_reteta = g.id_reteta
            WHERE r.sursa = 'generata_ai' AND r.stare IN ('ciorna', 'verificata')
            GROUP BY r.id_reteta
            ORDER BY r.id_reteta DESC;
        """)

    @staticmethod
    def get_retete_ai_toate():
        """Toate retetele generate de AI (ciorna, verificata, aprobata) pentru tabloul Cofetarului."""
        db = DatabaseManager.get_instance()
        return db.query("""
            SELECT r.id_reteta, r.denumire, r.portii_baza, r.sursa, r.stare,
                   u.nume AS creator, COUNT(DISTINCT ri.id_ingredient) AS numar_ingrediente,
                   g.id_generare, g.ingrediente_trimise, g.data_generarii, g.raspuns_ai,
                   p.id_produs, p.pret_vanzare, p.activ AS este_activ_vanzare
            FROM RETETE r
            JOIN UTILIZATORI u ON r.id_utilizator = u.id_utilizator
            LEFT JOIN GENERARI_AI g ON r.id_reteta = g.id_reteta
            LEFT JOIN RETETE_INGREDIENTE ri ON r.id_reteta = ri.id_reteta
            LEFT JOIN PRODUSE p ON r.id_reteta = p.id_reteta
            WHERE r.sursa = 'generata_ai'
            GROUP BY r.id_reteta
            ORDER BY r.id_reteta DESC;
        """)

    @staticmethod
    def cauta_dupa_ingredient(termen: str):
        """Interogarea 2.4: Cautare retete care contin un ingredient specific"""
        db = DatabaseManager.get_instance()
        return db.query("""
            SELECT DISTINCT r.id_reteta, r.denumire AS reteta, r.sursa, r.stare
            FROM RETETE r
            JOIN RETETE_INGREDIENTE ri ON r.id_reteta = ri.id_reteta
            JOIN INGREDIENTE i ON ri.id_ingredient = i.id_ingredient
            WHERE i.nume LIKE ?
            ORDER BY r.denumire ASC;
        """, (f"%{termen}%",))
