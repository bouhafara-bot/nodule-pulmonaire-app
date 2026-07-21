# Exemple de contenu à coller dans le fichier WSGI généré par PythonAnywhere
# (onglet "Web" → lien vers le fichier WSGI, ex. /var/www/votrenom_pythonanywhere_com_wsgi.py)
#
# Remplacez "votrenom" par votre nom d'utilisateur PythonAnywhere et adaptez
# le chemin si vous avez cloné le dépôt ailleurs que dans votre home.

import sys

project_home = "/home/votrenom/nodule-pulmonaire-app"
if project_home not in sys.path:
    sys.path.insert(0, project_home)

from app import app as application  # noqa: E402
