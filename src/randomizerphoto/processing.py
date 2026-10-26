import os
import random
import json
import datetime
import numpy as np
from PIL import Image, ImageEnhance, ImageOps
import piexif

# ... (Garde tout le dictionnaire IPHONE_PROFILES et la fonction generate_iphone_exif inchangés) ...
IPHONE_PROFILES = [
    {"model": "iPhone 8", "software": "16.7.2", "back": {"focal": (399, 100), "fnum": (18, 10), "focal35": 28, "lens": "iPhone 8 back camera 3.99mm f/1.8", "lens_info": "3.99mm f/1.8", "width": 3024, "height": 4032}, "front": {"focal": (287, 100), "fnum": (22, 10), "focal35": 32, "lens": "iPhone 8 front camera 2.87mm f/2.2", "lens_info": "2.87mm f/2.2", "width": 3024, "height": 4032}},
    {"model": "iPhone 11", "software": "16.5", "back": {"focal": (425, 100), "fnum": (18, 10), "focal35": 26, "lens": "iPhone 11 back camera 4.25mm f/1.8", "lens_info": "1.54-4.25mm f/1.8-2.4", "width": 3024, "height": 4032}, "front": {"focal": (271, 100), "fnum": (22, 10), "focal35": 23, "lens": "iPhone 11 front camera 2.71mm f/2.2", "lens_info": "2.71mm f/2.2", "width": 3024, "height": 4032}},
    {"model": "iPhone 12", "software": "17.1.1", "back": {"focal": (42, 10), "fnum": (16, 10), "focal35": 26, "lens": "iPhone 12 back dual wide camera 4.2mm f/1.6", "lens_info": "1.55-4.2mm f/1.6-2.4", "width": 3024, "height": 4032}, "front": {"focal": (271, 100), "fnum": (22, 10), "focal35": 23, "lens": "iPhone 12 front camera 2.71mm f/2.2", "lens_info": "2.71mm f/2.2", "width": 3024, "height": 4032}},
    {"model": "iPhone 13", "software": "17.4", "back": {"focal": (51, 10), "fnum": (16, 10), "focal35": 26, "lens": "iPhone 13 back dual wide camera 5.1mm f/1.6", "lens_info": "1.54-5.1mm f/1.6-2.4", "width": 3024, "height": 4032}, "front": {"focal": (271, 100), "fnum": (22, 10), "focal35": 23, "lens": "iPhone 13 front camera 2.71mm f/2.2", "lens_info": "2.71mm f/2.2", "width": 3024, "height": 4032}},
    {"model": "iPhone 14", "software": "17.5.1", "back": {"focal": (57, 10), "fnum": (15, 10), "focal35": 26, "lens": "iPhone 14 back camera 5.7mm f/1.5", "lens_info": "1.57-5.7mm f/1.5-2.4", "width": 3024, "height": 4032}, "front": {"focal": (269, 100), "fnum": (19, 10), "focal35": 24, "lens": "iPhone 14 front camera 2.69mm f/1.9", "lens_info": "2.69mm f/1.9", "width": 3024, "height": 4032}},
    {"model": "iPhone 15", "software": "17.6", "back": {"focal": (596, 100), "fnum": (16, 10), "focal35": 26, "lens": "iPhone 15 back camera 5.96mm f/1.6", "lens_info": "2.22-5.96mm f/1.6-2.4", "width": 3024, "height": 4032}, "front": {"focal": (269, 100), "fnum": (19, 10), "focal35": 23, "lens": "iPhone 15 front camera 2.69mm f/1.9", "lens_info": "2.69mm f/1.9", "width": 3024, "height": 4032}},
]

