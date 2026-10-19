"""Extrait le contenu de l'ancien site WordPress vers site/data/ressources.json.

Lit analyse/posts.json (table posts de la sauvegarde) et parcourt le contenu Divi de
chaque page, dans l'ordre : titres, textes, images, vidéos et fichiers à télécharger.
- Chaque fichier (PDF, PowerPoint…) devient une « ressource » (liste à plat, pour la recherche).
- Chaque page devient une suite de « blocs » (titre, texte, image, vidéo, fiches) pour l'affichage.
Les images sont converties en WebP dans site/images/.
"""
import json
import os
import re
import subprocess
import tempfile
import unicodedata
import urllib.parse
from html import unescape

from nettoyage import nettoyer_html, texte_seul

ICI = os.path.dirname(os.path.abspath(__file__))
PROJET = os.path.dirname(ICI)
SAUVEGARDE = os.path.expanduser("~/Desktop/site mamrtine")
UPLOADS = os.path.join(SAUVEGARDE, "extrait")
SITE = os.path.join(PROJET, "site")

# Regroupement identique au menu du site actuel : thème -> pages WordPress (dans l'ordre).
# Chaque page : (ancienne page WordPress, titre, nom court, page parente facultative).
# Le nom court donne le fichier : « conjugaison » dans le thème « francais » -> francais-conjugaison.html.
# Un nom court vide : la page est affichée sur la page du thème elle-même (francais.html…).
THEMES = [
    ("francais", "Français", [
        ("complementlettreharmos", "Complément méthode d'apprentissage de la lecture 3 Harmos", "complement-3h"),
        ("lecture-technique", "Lecture technique : les lettres de base", "lettres"),
        ("lecture-technique-2", "Lecture technique : digrammes et trigrammes", "digrammes"),
        ("6393-2", "Lecture : complément « transcrire »", "transcrire", "lecture-technique"),
        ("lecture-comprehension", "Lecture compréhension", "comprehension"),
        ("a-la-poursuite-de-bouba", "À la poursuite de Bouba", "bouba", "lecture-comprehension"),
        ("sur-le-chemin-de-la-piscine", "Sur le chemin de la piscine", "piscine", "lecture-comprehension"),
        ("antoine-de-saint-exupery-dessine-moi-un-mouton", "Dessine-moi un mouton", "mouton", "lecture-comprehension"),
        ("pourquoi-le-rouge-gorge", "Pourquoi le rouge-gorge", "rouge-gorge", "lecture-comprehension"),
        ("structure-dun-texte", "Structure d'un texte", "structure-texte", "lecture-comprehension"),
        ("orthographe", "Orthographe", "orthographe"),
        ("conjugaison", "Conjugaison", "conjugaison"),
        ("5950-2", "Le jardin des verbes", "jardin-des-verbes", "conjugaison"),
        ("grammaire", "Grammaire", "grammaire"),
        ("ecriture", "Écriture", "ecriture"),
    ]),
    ("maths", "Mathématiques", [
        ("maths", "J'apprends les maths", "bases"),
        ("programme-entrainement-mathematiques-4p-harmos-8ans", "Programme 4P HARMOS / 8 ans", "programme-4p"),
        ("programme-dentrainement-maths-5p-harmos", "Programme 5P HARMOS", "programme-5p"),
        ("programme-dentrainement-maths-9-ans-france", "Programme 9 ans (France)", "programme-9-ans"),
        ("programme-entrainement-mathematiques-6p-harmos", "Programme 6P HARMOS / 10 ans", "programme-6p"),
        ("fiches-dentrainement-3p-4p-5p-6p", "Fiches d'entraînement 3P à 6P", "fiches-3p-6p"),
        ("fiches-dentrainement-4p-5p-6p", "Fiches d'entraînement 4P à 6P", "fiches-4p-6p"),
    ]),
    ("sciences", "Sciences, Histoire, Géographie", [
        ("sciences", "Sciences", "naturelles"),
        ("histoire", "Histoire", "histoire"),
        ("geographie", "Géographie", "geographie"),
    ]),
    ("temps", "Étude du temps qui passe", [
        ("etude-du-temps-qui-passe", "Étude du temps qui passe", ""),
    ]),
    ("allemand", "J'apprends l'allemand", [
        ("allemand", "J'apprends l'allemand", ""),
    ]),
    ("musique", "Musique et chants", [
        ("musique-et-chants", "Musique et chants", ""),
    ]),
    ("dictionnaire", "Dictionnaire visuo-sémantique", [
        ("dictionnaire-visuo-semantique", "Dictionnaire visuo-sémantique", ""),
    ] + [(f"la-lettre-{l}", f"La lettre {l.upper()}", l, "dictionnaire-visuo-semantique") for l in "abcdefghijklmnopqrstvyz"]),
    ("tutoriels", "Tutoriels vidéos", [
        ("tutoriels", "Tutoriels vidéos", "youtube"),
        ("films-methode-diji", "Films méthode DIJI", "films-diji"),
    ]),
]


