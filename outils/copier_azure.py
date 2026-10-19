"""Remplit le dossier azure/ avec exactement les fichiers cités par le site :
ceux de site/data/ressources.json et les liens « fichier:… » des pages HTML.

Les fichiers sont des clones APFS (cp -c) : ils ne prennent pas de place en plus sur le disque.
Les noms sont ceux de ressources.json (accents réparés), pas ceux de la sauvegarde WordPress.
"""
import glob
import json
import os
import re
import shutil
from html import unescape
import subprocess

from extraire import PROJET, SITE, index_fichiers

AZURE = os.path.join(PROJET, "azure")


def main():
    ressources = json.load(open(os.path.join(SITE, "data", "ressources.json")))["ressources"]
    fichiers = index_fichiers()
    voulus = {r["fichier"] for r in ressources}
    for page in glob.glob(os.path.join(SITE, "*.html")):
        voulus |= {unescape(f) for f in re.findall(r'href="fichier:([^"]+)"', open(page, encoding="utf-8").read())}
    if os.path.isdir(AZURE):
        shutil.rmtree(AZURE)
    for f in sorted(voulus):
        dest = os.path.join(AZURE, f)
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        subprocess.run(["cp", "-c", fichiers[f], dest], check=True)
    taille = sum(os.path.getsize(os.path.join(AZURE, f)) for f in voulus)
    print(f"{len(voulus)} fichiers dans azure/ ({taille / 1e9:.2f} Go)")


if __name__ == "__main__":
    main()
