# Mémo VPS + Docker pour l’API Fiscale

Ce mémo résume les commandes que j’utilise pour gérer mon VPS OVH, Docker et mon API FastAPI `fiscal-reform-readiness-api`.

\---

## 1\. Connexion au VPS

### 1.1 Se connecter en SSH

```bash
ssh ubuntu@162.19.246.165
```

* **Ce que ça fait pour moi** : ouvre une session sur mon serveur OVH à distance pour pouvoir lancer toutes les autres commandes.

\---

## 2\. Mise à jour du système

### 2.1 Mettre à jour la liste des paquets

```bash
sudo apt update
```

* **Ce que ça fait pour moi** : demande à Ubuntu la liste la plus récente des paquets disponibles.

### 2.2 Installer les mises à jour

```bash
sudo apt upgrade -y
```

* **Ce que ça fait pour moi** : installe les dernières mises à jour de sécurité et de bugfix sur le VPS.

\---

## 3\. Installation de Docker

### 3.1 Installer les dépendances de base

```bash
sudo apt install -y ca-certificates curl gnupg
```

* **Ce que ça fait pour moi** : installe les outils nécessaires pour ajouter le dépôt officiel Docker.

### 3.2 Ajouter la clé GPG Docker

```bash
sudo install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg   | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
sudo chmod a+r /etc/apt/keyrings/docker.gpg
```

* **Ce que ça fait pour moi** : permet à Ubuntu de vérifier que les paquets Docker viennent bien de la bonne source.

### 3.3 Ajouter le dépôt Docker

```bash
echo   "deb \\\[arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu   $(. /etc/os-release \\\&\\\& echo "${UBUNTU\\\_CODENAME:-$VERSION\\\_CODENAME}") stable"   | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
```

* **Ce que ça fait pour moi** : ajoute le dépôt officiel Docker à la configuration APT de mon VPS.

### 3.4 Installer Docker Engine + plugin Compose

```bash
sudo apt update
sudo apt install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
```

* **Ce que ça fait pour moi** : installe Docker, la CLI Docker, le runtime containerd et le plugin `docker compose`.

### 3.5 Vérifier l’installation

```bash
docker --version
docker compose version
```

* **Ce que ça fait pour moi** : confirme que Docker et Docker Compose sont bien installés et accessibles.

### 3.6 Ajouter mon utilisateur au groupe docker (optionnel mais pratique)

```bash
sudo usermod -aG docker $USER
newgrp docker
```

* **Ce que ça fait pour moi** : me permet de lancer `docker` sans devoir taper `sudo` à chaque fois.

\---

## 4\. Préparer le projet sur le VPS

### 4.1 Créer le dossier de l’application

```bash
mkdir -p \\\~/apps/diagnostic-api
cd \\\~/apps/diagnostic-api
```

* **Ce que ça fait pour moi** : crée un répertoire dédié pour l’API fiscale et m’y place.

### 4.2 Copier les fichiers depuis mon PC (Windows PowerShell)

```powershell
scp fastapi\\\_diagnostic\\\_app.py diagnostic\\\_engine.py diagnostic\\\_mapping.py `
    requirements.txt Dockerfile docker-compose.yml `
    ubuntu@162.19.246.165:\\\~/apps/diagnostic-api/
```

* **Ce que ça fait pour moi** : envoie les fichiers de mon projet Fiscale depuis mon PC vers le VPS.

\---

## 5\. Docker Compose : construire et lancer l’API

*Toutes les commandes suivantes sont exécutées dans* `\\\~/apps/diagnostic-api` *sur le VPS.*

### 5.1 Construire et démarrer les conteneurs

```bash
docker compose up -d --build
```

* **Ce que ça fait pour moi** : construit l’image Docker à partir du Dockerfile et lance l’API en tâche de fond.

### 5.2 Voir l’état des services

```bash
docker compose ps
```

* **Ce que ça fait pour moi** : affiche quels services sont en cours d’exécution et sur quels ports.

### 5.3 Lire les logs des conteneurs

```bash
docker compose logs -f
# ou, si le service s'appelle diagnostic-api :
docker compose logs -f diagnostic-api
```