# Fiches qui n'étaient proposées que sur l'ancienne page d'accueil : on les range dans la bonne page.
# page -> [(titre de section, titre de la fiche, fichier)]
AJOUTS = {
    "ecriture": [
        ("Les majuscules et les chiffres", "Les majuscules", "2023/08/écriture-Majuscules.pdf"),
        ("Les majuscules et les chiffres", "Les chiffres", "2023/10/les-chiffres.pdf"),
    ],
}


def fichier_page(theme, court):
    return f"{theme}-{court}.html" if court else f"{theme}.html"


# Pages de texte (hors thèmes) : ancienne page WordPress -> nouvelle adresse.
PAGES_TEXTE = {
    "instituteurs-professeurs": "vous-etes.html#enseignants",
    "parents-denfants-dys": "vous-etes.html#parents",
    "autodidacte-dys": "vous-etes.html#autodidacte",
    "othophoniste": "vous-etes.html#orthophoniste",
    "introduction": "a-propos.html#introduction",
    "mes-invites": "a-propos.html#invites",
    "marlyse-narbel": "a-propos.html#invites",
    "cours-formation-continue": "a-propos.html#formation",
    "mes-collaborateurs": "a-propos.html#collaborations",
    "pour-en-savoir-plus": "a-propos.html#liens",
    "medias": "a-propos.html#medias",
    "mentions-legales": "mentions-legales.html",
    "contact": "index.html#contact",
    "tous-vos-outils": "index.html#ressources",
    "actualites": "index.html",
}

EXT_DOC = re.compile(r"\.(pdf|pptx?|docx?|xlsx?|zip|mp3|mp4|m4v)$", re.I)
EXT_IMG = re.compile(r"\.(jpe?g|png|gif|webp)$", re.I)
YOUTUBE = re.compile(r"(?:youtube(?:-nocookie)?\.com/(?:embed/|watch\?v=)|youtu\.be/)([\w-]{11})")


def nfc(s):
    return unicodedata.normalize("NFC", s)


def corriger(chemin):
    """Répare les accents enregistrés de travers (« Pre╠üsent » pour « Présent »).
    Ça touche aussi certains noms de fichiers sur le disque, d'où son usage dans index_fichiers."""
    if "╠" in chemin:
        try:
            chemin = chemin.encode("cp437").decode("utf-8")
        except (UnicodeEncodeError, UnicodeDecodeError):
            pass
    return nfc(chemin)


def chemin_upload(url):
    """'https://…/wp-content/uploads/2016/09/a.pdf?x' -> '2016/09/a.pdf' (ou None)."""
    m = re.search(r"wp-content/uploads/([^?#]+)", url.strip())
    return corriger(urllib.parse.unquote(m.group(1))) if m else None


def nettoyer_titre(titre):
    """« Présent .pdf » -> « Présent » : le type de fichier est affiché à part."""
    titre = " ".join(unescape(titre).split())
    return re.sub(r"\s*\.?(pdf|docx?|pptx?)$", "", titre, flags=re.I).strip(" -–:") or titre


