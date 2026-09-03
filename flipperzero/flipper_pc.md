# Flipper Zero + PC Ubuntu : installation et utilisation

Guide pour connecter, configurer et piloter un Flipper Zero depuis un PC Ubuntu, avec
qFlipper (interface graphique) et `screen` (accès CLI série).

## 1. Prérequis : permissions USB

Le Flipper communique en série USB (`/dev/ttyACM*`). Votre utilisateur doit être dans
le groupe `dialout` pour y accéder sans `sudo`.

```bash
groups $USER
```

Si `dialout` n'apparaît pas dans la liste :

```bash
sudo usermod -aG dialout $USER
```

**Important** : déconnectez-vous et reconnectez-vous (ou redémarrez) — les groupes sont
chargés au login, un simple redémarrage de terminal ne suffit pas.

## 2. Installer qFlipper

Trois méthodes possibles :

### Option A — AppImage (rapide, pas d'installation système)

1. Téléchargez le `.AppImage` Linux depuis les releases GitHub :
   `github.com/flipperdevices/qFlipper/releases/latest`
2. Rendez-le exécutable et lancez-le :

```bash
chmod +x qFlipper-x86_64-*.AppImage
./qFlipper-x86_64-*.AppImage
```

**Erreur fréquente sur Ubuntu 22.04+** : `dlopen(): error loading libfuse.so.2` (FUSE2
n'est plus installé par défaut) :

```bash
sudo apt install libfuse2
# si le paquet n'existe pas sous ce nom :
sudo apt install libfuse2t64
```

### Option B — Paquet .deb (recommandé si l'AppImage pose problème)

```bash
# téléchargez le .deb depuis les releases GitHub, puis :
sudo dpkg -i qFlipper-*.deb
sudo apt-get install -f
```

### Option C — Flatpak

```bash
flatpak install flathub one.flipperzero.qFlipper
```

## 3. Installer les règles udev (accès sans conflit)

Après un premier lancement, qFlipper peut signaler "Device cannot be recognized" avec
une suggestion de règles udev. Installez-les :

```bash
./qFlipper-x86_64-*.AppImage rules install
sudo udevadm control --reload-rules
sudo udevadm trigger
```

Débranchez puis rebranchez le Flipper après cette étape.

## 4. Connecter le Flipper

1. Branchez le Flipper en USB-C au PC.
2. Réveillez l'écran (bouton central) — un Flipper endormi n'apparaît pas toujours
   correctement en USB.
3. Sur l'écran du Flipper, une icône de connexion USB doit apparaître en haut à droite.
4. Ouvrez qFlipper : le Flipper doit apparaître comme connecté, avec son port série
   affiché (ex: `/dev/ttyACM0`).

**Si rien ne se connecte** :

```bash
lsusb          # le Flipper doit apparaître dans la liste
dmesg | tail -15   # rebranchez le câble juste avant, cherchez ttyACM0/ttyACM1
```

Testez un autre câble USB-C — beaucoup sont "charge only" sans lignes de données.

## 5. Utiliser qFlipper

Fonctions principales de l'interface :

- **File Manager** (icône dossier) : parcourir la carte SD et la mémoire interne du
  Flipper, glisser-déposer des fichiers dans les deux sens (ex: récupérer des logs
  d'app dans `SD Card/apps_data/...`).
- **Apps** : installer/mettre à jour des applications compagnon (ex: WiFi Marauder)
  directement depuis le catalogue.
- **Firmware update** : mettre à jour le firmware du Flipper lui-même.
- **Device Info** : version de firmware installée, numéro de série.

Alternative web sans installation : `lab.flipper.net/apps` (Chrome/Edge, via
WebSerial) permet d'installer des apps directement, le Flipper connecté.

## 6. Accès CLI via `screen`

Le Flipper expose une interface en ligne de commande sur son port série USB principal
(`/dev/ttyACM0` typiquement) — différente de la communication GPIO avec un module
externe comme la WiFi Dev Board.

```bash
sudo apt install screen   # si absent
screen /dev/ttyACM0 115200
```

**Important** : qFlipper doit être complètement fermé avant, sinon le port est occupé
("[screen is terminating]" immédiat) :

```bash
pkill -f qFlipper
ps aux | grep -i qflipper   # vérifier qu'il ne reste rien
```

Une fois connecté, tapez `help` ou `?` pour lister les commandes disponibles.

**Quitter `screen` proprement** (sans redémarrer le Flipper) :
`Ctrl+A` puis `K`, puis confirmez avec `y`.

**Enregistrer la session dans un fichier** :

```bash
screen -L -Logfile flipper_session.log /dev/ttyACM0 115200
```

## Dépannage rapide

| Symptôme | Cause probable | Solution |
|---|---|---|
| `libfuse.so.2` manquant | FUSE2 absent sur Ubuntu récent | `sudo apt install libfuse2` (ou `libfuse2t64`) |
| "Device cannot be recognized" | Règles udev manquantes | `./qFlipper*.AppImage rules install` + reload udev |
| Port introuvable (`ls /dev/ttyACM*` vide) | Câble "charge only", port USB défaillant | Changer de câble/port |
| `screen` se ferme immédiatement | Port occupé par qFlipper | `pkill -f qFlipper`, vérifier avec `sudo lsof /dev/ttyACM0` |
| Erreur de permission sur le port | Utilisateur hors groupe `dialout` | `sudo usermod -aG dialout $USER` + reconnexion session |
| ModemManager interfère | Sonde le port en arrière-plan | `sudo systemctl stop ModemManager` |