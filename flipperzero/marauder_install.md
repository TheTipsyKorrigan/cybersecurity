# Installation manuelle de Marauder sur la Flipper WiFi Dev Board (ESP32-S2)

Guide de flash via `esptool` en ligne de commande (Ubuntu/Linux), en cas de souci avec le
flasher web (boot loop, "invalid header", etc.).

## Prérequis

```bash
pip install esptool --break-system-packages
```

Ajoutez votre utilisateur au groupe `dialout` si nécessaire (déconnexion/reconnexion de
session requise après) :

```bash
sudo usermod -aG dialout $USER
```

## 1. Identifier le port série

Débranchez la Dev Board, puis rebranchez-la (elle doit être **seule**, pas clipsée sur
le Flipper, pour ce flash).

```bash
ls /dev/ttyACM* /dev/ttyUSB* 2>/dev/null
```

Notez le port affiché (ex: `/dev/ttyACM0`, `/dev/ttyACM1`...). Il peut changer selon ce
qui est déjà branché (le Flipper lui-même occupe souvent `ttyACM0`).

## 2. Mode bootloader

1. Débranchez le câble USB-C.
2. Maintenez le bouton **BOOT** appuyé.
3. Branchez le câble (en maintenant BOOT).
4. Attendez ~3 secondes.
5. Relâchez **BOOT**.

## 3. Vérifier la communication avec le chip

```bash
esptool --chip esp32s2 --port /dev/ttyACM1 chip-id
```

(adaptez le port). Vous devriez voir les infos du chip (MAC, crystal, etc.) sans erreur.

## 4. Effacer complètement la flash (recommandé)

Évite les résidus de configuration (NVS) d'un firmware précédent qui peuvent causer des
boot loops.

```bash
esptool --chip esp32s2 --port /dev/ttyACM1 erase-flash
```

## 5. Télécharger les binaires Marauder

Depuis [github.com/justcallmekoko/ESP32Marauder/releases](https://github.com/justcallmekoko/ESP32Marauder/releases),
prenez les 4 fichiers de la variante **flipper** (pas WROOM/S3), format "installer" :

- `..._flipper.bootloader.bin`
- `..._flipper.partition-table.bin`
- `..._flipper.ota-data.bin`
- `..._flipper.bin` (firmware principal)

## 6. Flasher

Remettez la carte en mode bootloader (étape 2) si elle a redémarré entre-temps, puis :

```bash
esptool --chip esp32s2 --port /dev/ttyACM1 write-flash \
  0x1000  esp32_marauder_installer_vX_XX_X_YYYYMMDD_flipper.bootloader.bin \
  0x8000  esp32_marauder_installer_vX_XX_X_YYYYMMDD_flipper.partition-table.bin \
  0xd000  esp32_marauder_installer_vX_XX_X_YYYYMMDD_flipper.ota-data.bin \
  0x10000 esp32_marauder_installer_vX_XX_X_YYYYMMDD_flipper.bin
```

(remplacez les noms de fichiers par les vôtres)

| Offset | Fichier |
|---|---|
| `0x1000` | bootloader.bin |
| `0x8000` | partition-table.bin |
| `0xd000` | ota-data.bin |
| `0x10000` | firmware (.bin) |

## 7. Finaliser

1. Débranchez le câble USB-C.
2. Rebranchez normalement (pas besoin de maintenir BOOT cette fois).
3. Appuyez une fois sur **RESET** sur la Dev Board.
4. Clipsez-la sur le Flipper Zero.
5. Sur le Flipper : **Apps → GPIO → ESP32 WiFi Marauder**.

## Dépannage rapide

- **Port introuvable** : vérifiez `ls /dev/ttyACM* /dev/ttyUSB* 2>/dev/null`, essayez un
  autre câble USB-C (certains sont "charge only").
- **`chip-id` échoue / port busy** : fermez qFlipper complètement
  (`pkill -f qFlipper`), vérifiez qu'aucun processus ne tient le port
  (`sudo lsof /dev/ttyACM1`).
- **Boot loop après flash** (`rst:0x3 RTC_SW_SYS_RST` en boucle, "invalid header") :
  refaites un `erase-flash` complet avant de reflasher — évite les partitions NVS
  corrompues d'un firmware précédent.
- **Confirmer que le matériel est sain** : si `esptool chip-id` répond correctement
  (MAC affichée, pas d'erreur), le chip communique bien — un boot loop après ça pointe
  vers le firmware, pas le matériel.