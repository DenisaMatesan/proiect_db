from core.database import DatabaseManager

class RapoarteService:
    @staticmethod
    def get_dashboard_stats():
        """Statistici agregate pentru dashboard-ul Administratorului."""
        db = DatabaseManager.get_instance()
        critice = db.query_one("SELECT COUNT(*) AS total FROM INGREDIENTE WHERE stoc_curent <= prag_minim;")
        expirabile = db.query_one("SELECT COUNT(*) AS total FROM LOTURI WHERE data_expirarii <= date('now', '+7 days') AND cantitate_ramasa > 0;")
        venit = db.query_one("""
            SELECT COALESCE(SUM(cd.cantitate * p.pret_vanzare), 0) AS total
            FROM COMENZI_DETALII cd
            JOIN PRODUSE p ON cd.id_produs = p.id_produs
            JOIN COMENZI c ON cd.id_comanda = c.id_comanda
            WHERE c.stare = 'finalizata';
        """)
        comenzi_active = db.query_one("SELECT COUNT(*) AS total FROM COMENZI WHERE stare != 'finalizata';")
        retete_ai = db.query_one("SELECT COUNT(*) AS total FROM RETETE WHERE sursa = 'generata_ai' AND stare IN ('ciorna', 'verificata');")

        return {
            "ingrediente_critice": critice['total'] if critice else 0,
            "loturi_urgente": expirabile['total'] if expirabile else 0,
            "venit_total": float(venit['total']) if venit else 0.0,
            "comenzi_active": comenzi_active['total'] if comenzi_active else 0,
            "retete_ai_in_asteptare": retete_ai['total'] if retete_ai else 0
        }

    @staticmethod
    def top_produse_vandute():
        """Interogarea 4.1: Top cele mai vandute produse dupa bucati si incasari"""
        db = DatabaseManager.get_instance()
        return db.query("""
            SELECT p.id_produs, p.denumire AS produs,
                   SUM(cd.cantitate) AS bucati_vandute,
                   SUM(cd.cantitate * p.pret_vanzare) AS total_incasat
            FROM COMENZI_DETALII cd
            JOIN PRODUSE p ON cd.id_produs = p.id_produs
            JOIN COMENZI c ON cd.id_comanda = c.id_comanda
            WHERE c.stare = 'finalizata'
            GROUP BY p.id_produs, p.denumire
            ORDER BY bucati_vandute DESC;
        """)

    @staticmethod
    def clienti_fideli(prag_lei=200):
        """Interogarea 4.3: Clienti fideli (Vanzari totale peste un prag dat - clauza HAVING)"""
        db = DatabaseManager.get_instance()
        return db.query("""
            SELECT cl.id_client, cl.nume AS client, cl.telefon,
                   COUNT(c.id_comanda) AS numar_comenzi,
                   SUM(cd.cantitate * p.pret_vanzare) AS total_cheltuit
            FROM CLIENTI cl
            JOIN COMENZI c ON cl.id_client = c.id_client
            JOIN COMENZI_DETALII cd ON c.id_comanda = cd.id_comanda
            JOIN PRODUSE p ON cd.id_produs = p.id_produs
            GROUP BY cl.id_client, cl.nume, cl.telefon
            HAVING total_cheltuit > ?
            ORDER BY total_cheltuit DESC;
        """, (prag_lei,))

    @staticmethod
    def produse_peste_media():
        """Interogarea 4.4: Produse cu pret peste pretul mediu (Subinterogare)"""
        db = DatabaseManager.get_instance()
        medie_row = db.query_one("SELECT AVG(pret_vanzare) AS pret_mediu FROM PRODUSE;")
        pret_mediu = round(medie_row['pret_mediu'] if medie_row and medie_row['pret_mediu'] else 0, 2)

        produse = db.query("""
            SELECT id_produs, denumire, pret_vanzare
            FROM PRODUSE
            WHERE pret_vanzare > (SELECT AVG(pret_vanzare) FROM PRODUSE)
            ORDER BY pret_vanzare DESC;
        """)
        return {"pret_mediu": pret_mediu, "produse": produse}

    @staticmethod
    def venituri_luna_curenta():
        """Interogarea 4.5: Venituri totale in luna curenta"""
        db = DatabaseManager.get_instance()
        res = db.query_one("""
            SELECT COALESCE(SUM(cd.cantitate * p.pret_vanzare), 0) AS venit_lunar
            FROM COMENZI_DETALII cd
            JOIN PRODUSE p ON cd.id_produs = p.id_produs
            JOIN COMENZI c ON cd.id_comanda = c.id_comanda
            WHERE c.stare = 'finalizata'
              AND strftime('%m', c.data_livrare) = strftime('%m', 'now')
              AND strftime('%Y', c.data_livrare) = strftime('%Y', 'now');
        """)
        return float(res['venit_lunar']) if res else 0.0

    @staticmethod
    def retete_per_utilizator():
        """Interogarea 2.3: Numar de retete create per utilizator/cofetar"""
        db = DatabaseManager.get_instance()
        return db.query("""
            SELECT u.id_utilizator, u.nume AS utilizator, u.rol,
                   COUNT(r.id_reteta) AS total_retete
            FROM UTILIZATORI u
            LEFT JOIN RETETE r ON u.id_utilizator = r.id_utilizator
            GROUP BY u.id_utilizator, u.nume;
        """)

    @staticmethod
    def retete_aprobate_si_ingrediente():
        """Interogarea 2.5: Retete aprobate si numarul de ingrediente din compozitie"""
        db = DatabaseManager.get_instance()
        return db.query("""
            SELECT r.id_reteta, r.denumire AS reteta, r.portii_baza,
                   COUNT(ri.id_ingredient) AS numar_ingrediente
            FROM RETETE r
            JOIN RETETE_INGREDIENTE ri ON r.id_reteta = ri.id_reteta
            WHERE r.stare = 'aprobata'
            GROUP BY r.id_reteta, r.denumire;
        """)
