#!/bin/bash

# Script, das die MRC-Dateien von Sharepoint in die Stage verschiebt

# Den Sharepoint-Ordner mounten
if [[ $(findmnt -M /home/schuhs/.HSS) ]]; then
    echo "Sharepoint-Ordner bereits gemounted."
else
    echo "Mounte Sharepoint-Ordner"
    mount /home/schuhs/.HSS
fi

# Laufwerk Y mounten
if [[ $(findmnt -M /home/schuhs/Y) ]]; then
    echo "Laufwerk Y bereits gemounted."
else
    echo "Mounte Laufwerk Y."
    mount /home/schuhs/Y
fi

# Die Dateien vom Sharepoint-Ordner auf in den Stage-Ordner verschieben
echo "Verschiebe Dateien nach /home/schuhs/Y/HOCHSCHULSCHRIFTEN/Alma/stage/"
mv /home/schuhs/.HSS/*.mrc /home/schuhs/Y/HOCHSCHULSCHRIFTEN/Alma/stage/

# Den Sharepoint-Ordner aushängen
echo "Unmount Sharepoint-Ordner"
umount /home/schuhs/.HSS