def slug(texte):
    t = unicodedata.normalize("NFD", texte.lower())
    t = "".join(c for c in t if unicodedata.category(c) != "Mn")
    return re.sub(r"[^a-z0-9]+", "-", t).strip("-")[:60]


def index_fichiers():
    idx = {}
    for root, _, fichiers in os.walk(os.path.join(UPLOADS, "uploads")):
        for f in fichiers:
            full = os.path.join(root, f)
            idx[corriger(os.path.relpath(full, os.path.join(UPLOADS, "uploads")))] = full
    return idx


class Convertisseur:
    """Ce qui transforme les liens et images de l'ancien site vers le nouveau."""

    def __init__(self):
        self.fichiers = index_fichiers()
        self.page_de = {s: fichier_page(t, court) for t, _, liste in THEMES for s, _, court, *_ in liste}

    def fichier(self, url):
        """Chemin d'un fichier à télécharger qui existe, ou None. Répare les adresses collées."""
        if "wp-content/uploads" not in url:
            return None
        for morceau in re.split(r"(?=https?://)|(?<=\.pdf)(?=p-content)", url):
            if "wp-content/uploads" not in morceau:
                morceau = "wp-content/uploads/" + morceau.split("uploads/")[-1]
            p = chemin_upload(morceau)
            if p and p in self.fichiers and EXT_DOC.search(p):
                return p
        return None

    def image(self, url, dossier, largeur):
        """Convertit une image de l'ancien site en WebP ; renvoie son chemin dans le site."""
        chemin = chemin_upload(url or "")
        if not chemin or chemin not in self.fichiers or not EXT_IMG.search(chemin):
            return None
        nom = slug(os.path.splitext(chemin)[0]) + ".webp"
        dest = os.path.join(SITE, "images", dossier, nom)
        if not os.path.exists(dest):
            os.makedirs(os.path.dirname(dest), exist_ok=True)
            source = self.fichiers[chemin]
            if source.lower().endswith(".gif"):  # cwebp ne lit pas les GIF : on passe par un PNG
                from PIL import Image
                source = dest + ".png"
                Image.open(self.fichiers[chemin]).convert("RGBA").save(source)
            subprocess.run(["cwebp", "-quiet", "-q", "75", "-resize", str(largeur), "0",
                            source, "-o", dest], check=False)
            if source.endswith(".webp.png"):
                os.remove(source)
            if not os.path.exists(dest):
                return None
        return f"images/{dossier}/{nom}"

    def apercu_document(self, fichier):
        """Aperçu fabriqué à partir du fichier lui-même : la 1re page d'un PDF (sips), ou l'aperçu
        Quick Look de macOS pour un Word, un PowerPoint ou une vidéo."""
        if fichier.lower().endswith(".mp3"):
            return None
        nom = "doc-" + slug(os.path.splitext(fichier)[0]) + ".webp"
        dest = os.path.join(SITE, "images", "apercus", nom)
        if os.path.exists(dest):
            return f"images/apercus/{nom}"
        source = self.fichiers[fichier]
        with tempfile.TemporaryDirectory() as tmp:
            png = os.path.join(tmp, "page.png")
            if fichier.lower().endswith(".pdf"):
                subprocess.run(["sips", "-s", "format", "png", "-Z", "800", source, "--out", png],
                               capture_output=True, check=False)
            else:
                subprocess.run(["qlmanage", "-t", "-s", "800", "-o", tmp, source], capture_output=True, check=False)
                vignettes = [f for f in os.listdir(tmp) if f.endswith(".png")]
                if vignettes:
                    png = os.path.join(tmp, vignettes[0])
            if not os.path.exists(png):
                return None
            os.makedirs(os.path.dirname(dest), exist_ok=True)
            subprocess.run(["cwebp", "-quiet", "-q", "72", "-resize", "400", "0", png, "-o", dest], check=False)
        return f"images/apercus/{nom}" if os.path.exists(dest) else None

    def lien(self, href):
        """Nouvelle adresse d'un lien, ou None s'il ne mène plus nulle part."""
        href = unescape(href or "").strip()
        if not href or href.startswith("#"):
            return None
        if not re.match(r"^[a-z]+:", href, re.I):  # lien relatif de l'ancien site (« contact/ »)
            href = "https://methodolodys.ch/" + href.lstrip("./")
        if "wp-content/uploads" in href:
            f = self.fichier(href)
            if f:
                return "fichier:" + f
            return self.image(href, "pages", 1200)
        m = re.match(r"https?://(?:www\.)?methodolodys\.ch/(?:project/)?([^/#?]*)/?(?:#(.*))?", href)
        if m:
            ancienne = m.group(1)
            if ancienne in self.page_de:
                return self.page_de[ancienne]
            if ancienne in PAGES_TEXTE:
                return PAGES_TEXTE[ancienne]
            return "index.html" if ancienne == "" else None
        if "P7SfXW-qO" in href or "page_id=1662" in href:  # lien court vers les lettres du dictionnaire
            return "dictionnaire-a.html"
        if "wp.me/" in href:
            return None
        return href

    def html(self, html):
        html = re.sub(r"\[/?et_pb_[^\]]*\]", "", html)  # restes de balises Divi
        return nettoyer_html(html, self.lien, lambda src: self.image(src, "pages", 800))


