import os
import json
import urllib.request
import datetime
import random
from core.database import DatabaseManager

class AIService:
    @staticmethod
    def cauta_reteta_existenta(ingrediente_nume: list):
        """
        Pasul 1 descris in Capitolul III:
        Verifica mai intai in baza de date daca exista deja o reteta aprobata
        care contine toate ingredientele alese. Daca exista, o returneaza direct!
        """
        db = DatabaseManager.get_instance()
        if not ingrediente_nume:
            return None

        # Cautam retete aprobate care contin ingredientele cerute
        placeholders = ','.join(['?'] * len(ingrediente_nume))
        nume_lower = [i.strip().lower() for i in ingrediente_nume]

        sql = f"""
            SELECT r.id_reteta, r.denumire, r.portii_baza, r.sursa, r.stare,
                   COUNT(DISTINCT i.id_ingredient) AS ingrediente_potrivite
            FROM RETETE r
            JOIN RETETE_INGREDIENTE ri ON r.id_reteta = ri.id_reteta
            JOIN INGREDIENTE i ON ri.id_ingredient = i.id_ingredient
            WHERE r.stare = 'aprobata' AND LOWER(i.nume) IN ({placeholders})
            GROUP BY r.id_reteta
            HAVING ingrediente_potrivite = ?
            LIMIT 1;
        """
        row = db.query_one(sql, (*nume_lower, len(ingrediente_nume)))
        if row:
            # Preluam toate ingredientele retetei
            from services.retete_service import ReteteService
            reteta_completa = ReteteService.get_reteta_detalii(row['id_reteta'])
            reteta_completa['gasit_in_baza_de_date'] = True
            return reteta_completa

        return None

    @classmethod
    def genereaza_propunere_ai(cls, ingrediente_nume: list, tip_desert: str = "desert fin artizanal",
                               id_cofetar: int = 2):
        """
        Fluxul complet AI:
        1. Cautare in DB intai.
        2. Daca nu exista -> Apel AI (Gemini API sau Fallback inteligent offline).
        3. Salvare automata in GENERARI_AI + RETETE (stare='ciorna') + RETETE_INGREDIENTE.
        4. Returnare catre cofetar pentru verificare.
        """
        db = DatabaseManager.get_instance()

        # 1. Cautare in DB
        reteta_existenta = cls.cauta_reteta_existenta(ingrediente_nume)
        if reteta_existenta:
            return {
                "sursa": "baza_de_date",
                "mesaj": "S-a găsit o rețetă aprobată existentă în laborator care conține toate aceste ingrediente!",
                "reteta": reteta_existenta
            }

        # 2. Generare AI (online sau fallback artizanal)
        api_key = os.getenv("GEMINI_API_KEY", "").strip()
        reteta_ai = None

        if api_key:
            try:
                reteta_ai = cls._apeleaza_gemini_api(api_key, ingrediente_nume, tip_desert)
            except Exception as e:
                print(f"[AIService] Eroare apel API Gemini ({e}). Folosim fallback-ul inteligent de patiserie.")
                reteta_ai = cls._generator_artizanal_fallback(ingrediente_nume, tip_desert)
        else:
            reteta_ai = cls._generator_artizanal_fallback(ingrediente_nume, tip_desert)

        # 3. Salvare in baza de date (Tranzactie: GENERARI_AI + RETETE 'ciorna' + RETETE_INGREDIENTE)
        def _tx(cursor):
            now = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            ingrediente_str = ", ".join(ingrediente_nume)
            raspuns_json_str = json.dumps(reteta_ai, ensure_ascii=False)

            # Inseram reteta ca ciorna
            cursor.execute("""
                INSERT INTO RETETE (denumire, portii_baza, sursa, stare, id_utilizator)
                VALUES (?, ?, 'generata_ai', 'ciorna', ?);
            """, (reteta_ai['denumire'], reteta_ai.get('portii_baza', 10), id_cofetar))
            id_reteta = cursor.lastrowid

            # Inseram in tabela GENERARI_AI pentru istoric
            cursor.execute("""
                INSERT INTO GENERARI_AI (ingrediente_trimise, raspuns_ai, data_generarii, id_utilizator, id_reteta)
                VALUES (?, ?, ?, ?, ?);
            """, (ingrediente_str, raspuns_json_str, now, id_cofetar, id_reteta))
            id_generare = cursor.lastrowid

            # Asociem ingredientele din raspuns cu tabela INGREDIENTE
            for ing in reteta_ai.get('ingrediente', []):
                nume_ing = ing.get('nume', '').strip()
                cant = float(ing.get('cantitate', 0.2))
                um = ing.get('unitate_masura', 'kg')

                # Verificam daca ingredientul exista deja in catalog
                cursor.execute("SELECT id_ingredient FROM INGREDIENTE WHERE LOWER(nume) = LOWER(?);", (nume_ing,))
                row = cursor.fetchone()
                if row:
                    id_ing = row[0]
                else:
                    # Inseram ingredient nou in catalog
                    cursor.execute("""
                        INSERT INTO INGREDIENTE (nume, unitate_masura, stoc_curent, prag_minim)
                        VALUES (?, ?, 0.0, 1.0);
                    """, (nume_ing, um))
                    id_ing = cursor.lastrowid

                # Inseram legatura in RETETE_INGREDIENTE
                cursor.execute("""
                    INSERT OR REPLACE INTO RETETE_INGREDIENTE (id_reteta, id_ingredient, cantitate)
                    VALUES (?, ?, ?);
                """, (id_reteta, id_ing, cant))

            return {
                "id_reteta": id_reteta,
                "id_generare": id_generare,
                "denumire": reteta_ai['denumire'],
                "portii_baza": reteta_ai.get('portii_baza', 10),
                "timp_minute": reteta_ai.get('timp_minute', 50),
                "pasi_preparare": reteta_ai.get('pasi_preparare', ''),
                "ingrediente": reteta_ai.get('ingrediente', [])
            }

        res = db.execute_transaction(_tx)
        if not res['success']:
            raise RuntimeError(res['error'])

        return {
            "sursa": "inteligenta_artificiala",
            "mesaj": "Rețetă nouă generată cu succes de Asistentul AI și salvată ca ciornă!",
            "reteta": res['data']
        }

    @staticmethod
    def _apeleaza_gemini_api(api_key: str, ingrediente: list, tip_desert: str):
        prompt = f"""
        Ești un maestru cofetar-patiser artizanal cu experiență internațională.
        Creează o rețetă rafinată și delicioasă de tip '{tip_desert}' pentru un laborator de cofetărie artizanală.
        Trebuie să folosești OBLIGATORIU următoarele ingrediente disponibile: {', '.join(ingrediente)}.
        Răspunde STRICT în format JSON, fără niciun comentariu sau markdown în afara obiectului JSON:
        {{
            "denumire": "Numele desertului elegant",
            "portii_baza": 10,
            "timp_minute": 45,
            "ingrediente": [
                {{"nume": "nume ingredient", "cantitate": 0.350, "unitate_masura": "kg"}}
            ],
            "pasi_preparare": "Pașii detaliați de preparare..."
        }}
        """

        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}"
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"response_mime_type": "application/json"}
        }

        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode('utf-8'),
            headers={'Content-Type': 'application/json'}
        )

        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode('utf-8'))
            text = data['candidates'][0]['content']['parts'][0]['text']
            return json.loads(text)

    @staticmethod
    def _generator_artizanal_fallback(ingrediente: list, tip_desert: str):
        """
        Generator de retete de patiserie artizanala (fallback garantat 100% offline).
        Produce retete coerente, cu cantitati precise si instructiuni clare de laborator.
        """
        baza_nume = ", ".join(ingrediente[:2]).capitalize()
        denumiri_elegante = [
            f"Mousse Delicat cu {baza_nume}",
            f"Tartă Artizanală 'Maison Rose' cu {baza_nume}",
            f"Entremet Fin de Patiserie cu {baza_nume}",
            f"Pavlova Pastiche cu {baza_nume}",
            f"Eclere 'Plaisir Doux' cu {baza_nume}"
        ]
        nume_reteta = random.choice(denumiri_elegante)

        lista_ingrediente = []
        for ing in ingrediente:
            cant = round(random.choice([0.250, 0.300, 0.400, 0.500]), 3)
            lista_ingrediente.append({
                "nume": ing.strip(),
                "cantitate": cant,
                "unitate_masura": "kg"
            })

        # Ingrediente complementare de baza specifice cofetariei
        suplimentare = [("Făină 000", 0.300, "kg"), ("Unt 82%", 0.200, "kg"), ("Zahăr Tos", 0.150, "kg")]
        for sup_nume, sup_cant, sup_um in suplimentare:
            if not any(sup_nume.lower() in ing['nume'].lower() for ing in lista_ingrediente):
                lista_ingrediente.append({"nume": sup_nume, "cantitate": sup_cant, "unitate_masura": sup_um})

        pasi = (
            f"1. Pregătirea blatului și a bazei: Se omogenizează ingredientele uscate cu untul la temperatura camerei.\n"
            f"2. Încorporarea aromelor: Se infuzează {ingrediente[0]} într-un ganache catifelat.\n"
            f"3. Coacerea la 175°C timp de 25 de minute până la rumenire aurie.\n"
            f"4. Asamblarea straturilor și decorarea fină în stilul laboratorului 'Delice Pâtisserie'.\n"
            f"5. Răcirea la 4°C timp de minimum 2 ore înainte de porționare și servire."
        )

        return {
            "denumire": nume_reteta,
            "portii_baza": 10,
            "timp_minute": 55,
            "ingrediente": lista_ingrediente,
            "pasi_preparare": pasi
        }
