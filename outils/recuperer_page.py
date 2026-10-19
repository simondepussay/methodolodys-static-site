"""Ajoute à la sauvegarde une page publiée sur le site WordPress APRÈS la sauvegarde.

    python3 recuperer_page.py complementlettreharmos

La page est lue sur methodolodys.ch (API WordPress) et ajoutée à analyse/posts.json,
comme si elle avait été dans la sauvegarde. Ses fichiers (PDF, images…) doivent être
téléchargés à part dans extrait/uploads/ : le script affiche ceux qui manquent.
Il faut ensuite ajouter la page dans THEMES (extraire.py) et relancer la chaîne habituelle.
"""
import json
import os
import re
import sys
import urllib.parse
import urllib.request
from html import unescape

from extraire import SAUVEGARDE, UPLOADS, chemin_upload


def retablir_shortcodes(contenu):
    """L'API renvoie les balises Divi « embellies » par WordPress : = »x » au lieu de ="x".
    On remet de vrais guillemets à l'intérieur des balises [et_pb_…]."""
    def reparer(m):
        balise = unescape(m.group(0))
        balise = re.sub(r"=\s*[«»“”″]\s*", '="', balise)
        balise = re.sub(r"\s*[«»“”″](?=\s|\]|$)", '"', balise)
        return balise
    contenu = re.sub(r"\[/?et_pb_[^\]]*\]", reparer, contenu)
    # wpautop a entouré les balises de <p> et <br> : sans importance pour l'extraction
    return contenu


def main(slug_page):
    url = f"https://methodolodys.ch/wp-json/wp/v2/pages?slug={urllib.parse.quote(slug_page)}"
    with urllib.request.urlopen(url, timeout=60) as reponse:
        pages = json.load(reponse)
    if not pages:
        sys.exit(f"Page « {slug_page} » introuvable sur le site.")
    p = pages[0]
    post = {
        "ID": str(p["id"]),
        "post_name": p["slug"],
        "post_title": unescape(p["title"]["rendered"]),
        "post_content": retablir_shortcodes(p["content"]["rendered"]),
        "post_date": p["date"].replace("T", " "),
        "post_modified": p["modified"].replace("T", " "),
        "post_parent": str(p["parent"]),
        "post_status": "publish",
        "post_type": "page",
        "guid": p["link"],
    }
    chemin = os.path.join(SAUVEGARDE, "analyse", "posts.json")
    posts = [x for x in json.load(open(chemin)) if not (x["post_type"] == "page" and x["post_name"] == slug_page)]
    posts.append(post)
    with open(chemin, "w") as f:
        json.dump(posts, f, ensure_ascii=False)
    print(f"Page « {post['post_title']} » ajoutée à la sauvegarde.")

    manquants = sorted({c for c in (chemin_upload(u) for u in re.findall(
        r"wp-content/uploads/[^\"'\s\])<>]+", post["post_content"])) if c
        and not os.path.exists(os.path.join(UPLOADS, "uploads", c))})
    if manquants:
        print("Fichiers à télécharger dans extrait/uploads/ :")
        for c in manquants:
            print("  ", c)


if __name__ == "__main__":
    main(sys.argv[1])