* **Ce que ça fait pour moi** : me permet de voir les logs en temps réel pour déboguer une erreur (par exemple un HTTP 500).

### 5.4 Arrêter et relancer après une mise à jour du code

```bash
docker compose down
docker compose up -d --build
```

* **Ce que ça fait pour moi** : redémarre proprement l’API après avoir modifié le code source.

\---

## 6\. Pare-feu UFW : ouvrir les ports nécessaires

### 6.1 Autoriser le SSH (port 22) et l’API (port 8000)

```bash
sudo ufw allow 22/tcp
sudo ufw allow 8000/tcp
```

* **Ce que ça fait pour moi** : autorise les connexions entrantes sur le port SSH et sur le port HTTP de mon API.

### 6.2 Activer UFW et vérifier l’état

```bash
sudo ufw enable
sudo ufw status
```

* **Ce que ça fait pour moi** : active le pare-feu Ubuntu et m’affiche quelles règles sont en place.

\---

## 7\. Tester l’API depuis le VPS

### 7.1 Tester le endpoint `/health`

```bash
curl http://127.0.0.1:8000/health
```

* **Ce que ça fait pour moi** : vérifie que l’API répond bien depuis le serveur lui-même.
* **Réponse attendue** : un JSON du type `{"status":"ok","service":"fiscal-reform-readiness-api","version":"1.0.0"}`.

\---

## 8\. Tester l’API depuis mon PC (Windows)

### 8.1 Tester `/health` avec curl

```cmd
curl http://162.19.246.165:8000/health
```

* **Ce que ça fait pour moi** : vérifie que mon API est accessible depuis Internet via l’IP publique du VPS.

### 8.2 Créer un fichier `body.json` pour le diagnostic

Contenu de `body.json` dans mon repo `Fiscale` :

```json
{
  "answers": {
    "Q01": "pme",
    "Q03": "reel\\\_normal",
    "Q05": \\\["b2b\\\_france", "b2c\\\_france"],
    "Q08": "logiciel\\\_facturation",
    "Q09": "pdf\\\_email",
    "Q10": "update\\\_announced",
    "Q12": "partial",
    "Q15": "evaluating",
    "Q16B": "unknown",
    "Q16C": "unknown",
    "Q17": "planned",
    "Q18": "informed\\\_lightly",
    "Q19A": "in\\\_progress",
    "Q19B": "in\\\_progress",
    "Q20": 3
  },
  "max\\\_actions": 3
}
```

* **Ce que ça fait pour moi** : prépare un exemple de réponses pour tester le moteur de diagnostic.

### 8.3 Appeler `/diagnostic` depuis Windows CMD

En se plaçant dans `F:\\\\GitHub\\\\Fiscale` où se trouve `body.json` :

```cmd
curl -X POST http://162.19.246.165:8000/diagnostic ^
  -H "Content-Type: application/json" ^
  -d @body.json
```

* **Ce que ça fait pour moi** : envoie le JSON de test à l’API et affiche le score, le niveau (en\_retard / en\_chemin / pret) et les actions proposées.

\---

## 9\. Résumé rapide des commandes les plus utiles

* Connexion SSH : `ssh ubuntu@162.19.246.165`
* Mise à jour : `sudo apt update \\\&\\\& sudo apt upgrade -y`
* Vérifier Docker : `docker --version`, `docker compose version`
* Lancer l’API : `docker compose up -d --build`
* Voir l’état : `docker compose ps`
* Logs en temps réel : `docker compose logs -f`
* Ouvrir le port 8000 : `sudo ufw allow 8000/tcp`
* Healthcheck depuis le VPS : `curl http://127.0.0.1:8000/health`
* Healthcheck depuis mon PC : `curl http://162.19.246.165:8000/health`
* Diagnostic depuis mon PC : `curl -X POST http://162.19.246.165:8000/diagnostic -H "Content-Type: application/json" -d @body.json`



cd \~/apps/diagnostic-api

ls -la





cd \~/Fiscale → aller dans le bon dossier projet



docker compose ps → voir les conteneurs



docker compose logs -f → suivre les logs en temps réel



curl ... /diagnostic → déclencher la requête qui fait planter ou non l’API

```


