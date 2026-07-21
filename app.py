import os
import re
import secrets
import smtplib
import threading
from datetime import datetime
from email.mime.text import MIMEText
from pathlib import Path

import requests
from flask import Flask, jsonify, render_template, request
from openpyxl import Workbook, load_workbook

BASE_DIR = Path(__file__).resolve().parent

try:
    from dotenv import load_dotenv
    load_dotenv(BASE_DIR / ".env")
except ImportError:
    pass

app = Flask(__name__)

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


EMAIL_SUBJECT = "Votre code d'accès — Nodule pulmonaire, aide à la décision"


def _email_body(nom, prenom, code):
    return (
        f"Bonjour {prenom} {nom},\n\n"
        "Voici votre code d'accès personnel pour utiliser la calculette "
        "« Nodule pulmonaire — aide à la décision » :\n\n"
        f"    {code}\n\n"
        "Saisissez ce code sur la page d'inscription (avec la même adresse email) "
        "pour accéder à l'outil.\n\n"
        "Cet outil est une aide à la décision et ne remplace pas le jugement clinique.\n"
    )


def send_via_smtp(to_email, nom, prenom, code):
    host = os.environ.get("SMTP_HOST")
    port = int(os.environ.get("SMTP_PORT", "587"))
    user = os.environ.get("SMTP_USER")
    password = os.environ.get("SMTP_PASSWORD")
    from_addr = os.environ.get("SMTP_FROM", user)

    if not host or not user or not password:
        return None  # SMTP non configuré

    msg = MIMEText(_email_body(nom, prenom, code), "plain", "utf-8")
    msg["Subject"] = EMAIL_SUBJECT
    msg["From"] = from_addr or "noreply@example.com"
    msg["To"] = to_email

    with smtplib.SMTP(host, port, timeout=10) as server:
        server.starttls()
        server.login(user, password)
        server.sendmail(msg["From"], [to_email], msg.as_string())
    return True


def send_via_sendgrid(to_email, nom, prenom, code):
    api_key = os.environ.get("SENDGRID_API_KEY")
    from_addr = os.environ.get("SENDGRID_FROM")

    if not api_key or not from_addr:
        return None  # SendGrid non configuré

    resp = requests.post(
        "https://api.sendgrid.com/v3/mail/send",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        json={
            "personalizations": [{"to": [{"email": to_email}]}],
            "from": {"email": from_addr},
            "subject": EMAIL_SUBJECT,
            "content": [{"type": "text/plain", "value": _email_body(nom, prenom, code)}],
        },
        timeout=10,
    )
    if not resp.ok:
        app.logger.error("SendGrid a refusé l'envoi (%s) : %s", resp.status_code, resp.text)
        resp.raise_for_status()
    return True


def send_code_email(to_email, nom, prenom, code):
    """Essaie SendGrid (API HTTP, fonctionne même quand le SMTP sortant est
    bloqué, ex. PythonAnywhere gratuit), puis SMTP classique si configuré."""
    for sender in (send_via_sendgrid, send_via_smtp):
        result = sender(to_email, nom, prenom, code)
        if result is True:
            return True
    app.logger.warning("Aucun envoi d'email configuré — code généré pour %s : %s", to_email, code)
    return False


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