class Page:
    """Construit la suite de blocs d'une page et ses ressources."""

    def __init__(self, conv, slug_page, titres_page, ressources, dates):
        self.conv = conv
        self.id = slug_page
        self.titres_page = {slug(t) for t in titres_page if t}
        self.ressources = ressources
        self.dates = dates
        self.blocs = []
        self.section = None
        self.vus = set()

    # --- ajout de blocs ---

    def titre(self, html, niveau):
        texte = " ".join(texte_seul(html).split())
        if not texte or slug(texte) in self.titres_page:
            return
        self.section = texte
        self.blocs.append({"t": "titre", "texte": texte, "niveau": niveau, "ancre": slug(texte)})

    def texte(self, html):
        propre = self.conv.html(html)
        if texte_seul(propre) or "<img" in propre:
            self.blocs.append({"t": "texte", "html": propre})

    def image(self, url, legende=""):
        if re.search(r"favicon|logo", url or "", re.I):  # petites icônes décoratives
            return
        src = self.conv.image(url, "pages", 800)
        if src:
            self.blocs.append({"t": "image", "src": src, "alt": legende})

    def video(self, youtube_id, titre=""):
        if not any(b.get("youtube") == youtube_id for b in self.blocs):
            self.blocs.append({"t": "video", "youtube": youtube_id, "titre": titre or self.section or ""})

    def fiche(self, titre, fichier, image_url=None):
        if fichier in self.vus:
            return
        self.vus.add(fichier)
        m = re.match(r"(\d{4})/(\d{2})/", fichier)
        r = {
            "id": len(self.ressources),
            # Un libellé comme « cliquez ici » ne veut rien dire seul : on prend le titre de la section.
            "titre": (None if re.fullmatch(r"(cliquez ici|cliquer ici|ici|télécharger( le pdf)?|pdf)\W*",
                                           nettoyer_titre(titre), re.I) else nettoyer_titre(titre))
            or (self.section and re.sub(r"\s*à télécharger\s*$", "", self.section, flags=re.I))
            or os.path.splitext(os.path.basename(fichier))[0].replace("-", " "),
            "fichier": fichier,
            "type": fichier.rsplit(".", 1)[-1].lower(),
            "taille": os.path.getsize(self.conv.fichiers[fichier]),
            "image": (self.conv.image(image_url, "apercus", 400) if image_url else None)
            # (le dictionnaire s'affiche en liste de mots : pas besoin d'aperçu)
            or (None if self.id.startswith("la-lettre-") else self.conv.apercu_document(fichier)),
            "page": self.id,
            "section": self.section,
            "date": self.dates.get(fichier) or (f"{m.group(1)}-{m.group(2)}-01" if m else None),
        }
        self.ressources.append(r)
        if self.blocs and self.blocs[-1]["t"] == "fiches":
            self.blocs[-1]["ids"].append(r["id"])
        else:
            self.blocs.append({"t": "fiches", "ids": [r["id"]]})

    # --- lecture du HTML d'un module texte ---

    def contenu_html(self, html):
        """Découpe le HTML en titres, vidéos, liens vers des fichiers et texte."""
        morceaux = re.split(r"(<h[1-5][^>]*>.*?</h[1-5]>|<iframe[^>]*>(?:</iframe>)?)", html, flags=re.S)
        for m in morceaux:
            if not m.strip():
                continue
            if m.startswith("<iframe"):
                y = YOUTUBE.search(m)
                if y:
                    self.video(y.group(1))
                continue
            titre = re.match(r"<h([1-5])", m)
            liens = [(h, lib) for h, lib in re.findall(r'<a [^>]*href="([^"]+)"[^>]*>(.*?)</a>', m, re.S)
                     if self.conv.fichier(h)]
            if titre and not liens:
                self.titre(m, 2 if titre.group(1) in "12" else int(titre.group(1)))
                continue
            # Vidéos YouTube collées en adresse simple (WordPress les affichait en lecteur)
            for y in re.findall(r"(?m)^\s*(?:<p>)?\s*(https?://(?:www\.)?(?:youtube\.com/watch\?v=|youtu\.be/)[\w-]{11}\S*)", m):
                self.video(YOUTUBE.search(y).group(1))
                m = m.replace(y, "")
            if liens:
                # Ce qui reste une fois les liens retirés : s'il y a du vrai texte, on le garde.
                reste = re.sub(r'<a [^>]*href="([^"]+)"[^>]*>.*?</a>',
                               lambda a: "" if self.conv.fichier(a.group(1)) else a.group(0), m, flags=re.S)
                if len(texte_seul(reste)) > 3:
                    self.texte(reste)
                for h, lib in liens:
                    self.fiche(texte_seul(lib), self.conv.fichier(h))
            else:
                self.texte(m)

    # --- lecture des modules Divi ---

    def lire(self, contenu):
        if "[et_pb_" not in contenu:  # page écrite sans Divi : du HTML simple
            self.contenu_html(contenu)
            return
        modules = re.finditer(
            r"\[(et_pb_(?:text|blurb|button|image|video|toggle|cta|audio|code|fullwidth_image))\b([^\]]*)\]"
            # contenu jusqu'à la balise de fin, sans avaler le module suivant si elle manque
            r"(?:((?:(?!\[et_pb_).)*?)\[/\1\])?", contenu, re.S)
        for m in modules:
            nom, attrs, interieur = m.group(1), dict(re.findall(r'(\w+)="([^"]*)"', m.group(2))), m.group(3) or ""
            a = lambda cle: unescape(attrs.get(cle, ""))
            if nom in ("et_pb_text", "et_pb_code"):
                self.contenu_html(interieur)
            elif nom == "et_pb_toggle":
                self.titre(a("title"), 3)
                self.contenu_html(interieur)
            elif nom == "et_pb_cta":
                self.titre(a("title"), 3)
                self.contenu_html(interieur)
                self.bouton(a("button_text"), a("button_url"))
            elif nom == "et_pb_button":
                self.bouton(a("button_text"), a("button_url"))
            elif nom == "et_pb_blurb":
                self.blurb(a("title"), a("url") or a("link_option_url"), a("image"), interieur)
            elif nom in ("et_pb_image", "et_pb_fullwidth_image"):
                f = self.conv.fichier(a("url") or a("link_option_url"))
                if f:
                    self.fiche(a("title") or a("alt"), f, a("src"))
                else:
                    self.image(a("src"), a("alt"))
            elif nom == "et_pb_video":
                y = YOUTUBE.search(a("src"))
                if y:
                    self.video(y.group(1))
                elif self.conv.fichier(a("src")):
                    self.fiche(os.path.basename(a("src")).rsplit(".", 1)[0].replace("-", " "), self.conv.fichier(a("src")))
            elif nom == "et_pb_audio":
                if self.conv.fichier(a("audio")):
                    self.fiche(a("title") or os.path.basename(a("audio")), self.conv.fichier(a("audio")))

    def finir(self):
        """Une vidéo suivie d'une courte ligne de texte : cette ligne est sa légende."""
        blocs = []
        for b in self.blocs:
            prec = blocs[-1] if blocs else None
            if (b["t"] == "texte" and prec and prec["t"] == "video" and not prec.get("legende")
                    and "<a " not in b["html"] and len(texte_seul(b["html"])) < 120):
                prec["legende"] = texte_seul(b["html"])
                continue
            blocs.append(b)
        return blocs

    def bouton(self, texte, url):
        f = self.conv.fichier(url)
        if f:
            self.fiche(texte, f)
        elif texte and self.conv.lien(url):
            self.blocs.append({"t": "lien", "texte": texte, "href": self.conv.lien(url)})

    def blurb(self, titre, url, image, interieur):
        fichiers = []
        if self.conv.fichier(url):
            fichiers.append((titre, self.conv.fichier(url)))
        for h, lib in re.findall(r'<a [^>]*href="([^"]+)"[^>]*>(.*?)</a>', interieur, re.S):
            f = self.conv.fichier(h)
            if f and f not in [x[1] for x in fichiers]:
                # Plusieurs liens dans un même bloc (PDF + PowerPoint…) : on précise le libellé.
                lib = texte_seul(lib)
                fichiers.append((f"{titre} ({lib})" if titre and lib and slug(lib) != slug(titre) else titre or lib, f))
        if fichiers:
            for t, f in fichiers:
                self.fiche(t, f, image)
            return
        # Bloc sans fichier : on garde son titre, son image et son texte.
        lien = self.conv.lien(url)
        html = ""
        if titre:
            html += f'<h4>{f"<a href={json.dumps(lien)}>" if lien else ""}{titre}{"</a>" if lien else ""}</h4>'
        if image:
            html += f'<img src="{image}" alt="">'
        self.texte(html + interieur)