def generate_iphone_exif(device, camera):
    cam = device[camera]
    now = datetime.datetime.now()
    date_str = (now - datetime.timedelta(days=random.randint(1, 30), seconds=random.randint(0, 86400))).strftime("%Y:%m:%d %H:%M:%S")
    iso = random.choice([32, 40, 50, 64, 80, 100, 125, 160, 200])
    
    if iso <= 64: shutter = random.choice([(1, 500), (1, 800), (1, 1000), (1, 1200)])
    elif iso <= 125: shutter = random.choice([(1, 120), (1, 160), (1, 200), (1, 250)])
    else: shutter = random.choice([(1, 60), (1, 80), (1, 100)])

    zeroth = {piexif.ImageIFD.Make: "Apple", piexif.ImageIFD.Model: device["model"], piexif.ImageIFD.Software: f"iOS {device['software']}", piexif.ImageIFD.Orientation: 1, piexif.ImageIFD.XResolution: (72, 1), piexif.ImageIFD.YResolution: (72, 1), piexif.ImageIFD.ResolutionUnit: 2, piexif.ImageIFD.DateTime: date_str}
    exif = {piexif.ExifIFD.DateTimeOriginal: date_str, piexif.ExifIFD.DateTimeDigitized: date_str, piexif.ExifIFD.OffsetTimeOriginal: "+01:00", piexif.ExifIFD.ColorSpace: 1, piexif.ExifIFD.ExifVersion: b"0232", piexif.ExifIFD.ComponentsConfiguration: b"\x01\x02\x03\x00", piexif.ExifIFD.FocalLength: cam["focal"], piexif.ExifIFD.FNumber: cam["fnum"], piexif.ExifIFD.FocalLengthIn35mmFilm: cam["focal35"], piexif.ExifIFD.ISOSpeedRatings: iso, piexif.ExifIFD.LensModel: cam["lens"], piexif.ExifIFD.LensMake: "Apple", piexif.ExifIFD.LensInfo: cam["lens_info"], piexif.ExifIFD.ExposureTime: shutter, piexif.ExifIFD.ExposureBiasValue: (0, 1), piexif.ExifIFD.Flash: 16, piexif.ExifIFD.MeteringMode: 5, piexif.ExifIFD.SensingMethod: 2, piexif.ExifIFD.ExposureProgram: 2, piexif.ExifIFD.WhiteBalance: 0, piexif.ExifIFD.SceneCaptureType: 0}
    return piexif.dump({"0th": zeroth, "Exif": exif, "1st": {}, "GPS": {}, "Interop": {}})

def process_single_image(img, output_path, ratio_str, model_choice):
    random.seed(os.urandom(16))
    np.random.seed(int.from_bytes(os.urandom(4), "big"))

    if model_choice and model_choice != "Mix":
        pool = [m for m in IPHONE_PROFILES if m["model"] == model_choice]
        device = random.choice(pool) if pool else random.choice(IPHONE_PROFILES)
    else:
        device = random.choice(IPHONE_PROFILES)

    camera = random.choice(["back", "front"])
    
    ratio_map = {"3:4": (3, 4), "1:1": (1, 1), "9:16": (9, 16), "4:3": (4, 3)}
    target_ratio_val = ratio_map.get(ratio_str, (3, 4))

    # MÉTHODE ULTRA LIGHT : on laisse Pillow gérer le redimensionnement direct sans créer de multiples copies en RAM
    target_width = 1080 
    target_height = int(target_width * target_ratio_val[1] / target_ratio_val[0])
    
    # Recadrage et redimensionnement en une seule étape
    img = ImageOps.fit(img, (target_width, target_height), Image.Resampling.LANCZOS)

    # Ajustements basiques directs
    img = ImageEnhance.Brightness(img).enhance(random.uniform(0.99, 1.02))
    img = ImageEnhance.Contrast(img).enhance(random.uniform(0.99, 1.02))
    img = ImageEnhance.Color(img).enhance(random.uniform(0.99, 1.01))

    exif_bytes = generate_iphone_exif(device, camera)
    
    # Écriture directe sur le disque (aucune copie mémoire supplémentaire)
    img.save(output_path, format="JPEG", quality=random.randint(94, 96), exif=exif_bytes)

def generate_unique_filename(used):
    while True:
        r = random.randint(1000, 9999)
        if r not in used:
            used.add(r)
            return f"R_{r}.jpg"

def load_history(path):
    if os.path.exists(path):
        try:
            with open(path, "r") as f: return set(json.load(f))
        except Exception: return set()
    return set()

def save_history(history_set, path):
    try:
        with open(path, "w") as f: json.dump(list(history_set), f)
    except Exception as e:
        print("Impossible de sauvegarder l'historique:", e)

def process_folder_advanced(input_folder, output_base_folder, num_folders, history_path, progress_callback, model=None, ratio="3:4"):
    exts = ('.jpg', '.jpeg', '.png', '.webp')
    files = [f for f in os.listdir(input_folder) if f.lower().endswith(exts) and not f.startswith("R_")]
    if not files: return

    used = load_history(history_path)
    total = num_folders * len(files)
    done = 0

    for i in range(1, num_folders + 1):
        for name in files:
            out_name = generate_unique_filename(used)
            out = os.path.join(output_base_folder, out_name)
            try:
                # OUVERTURE EN MODE "STREAMING" : L'image n'est jamais chargée entièrement en mémoire
                with Image.open(os.path.join(input_folder, name)) as img:
                    if img.mode in ("RGBA", "P"): img = img.convert("RGB")
                    img = ImageOps.exif_transpose(img)
                    process_single_image(img, out, ratio, model)
                    
                    if not os.path.exists(out):
                        print(f"[!] ERREUR : Le fichier {out_name} n'a pas été écrit.")
            except Exception as e:
                print(f"[-] Erreur sur {name} : {e}")
            
            done += 1
            if progress_callback: progress_callback(done, total)

    save_history(used, history_path)
