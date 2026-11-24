import os
import sqlite3
import datetime
import hashlib
import binascii

class DatabaseManager:
    """
    Manager de Baze de Date unificat:
    Se conecteaza la MySQL/MariaDB (daca este pornit) sau utilizeaza SQLite ca motor local garantat.
    Gestioneaza tranzactii, triggere si seed data.
    """
    _instance = None

    def __init__(self, db_path="laborator_cofetarie.db"):
        self.db_path = os.path.abspath(db_path)
        self.engine_type = "sqlite"
        self._init_database()

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = DatabaseManager()
        return cls._instance

    def _get_connection(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON;")
        return conn

    def _init_database(self):
        """Creaza schema si datele de test daca baza de date este noua."""
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.executescript("""
        CREATE TABLE IF NOT EXISTS UTILIZATORI (
            id_utilizator INTEGER PRIMARY KEY AUTOINCREMENT,
            nume VARCHAR(100) UNIQUE NOT NULL,
            parola VARCHAR(255) NOT NULL,
            rol VARCHAR(20) NOT NULL CHECK (rol IN ('administrator', 'cofetar', 'vanzator'))
        );

        CREATE TABLE IF NOT EXISTS FURNIZORI (
            id_furnizor INTEGER PRIMARY KEY AUTOINCREMENT,
            denumire VARCHAR(100) NOT NULL,
            telefon VARCHAR(15)
        );

        CREATE TABLE IF NOT EXISTS INGREDIENTE (
            id_ingredient INTEGER PRIMARY KEY AUTOINCREMENT,
            nume VARCHAR(100) NOT NULL,
            unitate_masura VARCHAR(10) NOT NULL,
            stoc_curent DECIMAL(10,3) DEFAULT 0,
            prag_minim DECIMAL(10,3) DEFAULT 0
        );

        CREATE TABLE IF NOT EXISTS CLIENTI (
            id_client INTEGER PRIMARY KEY AUTOINCREMENT,
            nume VARCHAR(100) NOT NULL,
            telefon VARCHAR(15) UNIQUE NOT NULL
        );

        CREATE TABLE IF NOT EXISTS LOTURI (
            id_lot INTEGER PRIMARY KEY AUTOINCREMENT,
            id_ingredient INTEGER NOT NULL,
            id_furnizor INTEGER NOT NULL,
            cantitate_ramasa DECIMAL(10,3) NOT NULL,
            data_receptiei DATETIME NOT NULL,
            data_expirarii DATE NOT NULL,
            FOREIGN KEY (id_ingredient) REFERENCES INGREDIENTE(id_ingredient),
            FOREIGN KEY (id_furnizor) REFERENCES FURNIZORI(id_furnizor)
        );

        CREATE TABLE IF NOT EXISTS RETETE (
            id_reteta INTEGER PRIMARY KEY AUTOINCREMENT,
            denumire VARCHAR(100) NOT NULL,
            portii_baza INTEGER NOT NULL,
            sursa VARCHAR(20) NOT NULL CHECK (sursa IN ('manuala', 'generata_ai')),
            stare VARCHAR(20) NOT NULL CHECK (stare IN ('ciorna', 'verificata', 'aprobata')),
            id_utilizator INTEGER NOT NULL,
            FOREIGN KEY (id_utilizator) REFERENCES UTILIZATORI(id_utilizator)
        );

        CREATE TABLE IF NOT EXISTS RETETE_INGREDIENTE (
            id_reteta INTEGER NOT NULL,
            id_ingredient INTEGER NOT NULL,
            cantitate DECIMAL(10,3) NOT NULL,
            PRIMARY KEY (id_reteta, id_ingredient),
            FOREIGN KEY (id_reteta) REFERENCES RETETE(id_reteta) ON DELETE CASCADE,
            FOREIGN KEY (id_ingredient) REFERENCES INGREDIENTE(id_ingredient)
        );

        CREATE TABLE IF NOT EXISTS GENERARI_AI (
            id_generare INTEGER PRIMARY KEY AUTOINCREMENT,
            ingrediente_trimise TEXT NOT NULL,
            raspuns_ai TEXT NOT NULL,
            data_generarii DATETIME NOT NULL,
            id_utilizator INTEGER NOT NULL,
            id_reteta INTEGER,
            FOREIGN KEY (id_utilizator) REFERENCES UTILIZATORI(id_utilizator),
            FOREIGN KEY (id_reteta) REFERENCES RETETE(id_reteta)
        );

        CREATE TABLE IF NOT EXISTS PRODUSE (
            id_produs INTEGER PRIMARY KEY AUTOINCREMENT,
            denumire VARCHAR(100) NOT NULL,
            pret_vanzare DECIMAL(10,2) NOT NULL,
            activ BOOLEAN DEFAULT 1,
            id_reteta INTEGER NOT NULL,
            FOREIGN KEY (id_reteta) REFERENCES RETETE(id_reteta)
        );

        CREATE TABLE IF NOT EXISTS COMENZI (
            id_comanda INTEGER PRIMARY KEY AUTOINCREMENT,
            data_livrare DATETIME NOT NULL,
            tip VARCHAR(20) NOT NULL CHECK (tip IN ('rapida', 'custom')),
            stare VARCHAR(20) NOT NULL CHECK (stare IN ('preluata', 'in_productie', 'finalizata')),
            text_personalizat VARCHAR(255),
            model_dorit VARCHAR(255),
            id_client INTEGER NOT NULL,
            FOREIGN KEY (id_client) REFERENCES CLIENTI(id_client)
        );

        CREATE TABLE IF NOT EXISTS COMENZI_DETALII (
            id_detaliu INTEGER PRIMARY KEY AUTOINCREMENT,
            id_comanda INTEGER NOT NULL,
            id_produs INTEGER NOT NULL,
            cantitate INTEGER NOT NULL,
            FOREIGN KEY (id_comanda) REFERENCES COMENZI(id_comanda) ON DELETE CASCADE,
            FOREIGN KEY (id_produs) REFERENCES PRODUSE(id_produs)
        );

        CREATE TABLE IF NOT EXISTS PRODUCTIE (
            id_sarcina INTEGER PRIMARY KEY AUTOINCREMENT,
            stare VARCHAR(20) NOT NULL CHECK (stare IN ('in_asteptare', 'in_lucru', 'gata')),
            data_productie DATE NOT NULL,
            id_detaliu INTEGER NOT NULL,
            id_comanda INTEGER NOT NULL,
            id_utilizator INTEGER NOT NULL,
            FOREIGN KEY (id_detaliu) REFERENCES COMENZI_DETALII(id_detaliu) ON DELETE CASCADE,
            FOREIGN KEY (id_comanda) REFERENCES COMENZI(id_comanda) ON DELETE CASCADE,
            FOREIGN KEY (id_utilizator) REFERENCES UTILIZATORI(id_utilizator)
        );
        """)

        cursor.executescript("""
        DROP TRIGGER IF EXISTS trg_after_insert_lot;
        CREATE TRIGGER trg_after_insert_lot
        AFTER INSERT ON LOTURI
        BEGIN
            UPDATE INGREDIENTE
            SET stoc_curent = stoc_curent + NEW.cantitate_ramasa
            WHERE id_ingredient = NEW.id_ingredient;
        END;

        DROP TRIGGER IF EXISTS trg_after_update_lot;
        CREATE TRIGGER trg_after_update_lot
        AFTER UPDATE ON LOTURI
        BEGIN
            UPDATE INGREDIENTE
            SET stoc_curent = stoc_curent + (NEW.cantitate_ramasa - OLD.cantitate_ramasa)
            WHERE id_ingredient = NEW.id_ingredient;
        END;

        DROP TRIGGER IF EXISTS trg_after_delete_lot;
        CREATE TRIGGER trg_after_delete_lot
        AFTER DELETE ON LOTURI
        BEGIN
            UPDATE INGREDIENTE
            SET stoc_curent = stoc_curent - OLD.cantitate_ramasa
            WHERE id_ingredient = OLD.id_ingredient;
        END;

        DROP TRIGGER IF EXISTS trg_check_cantitate_lot;
        CREATE TRIGGER trg_check_cantitate_lot
        BEFORE UPDATE ON LOTURI
        WHEN NEW.cantitate_ramasa < 0
        BEGIN
            SELECT RAISE(ABORT, 'Eroare tranzacțională: Cantitatea rămasă din lot nu poate fi negativă!');
        END;

        DROP TRIGGER IF EXISTS trg_check_stoc_ingredient;
        CREATE TRIGGER trg_check_stoc_ingredient
        BEFORE UPDATE ON INGREDIENTE
        WHEN NEW.stoc_curent < 0
        BEGIN
            SELECT RAISE(ABORT, 'Eroare tranzacțională: Stocul curent al ingredientului nu poate fi negativ!');
        END;
        """)

        cursor.execute("SELECT COUNT(*) FROM UTILIZATORI;")
        if cursor.fetchone()[0] == 0:
            self._seed_data(cursor)

        conn.commit()
        conn.close()

    def _hash_password(self, password, salt=b'laborator_delice_salt'):
        pwdhash = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt, 100000)
        return binascii.hexlify(pwdhash).decode('ascii')

    def reset_and_seed_data(self):
        """Re-populeaza baza de date cu datele bogate si proaspete din seed."""
        if os.path.exists(self.db_path):
            os.remove(self.db_path)
        self._init_database()

    def _seed_data(self, cursor):
        today = datetime.date.today().strftime('%Y-%m-%d')
        now = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        def d_plus(days):
            return (datetime.date.today() + datetime.timedelta(days=days)).strftime('%Y-%m-%d')
        def d_minus(days):
            return (datetime.date.today() - datetime.timedelta(days=days)).strftime('%Y-%m-%d %H:%M:%S')

        # 1. Utilizatori
        pwd_admin = self._hash_password("admin123")
        pwd_cofetar = self._hash_password("cofetar123")
        pwd_vanzator = self._hash_password("vanzator123")

        cursor.executemany("""
        INSERT INTO UTILIZATORI (nume, parola, rol) VALUES (?, ?, ?);
        """, [
            ('elena.admin', pwd_admin, 'administrator'),
            ('mihai.cofetar', pwd_cofetar, 'cofetar'),
            ('ana.vanzator', pwd_vanzator, 'vanzator')
        ])

        # 2. Furnizori
        cursor.executemany("""
        INSERT INTO FURNIZORI (denumire, telefon) VALUES (?, ?);
        """, [
            ('Lactate LactoSud SRL', '0722111222'),
            ('Ingrediente Premium SRL', '0733333444'),
            ('Fructe Exotice Import SRL', '0744999888'),
            ('Delicii & Arome Italice SRL', '0755123789'),
            ('Depozitul de Cacao & Ciocolată', '0766444555')
        ])

        # 3. Ingrediente (stoc initial 0, triggerele de la LOTURI il cresc automat!)
        cursor.executemany("""
        INSERT INTO INGREDIENTE (nume, unitate_masura, stoc_curent, prag_minim) VALUES (?, ?, ?, ?);
        """, [
            ('Făină 000', 'kg', 0.000, 15.000),
            ('Zahăr Tos', 'kg', 0.000, 8.000),
            ('Unt 82%', 'kg', 0.000, 5.000),
            ('Ciocolată Neagră 70%', 'kg', 0.000, 3.000),
            ('Ciocolată Albă Callebaut', 'kg', 0.000, 2.500),
            ('Fructul Pasiunii / Mango', 'kg', 0.000, 3.000),
            ('Zmeură Proaspătă', 'kg', 0.000, 2.000),
            ('Fistic Granulat de Bronte', 'kg', 0.000, 1.500),
            ('Mascarpone Cremoso', 'kg', 0.000, 4.000),
            ('Smântână Dulce 35%', 'l', 0.000, 6.000),
            ('Vanilie Bourbon de Madagascar', 'kg', 0.000, 0.500),
            ('Ouă Proaspete', 'buc', 0.000, 60.000),
            ('Cafea Espresso Arabica', 'kg', 0.000, 1.000),
            ('Lapte Integral 3.5%', 'l', 0.000, 10.000),
            ('Lămâi Bio de Sicilia', 'kg', 0.000, 3.000)
        ])

        # 4. Clienti
        cursor.executemany("""
        INSERT INTO CLIENTI (nume, telefon) VALUES (?, ?);
        """, [
            ('Maria Georgescu', '0744555666'),
            ('Cristian Vasilescu', '0755888999'),
            ('Ioana Dumitrescu', '0766123456'),
            ('Alexandru Popa', '0722998877'),
            ('Andreea Marin', '0733112233'),
            ('Mihai Stănescu', '0745001122'),
            ('Camelia Enache', '0788334455')
        ])

        # 5. Loturi (FEFO)
        cursor.executemany("""
        INSERT INTO LOTURI (id_ingredient, id_furnizor, cantitate_ramasa, data_receptiei, data_expirarii) VALUES (?, ?, ?, ?, ?);
        """, [
            (1, 2, 45.000, '2026-11-01 08:00:00', d_plus(60)), # Faina
            (2, 2, 4.500, '2026-11-01 08:00:00', d_plus(90)),  # Zahar (sub prag 8kg)
            (3, 1, 2.000, '2026-11-02 09:00:00', d_plus(3)),   # Unt (expira in 3 zile - URGENT!)
            (3, 1, 4.000, '2026-11-10 10:30:00', d_plus(18)),  # Unt lot 2
            (4, 5, 8.500, '2026-11-05 11:00:00', d_plus(45)),  # Ciocolata neagra
            (5, 5, 3.200, '2026-11-08 14:00:00', d_plus(40)),  # Ciocolata alba
            (6, 3, 2.800, '2026-11-12 08:30:00', d_plus(4)),   # Mango / Passionfruit (expira in 4 zile - excelent pt AI!)
            (7, 3, 1.800, '2026-11-15 09:15:00', d_plus(2)),   # Zmeura (expira in 2 zile - URGENT!)
            (8, 4, 2.500, '2026-11-03 10:00:00', d_plus(90)),  # Fistic granulat
            (9, 1, 2.500, '2026-11-14 08:00:00', d_plus(8)),   # Mascarpone (sub prag 4kg)
            (10, 1, 4.000, '2026-11-15 08:00:00', d_plus(3)),  # Smantana dulce (expira in 3 zile - URGENT!)
            (11, 4, 0.400, '2026-10-20 11:00:00', d_plus(120)),# Vanilie
            (12, 1, 45.000, '2026-11-16 07:30:00', d_plus(10)),# Oua (sub prag 60 buc)
            (13, 4, 3.000, '2026-11-01 12:00:00', d_plus(180)),# Cafea
            (14, 1, 15.000, '2026-11-14 08:00:00', d_plus(7)), # Lapte
            (15, 3, 4.000, '2026-11-10 09:00:00', d_plus(14))  # Lamai
        ])

        # 6. Retete
        cursor.executemany("""
        INSERT INTO RETETE (denumire, portii_baza, sursa, stare, id_utilizator) VALUES (?, ?, ?, ?, ?);
        """, [
            ('Tort Amandină Tradițională', 10, 'manuala', 'aprobata', 1),
            ('Ecler cu Ciocolată și Ganache', 12, 'generata_ai', 'aprobata', 2),
            ('Pavlova cu Fructe de Pădure & Fistic', 8, 'manuala', 'aprobata', 2),
            ('Tiramisu Artizanal cu Mascarpone', 10, 'manuala', 'aprobata', 1),
            ('Tartă cu Lămâie de Sicilia și Bezea', 8, 'manuala', 'aprobata', 2),
            ('Tort Red Velvet Velvet Delice', 12, 'generata_ai', 'verificata', 2),
            ('Mousse Exotique cu Mango & Fructul Pasiunii', 10, 'generata_ai', 'ciorna', 2)
        ])

        # 7. Retete Ingrediente
        cursor.executemany("""
        INSERT INTO RETETE_INGREDIENTE (id_reteta, id_ingredient, cantitate) VALUES (?, ?, ?);
        """, [
            (1, 1, 0.500), (1, 2, 0.400), (1, 3, 0.350), (1, 4, 0.250), (1, 12, 4.000),
            (2, 1, 0.250), (2, 3, 0.150), (2, 4, 0.300), (2, 10, 0.250), (2, 12, 4.000),
            (3, 2, 0.300), (3, 7, 0.350), (3, 8, 0.100), (3, 10, 0.300), (3, 12, 4.000),
            (4, 9, 0.500), (4, 2, 0.150), (4, 10, 0.250), (4, 13, 0.050), (4, 12, 3.000),
            (5, 1, 0.250), (5, 2, 0.250), (5, 3, 0.200), (5, 15, 0.300), (5, 12, 3.000),
            (6, 1, 0.400), (6, 2, 0.350), (6, 3, 0.250), (6, 9, 0.300), (6, 12, 3.000),
            (7, 6, 0.450), (7, 5, 0.250), (7, 10, 0.350)
        ])

        # 8. Generari AI
        cursor.executemany("""
        INSERT INTO GENERARI_AI (ingrediente_trimise, raspuns_ai, data_generarii, id_utilizator, id_reteta) VALUES (?, ?, ?, ?, ?);
        """, [
            ('ciocolată neagră, smântână, ouă', 'Rețetă Ecler cu Ganache catifelat de ciocolată generată cu succes.', d_minus(5), 2, 2),
            ('unt, mascarpone, cacao, făină', 'Rețetă Tort Red Velvet cu cremă fină de brânză și vanilie bourbon.', d_minus(2), 2, 6),
            ('mango, fructul pasiunii, ciocolată albă', 'Rețetă Mousse Exotique cu jeleu proaspăt de fructe exotice și oglindă albă.', now, 2, 7)
        ])

        # 9. Produse
        cursor.executemany("""
        INSERT INTO PRODUSE (denumire, pret_vanzare, activ, id_reteta) VALUES (?, ?, ?, ?);
        """, [
            ('Tort Amandină Tradițional (1.2 kg)', 155.00, 1, 1),
            ('Ecler Ciocolată & Ganache Bucată', 16.50, 1, 2),
            ('Pavlova Festivă cu Zmeură & Fistic', 28.00, 1, 3),
            ('Tiramisu Delice la Pahar', 24.00, 1, 4),
            ('Tartă cu Lămâie & Bezea Caramelizată', 22.00, 1, 5)
        ])

        # 10. Comenzi
        cursor.executemany("""
        INSERT INTO COMENZI (data_livrare, tip, stare, text_personalizat, model_dorit, id_client) VALUES (?, ?, ?, ?, ?, ?);
        """, [
            (now, 'custom', 'in_productie', 'La Mulți Ani Maria!', 'Model Aniversar Flori Pastel Roz', 1),
            (d_minus(2), 'rapida', 'finalizata', None, None, 2),
            (d_minus(1), 'rapida', 'finalizata', None, None, 3),
            (d_minus(3), 'custom', 'finalizata', 'Botez Sofia - Bun Venit!', 'Norișori pufoși și fundițe roz', 4),
            (d_plus(1) + ' 15:00:00', 'rapida', 'preluata', None, None, 5),
            (d_plus(2) + ' 16:30:00', 'custom', 'in_productie', 'Nuntă Fericită Ioana & Radu', 'Trei etaje, perle de zahăr și bezea', 7)
        ])

        # 11. Comenzi Detalii
        cursor.executemany("""
        INSERT INTO COMENZI_DETALII (id_comanda, id_produs, cantitate) VALUES (?, ?, ?);
        """, [
            (1, 1, 1), (1, 2, 4),
            (2, 1, 2),
            (3, 2, 6), (3, 4, 2),
            (4, 1, 1), (4, 3, 4),
            (5, 5, 2),
            (6, 1, 2), (6, 3, 6)
        ])

        # 12. Productie
        cursor.executemany("""
        INSERT INTO PRODUCTIE (stare, data_productie, id_detaliu, id_comanda, id_utilizator) VALUES (?, ?, ?, ?, ?);
        """, [
            ('in_lucru', today, 1, 1, 2),
            ('in_asteptare', today, 2, 1, 2),
            ('in_asteptare', d_plus(1), 7, 5, 2),
            ('in_lucru', d_plus(2), 8, 6, 2),
            ('in_asteptare', d_plus(2), 9, 6, 2)
        ])

    def query(self, sql, params=()):
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute(sql, params)
        rows = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return rows

    def query_one(self, sql, params=()):
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute(sql, params)
        row = cursor.fetchone()
        conn.close()
        return dict(row) if row else None

    def execute(self, sql, params=()):
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute(sql, params)
        conn.commit()
        last_id = cursor.lastrowid
        rowcount = cursor.rowcount
        conn.close()
        return {"last_id": last_id, "rowcount": rowcount}

    def execute_transaction(self, callback):
        conn = self._get_connection()
        cursor = conn.cursor()
        try:
            conn.execute("BEGIN IMMEDIATE;")
            result = callback(cursor)
            conn.commit()
            return {"success": True, "data": result}
        except Exception as e:
            conn.rollback()
            return {"success": False, "error": str(e)}
        finally:
            conn.close()