def main():
    posts = json.load(open(os.path.join(SAUVEGARDE, "analyse", "posts.json")))
    # Les pages « La lettre A–Z » du dictionnaire sont des « project » Divi, pas des pages.
    pages_wp = {p["post_name"]: p for p in posts
                if p["post_type"] in ("page", "project") and p["post_status"] == "publish"}
    dates = {}
    for p in posts:
        if p["post_type"] == "attachment":
            c = chemin_upload(p["guid"] or "")
            if c:
                dates[c] = p["post_date"][:10]
    conv = Convertisseur()

    ressources, themes, pages = [], [], {}
    for tid, tnom, liste in THEMES:
        sous = []
        for slug_page, nom, court, *parent in liste:
            wp = pages_wp[slug_page]
            page = Page(conv, slug_page, [nom, nom.split(":")[-1], wp["post_title"]], ressources, dates)
            page.lire(wp["post_content"])
            for section, titre, fichier in AJOUTS.get(slug_page, []):
                if section != page.section:
                    page.titre(section, 2)
                page.fiche(titre, unicodedata.normalize("NFC", fichier))
            pages[slug_page] = page.finir()
            for r in ressources[len(ressources) - len(page.vus):]:
                r["theme"] = tid
            sous.append({"id": slug_page, "titre": nom, "fichier": fichier_page(tid, court),
                         **({"parent": parent[0]} if parent else {})})
        themes.append({"id": tid, "titre": tnom, "pages": sous})

    os.makedirs(os.path.join(SITE, "data"), exist_ok=True)
    with open(os.path.join(SITE, "data", "ressources.json"), "w", encoding="utf-8") as out:
        json.dump({"themes": themes, "pages": pages, "ressources": ressources}, out, ensure_ascii=False, indent=1)
    print(len(ressources), "ressources")
    for t in themes:
        n = sum(1 for r in ressources if r["theme"] == t["id"])
        print(f"  {t['titre']}: {n}")


if __name__ == "__main__":
    main()
