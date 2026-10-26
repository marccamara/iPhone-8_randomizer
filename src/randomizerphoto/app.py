import json
import threading
import traceback
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse, parse_qs

import toga
from toga.style import Pack

from .processing import process_folder_advanced

HERE = Path(__file__).parent
APP_DOCS = Path.home() / "Documents"

# On utilise le dossier base pour TOUT
BASE_DIR = APP_DOCS / "base"
HIST = APP_DOCS / "used_file_names.json"
EXTS = (".jpg", ".jpeg", ".png", ".webp")

STATE = {
    "base": None, "dbg": "Application prête.", "done": 0, "total": 0, 
    "running": False, "finished": False, "error": None,
}

def debug(message):
    STATE["dbg"] = str(message)
    print("[RandomizerPhoto]", message)

def scan_documents_folder():
    try:
        APP_DOCS.mkdir(parents=True, exist_ok=True)
        BASE_DIR.mkdir(parents=True, exist_ok=True)
        
        # On scanne UNIQUEMENT les photos qui ne sont pas déjà traitées (sans le préfixe R_)
        files = [f for f in BASE_DIR.iterdir() if f.suffix.lower() in EXTS and not f.name.startswith("R_") and not f.name.startswith(".")]
        count = len(files)
        
        STATE["base"] = str(BASE_DIR)
        
        if count > 0:
            debug(f"✅ {count} image(s) source(s) trouvée(s) dans /base.")
        else:
            debug("⚠️ Aucune image. Dépose tes photos dans le dossier 'base'.")
            
    except Exception as e:
        STATE["base"] = None
        debug(f"❌ Erreur scan : {e}")
        traceback.print_exc()

def count_images(base):
    if not base: return 0
    try: 
        return sum(1 for f in Path(base).iterdir() if f.suffix.lower() in EXTS and not f.name.startswith("R_"))
    except Exception: 
        return 0

def progress(done, total):
    STATE["done"] = done
    STATE["total"] = total

def run_processing(n, model, ratio):
    STATE["running"] = True
    STATE["finished"] = False
    STATE["error"] = None
    try:
        if not STATE["base"]: 
            raise RuntimeError("Aucun dossier prêt.")
            
        base = Path(STATE["base"])
        out = base # ON ECRIT DANS LE MEME DOSSIER BASE

        debug("Traitement en cours...")

        try:
            process_folder_advanced(
                str(base), str(out), n, str(HIST), progress, model, ratio
            )
            debug("✅ Traitement terminé avec succès.")
        except Exception as e:
            debug(f"❌ CRASH LORS DU TRAITEMENT : {str(e)}")
            raise e

    except Exception as e:
        STATE["error"] = str(e)
        debug(f"❌ Erreur : {e}")
        traceback.print_exc()
    finally:
        STATE["running"] = False
        STATE["finished"] = True

def make_handler(app):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args): pass

        def send_json(self, code=200, data=None):
            if data is None: data = {}
            body = json.dumps(data).encode("utf-8")
            self.send_response(code)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self):
            parsed = urlparse(self.path)
            path = parsed.path

            if path == "/":
                try:
                    body = (HERE / "index.html").read_bytes()
                    self.send_response(200)
                    self.send_header("Content-Type", "text/html; charset=utf-8")
                    self.send_header("Content-Length", str(len(body)))
                    self.end_headers()
                    self.wfile.write(body)
                except Exception:
                    self.send_json(500, {"error": traceback.format_exc()})
                return

            if path == "/state":
                state = dict(STATE)
                if STATE.get("base"):
                    state["count"] = count_images(STATE["base"])
                    state["name"] = "Dossier /base"
                else:
                    state["count"] = 0
                    state["name"] = None
                self.send_json(200, state)
                return
            self.send_json(404, {"error": "Not found"})

        def do_POST(self):
            parsed = urlparse(self.path)
            path = parsed.path

            if path == "/pick":
                scan_documents_folder()
                self.send_json(200, {"ok": True})
                return

            if path == "/run":
                query = parse_qs(parsed.query)
                n = int(query.get("n", ["10"])[0])
                model = query.get("model", ["Mix"])[0]
                ratio = query.get("ratio", ["3:4"])[0]

                if STATE["base"] and not STATE["running"]:
                    threading.Thread(target=run_processing, args=(n, model, ratio), daemon=True).start()
                self.send_json(200, {"ok": True})
                return
            self.send_json(404, {"error": "Not found"})
    return Handler

class RandomizerPhoto(toga.App):
    def startup(self):
        APP_DOCS.mkdir(parents=True, exist_ok=True)
        BASE_DIR.mkdir(parents=True, exist_ok=True)

        server = ThreadingHTTPServer(("127.0.0.1", 0), make_handler(self))
        threading.Thread(target=server.serve_forever, daemon=True).start()
        port = server.server_address[1]

        self.main_window = toga.MainWindow(title=self.formal_name)
        self.main_window.content = toga.WebView(
            url=f"http://127.0.0.1:{port}/", style=Pack(flex=1)
        )
        self.main_window.show()
        print("[RandomizerPhoto] Application prête.")

def main():
    return RandomizerPhoto("RandomizerPhoto", "com.perso.randomizerphoto")
