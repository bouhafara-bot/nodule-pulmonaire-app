# Nodule pulmonaire — aide à la décision (avec inscription)

Application web une page : inscription (nom, prénom, lieu d'exercice, email) →
envoi d'un code d'accès unique par email → saisie du code → accès à la calculette
(Fleischner / Brock / VDT / Repères / Biopsie). Chaque inscription est enregistrée
dans `data/inscriptions.xlsx`.

## Lancer en local

```
python -m pip install -r requirements.txt
python app.py
```

Puis ouvrir http://localhost:5000

Sans configuration SMTP, l'application fonctionne quand même : le code généré
est simplement écrit dans le terminal (log serveur) au lieu d'être envoyé par
email — pratique pour tester le parcours complet avant d'avoir des identifiants
email définitifs.

## Configurer l'envoi d'email

Deux méthodes possibles (l'app essaie SendGrid en premier, puis le SMTP
classique si SendGrid n'est pas configuré) :

**Via SMTP classique** — copier `.env.example` en `.env` et renseigner
`SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD`, `SMTP_FROM` avec les
identifiants de votre fournisseur (Gmail avec un "mot de passe d'application",
Outlook, OVH, etc.). Fonctionne sur la plupart des hébergeurs, **mais pas sur
PythonAnywhere gratuit** (voir plus bas).

**Via l'API SendGrid** (nécessaire sur PythonAnywhere gratuit) — renseigner
`SENDGRID_API_KEY` et `SENDGRID_FROM` (l'adresse d'expéditeur doit être
vérifiée dans votre compte SendGrid : "Sender Authentication" → "Single Sender
Verification"). SendGrid propose 100 emails/jour gratuits. Cette méthode passe
par une requête HTTPS classique, pas par une connexion SMTP directe.

## Déployer en ligne

Cette application est un serveur Flask classique (pas une fonction serverless) :
elle a besoin d'un **disque persistant** pour conserver `data/inscriptions.xlsx`
entre les redémarrages. Sans disque persistant, le fichier Excel serait effacé
à chaque redéploiement ou redémarrage du service.

⚠️ Sur Render et Railway, le disque persistant n'est disponible qu'à partir
d'un plan payant (quelques dollars/mois) — il n'y a pas d'option gratuite
pour ce besoin précis.

Le dossier contient déjà :
- `Procfile` — commande de démarrage (`gunicorn app:app --bind 0.0.0.0:$PORT`)
- `render.yaml` — configuration Render prête à l'emploi (service + disque + variables)
- `railway.toml` — configuration Railway (build/démarrage)
- `.gitignore` — exclut `.env` et les fichiers Excel du dépôt Git

### Étape commune : dépôt Git

Le dépôt Git local a été initialisé dans ce dossier. Il vous reste à créer un
dépôt vide sur GitHub (via votre compte) puis à le relier :

```
git remote add origin <URL-de-votre-dépôt-GitHub>
git branch -M main
git push -u origin main
```

(Demandez-moi de pousser si vous préférez que je le fasse une fois le dépôt distant créé.)

### Option A — Render

1. Créez un compte sur render.com et connectez votre compte GitHub.
2. "New" → "Blueprint" → sélectionnez ce dépôt : Render lit `render.yaml`
   automatiquement et propose le service + le disque persistant (1 Go monté
   sur `/var/data`).
3. Choisissez le plan payant "Starter" (le disque persistant l'exige).
4. Dans l'onglet "Environment" du service, renseignez les valeurs manquantes :
   `SMTP_HOST`, `SMTP_USER`, `SMTP_PASSWORD`, `SMTP_FROM`.
5. Déployez. L'URL publique est fournie par Render (ex. `nodule-pulmonaire.onrender.com`).

### Option B — Railway

1. Créez un compte sur railway.app et connectez votre compte GitHub (ou
   installez la CLI Railway pour déployer sans GitHub : `npm i -g @railway/cli`).
2. "New Project" → "Deploy from GitHub repo" (ou `railway init` puis `railway up`
   depuis ce dossier si vous utilisez la CLI).
3. Ajoutez un **volume** (Settings → Volumes) monté sur `/data`, puis définissez
   la variable d'environnement `DATA_DIR=/data`.
4. Renseignez les variables `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`,
   `SMTP_PASSWORD`, `SMTP_FROM` dans l'onglet "Variables".
5. Railway assigne automatiquement `PORT` — rien à faire, `Procfile` s'en sert déjà.
6. Générez un domaine public dans "Settings → Networking → Generate Domain".

### Option C — PythonAnywhere (gratuit à vie)

Aucune carte bancaire requise, stockage persistant inclus dans votre compte —
mais le plan gratuit ("Beginner") **bloque les connexions SMTP sortantes**.
D'où l'ajout du support SendGrid (API HTTPS) dans `app.py`, qui fonctionne sur
ce plan.

1. Créez un compte gratuit sur [pythonanywhere.com](https://www.pythonanywhere.com).
2. Ouvrez une **Bash console** (onglet "Consoles" → "Bash") et clonez votre
   dépôt GitHub :
   ```
   git clone <URL-de-votre-dépôt-GitHub> nodule-pulmonaire-app
   cd nodule-pulmonaire-app
   ```
   (Si vous n'avez pas encore poussé le code sur GitHub, voir l'étape commune
   ci-dessus — ou utilisez l'onglet "Files" pour uploader les fichiers un par un.)
3. Créez un environnement virtuel et installez les dépendances :
   ```
   mkvirtualenv --python=/usr/bin/python3.10 nodule-venv
   pip install -r requirements.txt
   ```
4. Créez le fichier `.env` directement sur le serveur (onglet "Files", dans le
   dossier du projet) avec vos vraies valeurs `SENDGRID_API_KEY` et
   `SENDGRID_FROM` (ce fichier n'est jamais poussé sur GitHub grâce au
   `.gitignore`).
5. Onglet "Web" → "Add a new web app" → "Manual configuration" → Python 3.10.
6. Dans la section "Virtualenv", indiquez le chemin de l'environnement créé à
   l'étape 3 (ex. `/home/votrenom/.virtualenvs/nodule-venv`).
7. Cliquez sur le lien du fichier WSGI et remplacez son contenu par celui de
   [wsgi_pythonanywhere_example.py](wsgi_pythonanywhere_example.py) (en
   adaptant `votrenom` et le chemin du projet).
8. Cliquez sur "Reload" en haut de l'onglet "Web". Votre site est en ligne sur
   `https://votrenom.pythonanywhere.com`.

Avant de vous fier au SMTP classique ou à une API email tierce sur ce plan,
vérifiez la liste des sites autorisés en sortie depuis votre compte (menu
"Account" → lien "IP addresses & whitelisting", ou la page
`pythonanywhere.com/whitelist/` une fois connecté) — elle peut évoluer, et
c'est la source de vérité, pas ce document.

Je ne peux pas créer ces comptes, entrer vos identifiants ou effectuer un
paiement à votre place — ces étapes sont à faire de votre côté. Une fois un
compte/dépôt créé, je peux vous aider à vérifier la configuration, déboguer un
échec de déploiement, ou pousser le code si vous me donnez le feu vert.

## Fichier Excel des inscriptions

`data/inscriptions.xlsx` — une ligne par inscription : Horodatage, Nom,
Prénom, Lieu d'exercice, Email, Code. Ce fichier sert aussi à vérifier les
codes saisis (email + code doivent correspondre à une ligne).

## Sécurité

- Le code d'accès fait 8 caractères alphanumériques (sans caractères ambigus),
  soit plus de mille milliards de combinaisons — un brute-force via le
  formulaire web n'est pas réaliste.
- Ce n'est pas un système d'authentification à haute sécurité : il convient
  à un usage professionnel/interne (partage d'un outil d'aide à la décision
  entre confrères), pas à des données patient identifiables.
