import os
import re
import secrets
import smtplib
import threading
from datetime import datetime
from email.mime.text import MIMEText
from pathlib import Path

from flask import Flask, jsonify, render_template, request
from openpyxl import Workbook, load_workbook

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

app = Flask(__name__)

BASE_DIR = Path(__file__).parent
DATA_DIR = Path(os.environ.get("DATA_DIR", str(BASE_DIR / "data")))
DATA_DIR.mkdir(parents=True, exist_ok=True)
EXCEL_PATH = DATA_DIR / "inscriptions.xlsx"

HEADERS = ["Horodatage", "Nom", "Prénom", "Lieu d'exercice", "Email", "Code"]
CODE_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"  # sans 0/O/1/I pour éviter les confusions
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

excel_lock = threading.Lock()


def generate_code(length=8):
    return "".join(secrets.choice(CODE_ALPHABET) for _ in range(length))


def append_inscription(nom, prenom, lieu, email, code):
    with excel_lock:
        if EXCEL_PATH.exists():
            wb = load_workbook(EXCEL_PATH)
            ws = wb.active
        else:
            wb = Workbook()
            ws = wb.active
            ws.title = "Inscriptions"
            ws.append(HEADERS)
        ws.append([datetime.now().strftime("%Y-%m-%d %H:%M:%S"), nom, prenom, lieu, email, code])
        wb.save(EXCEL_PATH)


def find_matching_code(email, code):
    if not EXCEL_PATH.exists():
        return False
    with excel_lock:
        wb = load_workbook(EXCEL_PATH)
        ws = wb.active
        for row in ws.iter_rows(min_row=2, values_only=True):
            row_email, row_code = row[4], row[5]
            if (
                row_email
                and row_code
                and str(row_email).strip().lower() == email.strip().lower()
                and str(row_code).strip().upper() == code.strip().upper()
            ):
                return True
    return False


def send_code_email(to_email, nom, prenom, code):
    host = os.environ.get("SMTP_HOST")
    port = int(os.environ.get("SMTP_PORT", "587"))
    user = os.environ.get("SMTP_USER")
    password = os.environ.get("SMTP_PASSWORD")
    from_addr = os.environ.get("SMTP_FROM", user)

    body = (
        f"Bonjour {prenom} {nom},\n\n"
        "Voici votre code d'accès personnel pour utiliser la calculette "
        "« Nodule pulmonaire — aide à la décision » :\n\n"
        f"    {code}\n\n"
        "Saisissez ce code sur la page d'inscription (avec la même adresse email) "
        "pour accéder à l'outil.\n\n"
        "Cet outil est une aide à la décision et ne remplace pas le jugement clinique.\n"
    )
    msg = MIMEText(body, "plain", "utf-8")
    msg["Subject"] = "Votre code d'accès — Nodule pulmonaire, aide à la décision"
    msg["From"] = from_addr or "noreply@example.com"
    msg["To"] = to_email

    if not host or not user or not password:
        app.logger.warning("SMTP non configuré — code généré pour %s : %s", to_email, code)
        return False

    with smtplib.SMTP(host, port, timeout=10) as server:
        server.starttls()
        server.login(user, password)
        server.sendmail(msg["From"], [to_email], msg.as_string())
    return True


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/healthz")
def healthz():
    return jsonify(ok=True)


@app.route("/api/inscription", methods=["POST"])
def api_inscription():
    data = request.get_json(silent=True) or {}
    nom = (data.get("nom") or "").strip()
    prenom = (data.get("prenom") or "").strip()
    lieu = (data.get("lieu") or "").strip()
    email = (data.get("email") or "").strip()

    if not nom or not prenom or not lieu or not email:
        return jsonify(ok=False, error="Tous les champs sont obligatoires."), 400
    if not EMAIL_RE.match(email):
        return jsonify(ok=False, error="Adresse email invalide."), 400

    code = generate_code()
    try:
        append_inscription(nom, prenom, lieu, email, code)
    except Exception:
        app.logger.exception("Échec de l'écriture dans le fichier Excel")
        return jsonify(ok=False, error="Erreur serveur lors de l'enregistrement."), 500

    try:
        sent = send_code_email(email, nom, prenom, code)
    except Exception:
        app.logger.exception("Échec de l'envoi de l'email")
        sent = False

    return jsonify(ok=True, emailSent=sent)


@app.route("/api/verifier", methods=["POST"])
def api_verifier():
    data = request.get_json(silent=True) or {}
    email = (data.get("email") or "").strip()
    code = (data.get("code") or "").strip()

    if not email or not code:
        return jsonify(ok=False, error="Email et code requis."), 400

    valid = find_matching_code(email, code)
    return jsonify(ok=valid)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "5000"))
    app.run(host="0.0.0.0", port=port, debug=os.environ.get("FLASK_DEBUG") == "1")
