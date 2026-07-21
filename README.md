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

1. Copier `.env.example` en `.env`
2. Renseigner `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD`, `SMTP_FROM`
   avec les identifiants de votre fournisseur email (Gmail avec un "mot de passe
   d'application", Outlook, SendGrid, OVH, etc.)

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
