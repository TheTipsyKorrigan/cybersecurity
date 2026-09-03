# Tester le hardware de la Flipper WiFi Dev Board (ESP32-S2)

Ce guide permet de vérifier que la Dev Board est physiquement saine, indépendamment de
Marauder ou de tout autre firmware — utile en cas de boot loop, d'erreurs de flash, ou
de comportement suspect.

## Prérequis

```bash
pip install esptool --break-system-packages
```

Débranchez la Dev Board du Flipper — tous ces tests se font avec la carte **seule**,
branchée directement en USB-C sur le PC.

## 1. Identifier le port série

```bash
ls /dev/ttyACM* /dev/ttyUSB* 2>/dev/null
```

Notez le port affiché (ex: `/dev/ttyACM0`, `/dev/ttyACM1`...). Il peut changer selon ce
qui est déjà branché (le Flipper lui-même occupe souvent un port séparé s'il est aussi
connecté).

Si rien n'apparaît : vérifiez le câble (certains sont "charge only", sans lignes de
données) et testez un autre port USB.

## 2. Mode bootloader

Nécessaire pour la plupart des commandes esptool.

1. Débranchez le câble USB-C.
2. Maintenez le bouton **BOOT** appuyé.
3. Branchez le câble (en maintenant BOOT).
4. Attendez ~3 secondes.
5. Relâchez **BOOT**.

## 3. Test de base : communication avec le chip

```bash
esptool --chip esp32s2 --port /dev/ttyACM1 chip-id
```

(adaptez le port)

**Résultat attendu** : infos du chip affichées sans erreur — type de chip, fréquence du
crystal, mode USB, adresse MAC, "Stub flasher running". Si cette commande répond
correctement, **le chip communique bien** — c'est le test le plus basique et le plus
fiable pour écarter un problème matériel de communication série.

**Si ça échoue** ("port busy", "could not open port") :

```bash
sudo lsof /dev/ttyACM1
```

Un autre processus (qFlipper, ModemManager, brltty) tient peut-être le port. Fermez-le :

```bash
pkill -f qFlipper
sudo systemctl stop ModemManager
sudo systemctl stop brltty   # si actif
```

## 4. Test de la flash : lecture des infos mémoire

```bash
esptool --chip esp32s2 --port /dev/ttyACM1 flash-id
```

Affiche le fabricant et la taille de la puce flash (ex: 4MB). Si cette commande échoue
alors que `chip-id` fonctionnait, ça peut indiquer un souci spécifique à la puce flash
plutôt qu'au chip principal.

## 5. Test décisif : erase + reboot propre

```bash
esptool --chip esp32s2 --port /dev/ttyACM1 erase-flash
```

Puis, sans reflasher quoi que ce soit, revérifiez que le chip répond toujours :

```bash
esptool --chip esp32s2 --port /dev/ttyACM1 chip-id
```

**Si les deux commandes réussissent** → le hardware (chip + flash + communication USB)
est sain. Un boot loop ultérieur avec un firmware donné (Marauder ou autre) pointe alors
vers un problème logiciel (firmware corrompu, incompatibilité de version, partition NVS
résiduelle), pas vers la carte elle-même.

**Si `chip-id` échoue après l'erase** → suspicion de défaut matériel plus sérieux (flash
défectueuse, mauvais contact GPIO).

## 6. Test avec un firmware minimal (optionnel, le plus concluant)

Pour distinguer complètement "carte défectueuse" de "firmware Marauder incompatible" :

1. Flashez un firmware très simple (ex: un exemple "Hello World" ou "Blink" ESP-IDF/
   Arduino pour ESP32-S2, ou le firmware par défaut proposé par un flasher web comme
   fzeeflasher.com).
2. Observez le comportement au boot via un moniteur série :

```bash
python3 -m serial.tools.miniterm /dev/ttyACM1 115200
```

- **Boot stable, pas de reset en boucle** → le hardware est confirmé sain, le problème
  vient spécifiquement de Marauder (version, build, ou incompatibilité avec cette
  révision de carte).
- **Boot loop même avec un firmware minimal** → la carte a probablement un défaut
  matériel (contact GPIO, résidu de soudure, flash endommagée).

## Lecture des messages de boot

Sur un boot sain, vous devriez voir un firmware démarrer normalement après la séquence
ROM initiale. Sur un boot loop, la même séquence se répète en continu :

```
rst:0x3 (RTC_SW_SYS_RST), boot:0x8 (SPI_FAST_FLASH_BOOT)
ESP-ROM:esp32s2-rc4-20191025
...
entry 0x4004c18c
```

`RTC_SW_SYS_RST` = reset déclenché par le firmware lui-même (crash logiciel), pas par
l'alimentation — ça pointe presque toujours vers un problème de firmware plutôt que de
hardware, surtout si les tests 3 à 5 ci-dessus ont réussi.

## Inspection physique (complément)

- Vérifiez qu'aucune pin GPIO n'est tordue, décalée, ou en court-circuit avec sa
  voisine sur le connecteur qui se clipse au Flipper.
- Vérifiez l'absence de résidu de soudure ou de composant visiblement endommagé sur
  la carte, à la lumière.
- Testez avec un câble USB-C différent et un port USB différent (idéalement un port
  USB-A direct sur le PC plutôt qu'un hub).

## Résumé rapide

| Test | Résultat attendu si hardware OK |
|---|---|
| `chip-id` | Répond avec MAC, pas d'erreur |
| `flash-id` | Répond avec fabricant/taille flash |
| `erase-flash` puis `chip-id` | Les deux réussissent |
| Firmware minimal | Boot stable, pas de reset en boucle |