import os
import sys
import json
import urllib.parse
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from core.database import DatabaseManager
from core.auth import AuthService
from services.stocuri_service import StocuriService
from services.retete_service import ReteteService
from services.comenzi_service import ComenziService
from services.productie_service import ProductieService
from services.ai_service import AIService
from services.rapoarte_service import RapoarteService

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

class DeliceAppHandler(BaseHTTPRequestHandler):
    def _send_json(self, data, status=200):
        body = json.dumps(data, ensure_ascii=False).encode('utf-8')
        self.send_response(status)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Content-Length', str(len(body)))
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, PUT, DELETE, OPTIONS')
        self.end_headers()
        self.wfile.write(body)

    def _send_file(self, file_path, content_type='text/html'):
        if not os.path.isfile(file_path):
            self.send_error(404, "Fișierul nu a fost găsit")
            return
        with open(file_path, 'rb') as f:
            content = f.read()
        self.send_response(200)
        self.send_header('Content-Type', f'{content_type}; charset=utf-8')
        self.send_header('Content-Length', str(len(content)))
        self.end_headers()
        self.wfile.write(content)

    def _parse_body(self):
        content_len = int(self.headers.get('Content-Length', 0))
        if content_len > 0:
            raw = self.rfile.read(content_len).decode('utf-8')
            try:
                return json.loads(raw)
            except Exception:
                return urllib.parse.parse_qs(raw)
        return {}

    def _get_auth_user(self):
        auth_header = self.headers.get('Authorization', '')
        token = ''
        if auth_header.startswith('Bearer '):
            token = auth_header[7:].strip()
        else:
            cookie_header = self.headers.get('Cookie', '')
            for cookie in cookie_header.split(';'):
                if 'delice_token=' in cookie:
                    token = cookie.split('delice_token=')[1].strip()
                    break
        if token:
            return AuthService.verify_session_token(token)
        return None

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, PUT, DELETE, OPTIONS')
        self.end_headers()

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        query = urllib.parse.parse_qs(parsed.query)

        # 1. Rute statice si pagina principala
        if path == '/' or path == '/index.html':
            return self._send_file(os.path.join(BASE_DIR, 'templates', 'index.html'), 'text/html')
        elif path.startswith('/static/css/'):
            filename = os.path.basename(path)
            return self._send_file(os.path.join(BASE_DIR, 'static', 'css', filename), 'text/css')
        elif path.startswith('/static/js/'):
            filename = os.path.basename(path)
            return self._send_file(os.path.join(BASE_DIR, 'static', 'js', filename), 'application/javascript')

        # 2. Rute API
        try:
            if path == '/api/auth/me':
                user = self._get_auth_user()
                if user:
                    return self._send_json({"authenticated": True, "user": user})
                return self._send_json({"authenticated": False}, 401)

            elif path == '/api/dashboard/stats':
                return self._send_json(RapoarteService.get_dashboard_stats())

            elif path == '/api/stocuri/ingrediente':
                return self._send_json(StocuriService.get_ingrediente())

            elif path == '/api/stocuri/critice':
                return self._send_json(StocuriService.get_stocuri_critice())

            elif path == '/api/stocuri/loturi-fefo':
                return self._send_json(StocuriService.get_loturi_fefo())

            elif path == '/api/stocuri/loturi-urgente':
                zile = int(query.get('zile', [7])[0])
                return self._send_json(StocuriService.get_loturi_urgente(zile))

            elif path == '/api/stocuri/furnizori':
                return self._send_json(StocuriService.get_furnizori())

            elif path == '/api/retete':
                stare = query.get('stare', [None])[0]
                return self._send_json(ReteteService.get_retete(stare))

            elif path.startswith('/api/retete/') and '/scale' in path:
                # /api/retete/<id>/scale?portii=50
                parts = path.strip('/').split('/')
                id_reteta = int(parts[2])
                portii = int(query.get('portii', [10])[0])
                return self._send_json(ReteteService.scale_reteta(id_reteta, portii))

            elif path.startswith('/api/retete/') and path.count('/') == 3:
                parts = path.strip('/').split('/')
                id_reteta = int(parts[2])
                detalii = ReteteService.get_reteta_detalii(id_reteta)
                if detalii:
                    return self._send_json(detalii)
                return self._send_json({"error": "Rețeta nu există"}, 404)

            elif path == '/api/retete/flux-ai':
                return self._send_json(ReteteService.get_retete_ai_flux())

            elif path == '/api/retete/toate-ai':
                return self._send_json(ReteteService.get_retete_ai_toate())

            elif path == '/api/produse/active':
                return self._send_json(ComenziService.get_produse_active())

            elif path == '/api/clienti':
                return self._send_json(ComenziService.get_clienti())

            elif path == '/api/clienti/cauta':
                tel = query.get('telefon', [''])[0]
                client = ComenziService.cauta_client(tel)
                return self._send_json({"gasit": bool(client), "client": client})

            elif path == '/api/comenzi':
                return self._send_json(ComenziService.get_comenzi())

            elif path.startswith('/api/comenzi/') and path.count('/') == 3:
                parts = path.strip('/').split('/')
                id_comanda = int(parts[2])
                detalii = ComenziService.get_comanda_detalii(id_comanda)
                if detalii:
                    return self._send_json(detalii)
                return self._send_json({"error": "Comanda nu există"}, 404)

            elif path == '/api/productie/sarcini':
                data_p = query.get('data', [None])[0]
                return self._send_json(ProductieService.get_sarcini_zi(data_p))

            elif path == '/api/productie/incarcare':
                return self._send_json(ProductieService.get_incarcare_cofetari())

            elif path == '/api/productie/comenzi-custom':
                return self._send_json(ProductieService.get_comenzi_custom())

            elif path == '/api/productie/stadiu':
                return self._send_json(ProductieService.get_stadiu_sarcini())

            # Rapoarte
            elif path == '/api/rapoarte/top-produse':
                return self._send_json(RapoarteService.top_produse_vandute())

            elif path == '/api/rapoarte/clienti-fideli':
                prag = float(query.get('prag', [200])[0])
                return self._send_json(RapoarteService.clienti_fideli(prag))

            elif path == '/api/rapoarte/produse-peste-media':
                return self._send_json(RapoarteService.produse_peste_media())

            elif path == '/api/rapoarte/venit-lunar':
                return self._send_json({"venit_lunar": RapoarteService.venituri_luna_curenta()})

            elif path == '/api/rapoarte/receptii-furnizori':
                return self._send_json(StocuriService.get_total_per_furnizor())

            elif path == '/api/rapoarte/retete-utilizatori':
                return self._send_json(RapoarteService.retete_per_utilizator())

            elif path == '/api/rapoarte/retete-aprobate-ingrediente':
                return self._send_json(RapoarteService.retete_aprobate_si_ingrediente())

            else:
                return self._send_json({"error": "Ruta API nu a fost găsită"}, 404)

        except Exception as e:
            return self._send_json({"error": str(e)}, 500)

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        body = self._parse_body()

        try:
            # 1. Autentificare
            if path == '/api/auth/login':
                username = body.get('username', '').strip()
                password = body.get('password', '').strip()
                res = AuthService.authenticate(username, password)
                if res:
                    return self._send_json({"success": True, "user": res})
                return self._send_json({"success": False, "error": "Nume de utilizator (format nume.rol) sau parolă incorectă!"}, 401)

            # 2. Receptie lot
            elif path == '/api/stocuri/receptie-lot':
                id_ing = int(body.get('id_ingredient'))
                id_furnizor = int(body.get('id_furnizor'))
                cantitate = float(body.get('cantitate'))
                data_exp = body.get('data_expirarii')
                res = StocuriService.receptie_lot(id_ing, id_furnizor, cantitate, data_exp)
                return self._send_json({"success": True, "mesaj": "Lot recepționat cu succes! Stocul a crescut automat prin trigger."})

            # 3. Adaugare ingredient
            elif path == '/api/stocuri/ingrediente':
                nume = body.get('nume', '')
                um = body.get('unitate_masura', 'kg')
                prag = float(body.get('prag_minim', 0))
                res = StocuriService.adauga_ingredient(nume, um, prag)
                return self._send_json({"success": True, "id": res['last_id']})

            # 4. Adaugare furnizor
            elif path == '/api/stocuri/furnizori':
                denumire = body.get('denumire', '')
                tel = body.get('telefon', '')
                res = StocuriService.adauga_furnizor(denumire, tel)
                return self._send_json({"success": True, "id": res['last_id']})

            # 5. Aprobare reteta de catre Administrator
            elif path.startswith('/api/retete/') and path.endswith('/aproba'):
                parts = path.strip('/').split('/')
                id_reteta = int(parts[2])
                pret = float(body.get('pret_vanzare', 0))
                res = ReteteService.aproba_reteta(id_reteta, pret)
                return self._send_json(res)

            # 6. Cofetarul trimite reteta AI spre verificare
            elif path.startswith('/api/retete/') and path.endswith('/trimite-verificare'):
                parts = path.strip('/').split('/')
                id_reteta = int(parts[2])
                res = ReteteService.trimite_la_verificare(id_reteta)
                return self._send_json({"success": True, "mesaj": "Rețeta a fost marcată ca 'verificată' și trimisă administratorului!"})

            # 7. Asistent AI: Propunere reteta
            elif path == '/api/ai/genereaza':
                ingrediente = body.get('ingrediente', [])
                tip = body.get('tip_desert', 'desert fin artizanal')
                user = self._get_auth_user()
                id_cofetar = user['id'] if user else 2
                res = AIService.genereaza_propunere_ai(ingrediente, tip, id_cofetar)
                return self._send_json({"success": True, "data": res})

            # 8. Plasare comanda vanzator (Tranzactionala cu verificare stoc)
            elif path == '/api/comenzi/plasare':
                client_data = body.get('client', {})
                produse_items = body.get('produse', [])
                tip = body.get('tip', 'rapida')
                text_pers = body.get('text_personalizat', '')
                model = body.get('model_dorit', '')
                livrare = body.get('data_livrare', '')
                user = self._get_auth_user()
                id_v = user['id'] if user else 3

                res = ComenziService.plasare_comanda_tranzactionala(
                    client_data, produse_items, tip, text_pers, model, livrare, id_v
                )
                if res.get('success'):
                    return self._send_json(res)
                return self._send_json(res, 400)

            # 9. Schimbare stare sarcina productie ('in_lucru')
            elif path.startswith('/api/productie/sarcini/') and path.endswith('/stare'):
                parts = path.strip('/').split('/')
                id_sarcina = int(parts[3])
                noua_stare = body.get('stare', 'in_lucru')
                res = ProductieService.schimba_stare_sarcina(id_sarcina, noua_stare)
                return self._send_json({"success": True, "mesaj": f"Starea sarcinii a fost actualizată în '{noua_stare}'."})

            # 10. Finalizare sarcina productie FEFO
            elif path.startswith('/api/productie/sarcini/') and path.endswith('/finalizeaza-fefo'):
                parts = path.strip('/').split('/')
                id_sarcina = int(parts[3])
                res = ProductieService.finalizeaza_sarcina_fefo(id_sarcina)
                if res.get('success'):
                    return self._send_json(res)
                return self._send_json(res, 400)

            else:
                return self._send_json({"error": "Ruta API POST nu a fost găsită"}, 404)

        except Exception as e:
            return self._send_json({"success": False, "error": str(e)}, 500)

