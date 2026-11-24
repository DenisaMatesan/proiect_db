import datetime
from core.database import DatabaseManager

class StocuriService:
    @staticmethod
    def get_ingrediente():
        db = DatabaseManager.get_instance()
        return db.query("""
            SELECT id_ingredient, nume, unitate_masura, stoc_curent, prag_minim,
                   CASE WHEN stoc_curent <= prag_minim THEN 1 ELSE 0 END AS este_critic
            FROM INGREDIENTE
            ORDER BY nume ASC;
        """)

    @staticmethod
    def get_stocuri_critice():
        """Interogarea 1.1: Stocuri Critice (Ingrediente sub sau la pragul minim)"""
        db = DatabaseManager.get_instance()
        return db.query("""
            SELECT id_ingredient, nume, stoc_curent, prag_minim, unitate_masura
            FROM INGREDIENTE
            WHERE stoc_curent <= prag_minim
            ORDER BY stoc_curent ASC;
        """)

    @staticmethod
    def get_loturi_fefo():
        """Interogarea 1.2: Algoritmul FEFO - Loturi active ordonate crescator dupa data expirarii"""
        db = DatabaseManager.get_instance()
        return db.query("""
            SELECT l.id_lot, i.id_ingredient, i.nume AS ingredient, l.cantitate_ramasa, i.unitate_masura,
                   l.data_receptiei, l.data_expirarii, f.denumire AS furnizor
            FROM LOTURI l
            JOIN INGREDIENTE i ON l.id_ingredient = i.id_ingredient
            JOIN FURNIZORI f ON l.id_furnizor = f.id_furnizor
            WHERE l.cantitate_ramasa > 0 AND l.data_expirarii >= date('now')
            ORDER BY l.data_expirarii ASC;
        """)

    @staticmethod
    def get_loturi_urgente(zile=7):
        """Interogarea 1.3: Loturi urgente (care expira in urmatoarele N zile)"""
        db = DatabaseManager.get_instance()
        return db.query(f"""
            SELECT l.id_lot, i.id_ingredient, i.nume AS ingredient, l.cantitate_ramasa, i.unitate_masura,
                   l.data_expirarii, f.denumire AS furnizor
            FROM LOTURI l
            JOIN INGREDIENTE i ON l.id_ingredient = i.id_ingredient
            JOIN FURNIZORI f ON l.id_furnizor = f.id_furnizor
            WHERE l.data_expirarii <= date('now', '+{zile} days') AND l.cantitate_ramasa > 0
            ORDER BY l.data_expirarii ASC;
        """)

    @staticmethod
    def receptie_lot(id_ingredient: int, id_furnizor: int, cantitate: float, data_expirarii: str):
        """
        Inregistreaza o noua livrare in tabela LOTURI.
        Triggerul trg_after_insert_lot actualizeaza automat stoc_curent din INGREDIENTE!
        """
        db = DatabaseManager.get_instance()
        now = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        res = db.execute("""
            INSERT INTO LOTURI (id_ingredient, id_furnizor, cantitate_ramasa, data_receptiei, data_expirarii)
            VALUES (?, ?, ?, ?, ?);
        """, (id_ingredient, id_furnizor, cantitate, now, data_expirarii))
        return res

    @staticmethod
    def adauga_ingredient(nume: str, unitate_masura: str, prag_minim: float):
        db = DatabaseManager.get_instance()
        return db.execute("""
            INSERT INTO INGREDIENTE (nume, unitate_masura, stoc_curent, prag_minim)
            VALUES (?, ?, 0.000, ?);
        """, (nume.strip(), unitate_masura.strip(), prag_minim))

    @staticmethod
    def get_furnizori():
        db = DatabaseManager.get_instance()
        return db.query("SELECT * FROM FURNIZORI ORDER BY denumire ASC;")

    @staticmethod
    def adauga_furnizor(denumire: str, telefon: str):
        db = DatabaseManager.get_instance()
        return db.execute("INSERT INTO FURNIZORI (denumire, telefon) VALUES (?, ?);", (denumire.strip(), telefon.strip()))

    @staticmethod
    def get_total_per_furnizor():
        """Interogarea 1.4: Total ingrediente receptionate per Furnizor"""
        db = DatabaseManager.get_instance()
        return db.query("""
            SELECT f.id_furnizor, f.denumire AS furnizor, f.telefon,
                   COUNT(l.id_lot) AS total_loturi,
                   COALESCE(SUM(l.cantitate_ramasa), 0) AS cantitate_totala
            FROM FURNIZORI f
            LEFT JOIN LOTURI l ON f.id_furnizor = l.id_furnizor
            GROUP BY f.id_furnizor, f.denumire;
        """)

    @staticmethod
    def get_istoric_receptii(data_start: str = None, data_end: str = None):
        """Interogarea 1.5: Istoric receptii materii prime"""
        db = DatabaseManager.get_instance()
        if not data_start:
            data_start = (datetime.date.today() - datetime.timedelta(days=90)).strftime('%Y-%m-%d')
        if not data_end:
            data_end = datetime.date.today().strftime('%Y-%m-%d')

        return db.query("""
            SELECT l.id_lot, i.nume AS ingredient, l.cantitate_ramasa, l.data_receptiei, f.denumire AS furnizor
            FROM LOTURI l
            JOIN INGREDIENTE i ON l.id_ingredient = i.id_ingredient
            JOIN FURNIZORI f ON l.id_furnizor = f.id_furnizor
            WHERE date(l.data_receptiei) BETWEEN ? AND ?
            ORDER BY l.data_receptiei DESC;
        """, (data_start, data_end))
