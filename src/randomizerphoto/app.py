import json
import threading
import traceback
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse, parse_qs

import toga
from toga.style import Pack

from rubicon.objc import ObjCClass, ObjCInstance, ObjCProtocol, NSObject, objc_method

from .processing import process_folder_advanced

# ============================================================
# CONFIGURATION
# ============================================================
HERE = Path(__file__).parent
APP_DOCS = Path.home() / "Documents"
HIST = APP_DOCS / "used_file_names.json"
EXTS = (".jpg", ".jpeg", ".png", ".webp", ".heic")

# ============================================================
# ÉTAT GLOBAL
# ============================================================
STATE = {
    "base": None, "dbg": "Application prête.", "picking": False,
    "done": 0, "total": 0, "running": False, "finished": False, "error": None,
}

REFS = {"picker": None, "delegate": None, "security_url": None}

def debug(message):
    STATE["dbg"] = str(message)
    print("[RandomizerPhoto]", message)

def stop_security_scope():
    url = REFS.get("security_url")
    if url is not None:
        try: url.stopAccessingSecurityScopedResource()
        except Exception: pass
        REFS["security_url"] = None

# ============================================================
# DELEGATE IOS
# ============================================================
UIDocumentPickerDelegate = ObjCProtocol("UIDocumentPickerDelegate")

class PickerDelegate(NSObject, protocols=[UIDocumentPickerDelegate]):
    
    @objc_method
    def documentPicker_didPickDocumentsAtURLs_(self, picker, urls):
        try:
            STATE["picking"] = False
            if not urls:
                STATE["base"] = None
                return

            url = urls[0]
            stop_security_scope()
            REFS["security_url"] = url

            try: url.startAccessingSecurityScopedResource()
            except Exception as e: print("Erreur scope:", e)

            path = url.path
            if callable(path): path = path()
            base = Path(str(path))

            if not base.exists() or not base.is_dir():
                STATE["base"] = None
                debug("❌ Dossier invalide.")
                return

            count = sum(1 for f in base.iterdir() if f.suffix.lower() in EXTS)
            STATE["base"] = str(base)
            debug(f"✅ Dossier sélectionné : {count} images")
        except Exception:
            STATE["base"] = None
            traceback.print_exc()

    @objc_method
    def documentPickerWasCancelled_(self, picker):
        STATE["picking"] = False
        debug("Sélection annulée.")

# ============================================================
# PICKER & TRAITEMENT
# ============================================================
def create_folder_picker():
    Picker = ObjCClass("UIDocumentPickerViewController")
    UTType = ObjCClass("UTType")
    try: folder_type = UTType.typeWithIdentifier_("public.folder")
    except Exception: folder_type = UTType.typeWithIdentifier("public.folder")

    try:
        # asCopy=True est CRUCIAL pour iOS 16 et l'iPhone 8
        picker = Picker.alloc().initForOpeningContentTypes_asCopy_([folder_type], True)
    except Exception:
        picker = Picker.alloc().initForOpeningContentTypes_([folder_type])
    return picker

def present_picker(app):
    try:
        STATE["picking"] = True
        picker = create_folder_picker()
        delegate = PickerDelegate.alloc().init()
        
        REFS["picker"], REFS["delegate"] = picker, delegate
        picker.delegate = delegate
        picker.allowsMultipleSelection = False

        native = app.main_window._impl.native
        window = ObjCInstance(native)
        root = window.rootViewController

        root.presentViewController(picker, animated=True, completion=None)
        debug("📂 Picker ouvert.")
    except Exception:
        STATE["picking"] = False
        traceback.print_exc()

def count_images(base):
    if not base: return 0
    try: return sum(1 for f in Path(base).iterdir() if f.suffix.lower() in EXTS)
    except Exception: return 0

def progress(done, total):
    STATE["done"] = done
    STATE["total"] = total

def run_processing(n, model, ratio):
    STATE["running"] = True
    STATE["finished"] = False
    try:
        if not STATE["base"]: raise RuntimeError("Aucun dossier sélectionné.")
        base = Path(STATE["base"])
        
        out = base / "photos_traitees"
        out.mkdir(exist_ok=True)

        process_folder_advanced(
            str(base), str(out), n, str(HIST), progress, model, ratio
        )
        debug("✅ Traitement terminé.")
    except Exception as e:
        STATE["error"] = str(e)
        traceback.print_exc()
    finally:
        STATE["running"] = False
        STATE["finished"] = True
        stop_security_scope()

# ============================================================
# SERVEUR HTTP
# ============================================================
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
                    state["name"] = Path(STATE["base"]).name
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
                if not STATE["picking"]:
                    STATE["picking"] = True
                    app.loop.call_soon_threadsafe(present_picker, app)
                self.send_json(200, {"ok": True})
                return

            if path == "/run":
                query = parse_qs(parsed.query)
                n = int(query.get("n", ["10"])[0])
                model = query.get("model", ["Mix"])[0]
                ratio = query.get("ratio", ["3:4"])[0]

                if STATE["base"] and not STATE["running"] and not STATE["picking"]:
                    threading.Thread(target=run_processing, args=(n, model, ratio), daemon=True).start()
                self.send_json(200, {"ok": True})
                return
            self.send_json(404, {"error": "Not found"})
    return Handler

# ============================================================
# TOGA APP
# ============================================================
class RandomizerPhoto(toga.App):
    def startup(self):
        APP_DOCS.mkdir(parents=True, exist_ok=True)
        server = ThreadingHTTPServer(("127.0.0.1", 0), make_handler(self))
        threading.Thread(target=server.serve_forever, daemon=True).start()
        port = server.server_address[1]

        self.main_window = toga.MainWindow(title=self.formal_name)
        self.main_window.content = toga.WebView(
            url=f"http://127.0.0.1:{port}/", style=Pack(flex=1)
        )
        self.main_window.show()

def main():
    return RandomizerPhoto("RandomizerPhoto", "com.perso.randomizerphoto")