def run_server(port=8000):
    # Asiguram initializarea bazei de date
    db = DatabaseManager.get_instance()
    
    # Gasire automata de port liber daca cel implicit este ocupat (ex: AirPlay pe Mac ocupa portul 5000)
    candidate_ports = [port, 8080, 5050, 8000, 8888]
    if port not in candidate_ports:
        candidate_ports.insert(0, port)

    httpd = None
    actual_port = port
    for p in candidate_ports:
        try:
            ThreadingHTTPServer.allow_reuse_address = True
            server_address = ('', p)
            httpd = ThreadingHTTPServer(server_address, DeliceAppHandler)
            actual_port = p
            break
        except OSError as e:
            if e.errno == 48: # Address already in use
                continue
            raise e

    if not httpd:
        print("❌ Nu s-a putut gasi un port liber pentru server.")
        return

    print(f"\n✨ ================================================================= ✨")
    print(f"   🌸 Delice Pâtisserie - Laborator Artizanal de Cofetărie 🌸")
    print(f"   Aplicația rulează la: http://localhost:{actual_port}")
    print(f"   Baza de date: SQLite conectată la {db.db_path}")
    print(f"   Conturi de test configurate (format nume.rol):")
    print(f"     👩‍💼 Administrator : elena.admin  / admin123")
    print(f"     👨‍🍳 Cofetar       : mihai.cofetar / cofetar123")
    print(f"     🧑‍💼 Vânzător      : ana.vanzator  / vanzator123")
    print(f"✨ ================================================================= ✨\n")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nOprind serverul...")
        httpd.server_close()

if __name__ == '__main__':
    port = 8000
    if len(sys.argv) > 1 and sys.argv[1].isdigit():
        port = int(sys.argv[1])
    run_server(port)
