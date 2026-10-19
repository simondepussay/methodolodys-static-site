"""Crée les pages HTML du site (hors accueil) avec le même en-tête et pied de page.

- Une page par thème (francais.html…) : une coquille, le contenu vient de data/ressources.json (js/theme.js).
- Les pages de texte (vous-etes.html, a-propos.html, mentions-legales.html) sont écrites en entier
  à partir des textes de l'ancien site. Ensuite, on peut les modifier directement à la main :
  relancer ce script les écraserait (utiliser --textes pour le faire exprès).
"""
import json
import os
import sys
from html import escape

from extraire import PAGES_TEXTE, SAUVEGARDE, SITE, THEMES, Convertisseur, Page, fichier_page

# Adresse du site une fois en ligne (sert au plan du site pour Google)
ADRESSE_SITE = "https://methodolodys.ch"
# Pendant les essais sur l'adresse provisoire d'Azure, on demande à Google de ne pas indexer le site
# (sinon il verrait deux sites identiques). Passer à True le jour où methodolodys.ch pointe ici.
INDEXATION = False


def entete(titre, description, actif=""):
    menu = [("index.html", "Accueil"), ("index.html#ressources", "Ressources"), ("vous-etes.html", "Vous êtes"),
            ("a-propos.html", "À propos"), ("#contact", "Contact")]
    liens = "\n".join(
        f'      <a href="{h}"{" aria-current=\"page\"" if h == actif else ""}>{t}</a>' for h, t in menu)
    return f"""<!doctype html>
<html lang="fr">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{escape(titre)} | Methodolodys</title>
  <meta name="description" content="{escape(description)}">
  <link rel="icon" href="images/accueil/logo.webp">
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Lexend:wght@400;500;600&display=swap" rel="stylesheet">
  <link rel="stylesheet" href="css/style.css">
</head>
<body>

<header class="entete">
  <div class="conteneur">
    <a class="logo" href="index.html">
      <img src="images/accueil/logo.webp" alt="" width="48" height="52">
      Methodolodys
    </a>
    <button class="bouton-menu" aria-expanded="false" aria-controls="menu">Menu</button>
    <nav class="menu" id="menu" aria-label="Menu principal">
{liens}
    </nav>
  </div>
</header>
"""


PIED = """
<footer class="pied" id="contact">
  <div class="conteneur">
    <div>
      <h2>Contact</h2>
      <p><a href="mailto:martine.jimenez@bluewin.ch">martine.jimenez@bluewin.ch</a></p>
      <p>Je réponds à vos mails dans les 48 heures. Si vous n'avez pas reçu de réponse, n'hésitez pas à renvoyer un message.</p>
    </div>
    <div>
      <h2>Le site</h2>
      <p><a href="a-propos.html">À propos</a></p>
      <p><a href="mentions-legales.html">Mentions légales</a></p>
    </div>
    <div>
      <h2>Droits d'auteur</h2>
      <p>Tout est libre de téléchargement. Merci de maintenir le principe de gratuité et de signaler l'auteur en cas de diffusion.</p>
    </div>
    <p class="bas">© Martine Jiménez — Methodolodys</p>
  </div>
</footer>
"""


def page_theme(tid, titre_theme, page=None, parent=None):
    """Page d'entrée d'un thème, ou page d'une de ses parties (page = (id, titre))."""
    titre = page[1] if page else titre_theme
    fil = ['<a href="index.html">Accueil</a>']
    if page:
        fil.append(f'<a href="{tid}.html">{escape(titre_theme)}</a>')
        if parent:
            fil.append(f'<a href="{parent[0]}">{escape(parent[1])}</a>')
    fil.append(escape(titre))
    image = "" if page else f'\n    <img src="images/themes/{tid}.webp" alt="" width="260" height="195">'
    data_page = f' data-page="{page[0]}"' if page else ""
    return entete(titre, f"{titre} : fiches gratuites à télécharger pour accompagner les enfants dys.") + f"""
<main class="conteneur" data-theme="{tid}"{data_page}>
  <p class="fil">{" › ".join(fil)}</p>

  <div class="tete-theme{'' if image else ' sans-image'}">
    <div>
      <h1>{escape(titre)}</h1>
      <p class="nombre" id="nombre"></p>
      <div class="recherche" role="search">
        <label for="champ-recherche" class="titre-recherche">Chercher dans « {escape(titre_theme)} »</label>
        <div class="champ">
          <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" aria-hidden="true"><circle cx="11" cy="11" r="7"/><path d="m20 20-4-4"/></svg>
          <input id="champ-recherche" type="search" placeholder="Tapez un mot…" autocomplete="off">
        </div>
        <p class="compte" id="compte" aria-live="polite"></p>
      </div>
      <ul class="resultats" id="resultats"></ul>
    </div>{image}
  </div>

  <div id="pages"></div>
</main>
{PIED}
<script src="js/commun.js"></script>
<script src="js/theme.js"></script>
</body>
</html>
"""


def blocs_en_html(blocs, ressources):
    """Rendu statique des blocs (pages de texte)."""
    html = []
    for b in blocs:
        if b["t"] == "titre":
            h = min(b["niveau"] + 1, 4)
            html.append(f"<h{h}>{escape(b['texte'])}</h{h}>")
        elif b["t"] == "texte":
            html.append(b["html"])
        elif b["t"] == "image":
            html.append(f'<img src="{b["src"]}" alt="{escape(b["alt"])}" loading="lazy">')
        elif b["t"] == "video":
            titre = escape(b.get("legende") or b.get("titre") or "Vidéo")
            html.append(f'<div class="video"><iframe src="https://www.youtube-nocookie.com/embed/{b["youtube"]}" '
                        f'title="{titre}" loading="lazy" referrerpolicy="strict-origin-when-cross-origin" '
                        f'allow="encrypted-media; picture-in-picture" allowfullscreen></iframe></div>')
            if b.get("legende"):
                html.append(f"<p>{escape(b['legende'])}</p>")
        elif b["t"] == "lien":
            html.append(f'<p><a class="bouton secondaire" href="{escape(b["href"])}">{escape(b["texte"])}</a></p>')
        elif b["t"] == "fiches":
            items = "".join(
                f'<li><a href="fichier:{escape(ressources[i]["fichier"])}" target="_blank" rel="noopener">'
                f'{escape(ressources[i]["titre"])}</a> <span class="etiquette {ressources[i]["type"]}">'
                f'{ressources[i]["type"]}</span></li>' for i in b["ids"])
            html.append(f"<ul>{items}</ul>")
    return "\n".join(html)


def page_texte(nom_fichier, titre, description, sections, conv, pages_wp):
    """sections : [(ancre, titre de section, [anciennes pages WordPress])]"""
    ressources = []
    corps = []
    for ancre, titre_section, slugs in sections:
        contenu = []
        for s in slugs:
            wp = pages_wp[s]
            page = Page(conv, s, [titre_section, wp["post_title"]], ressources, {})
            page.lire(wp["post_content"])
            contenu.append(blocs_en_html(page.finir(), ressources))
        h2 = f"<h2>{escape(titre_section)}</h2>\n" if len(sections) > 1 else ""
        corps.append(f'<section id="{ancre}">\n{h2}' + "\n".join(contenu) + "\n</section>")
    sommaire = ""
    if len(sections) > 1:
        sommaire = '<ul class="sommaire-texte">' + "".join(
            f'<li><a href="#{a}">{escape(t)}</a></li>' for a, t, _ in sections) + "</ul>"
    html = entete(titre, description, nom_fichier) + f"""
<main class="conteneur">
  <p class="fil"><a href="index.html">Accueil</a> › {escape(titre)}</p>
  <div class="article">
    <h1>{escape(titre)}</h1>
    {sommaire}
{chr(10).join(corps)}
  </div>
</main>
{PIED}
<script src="js/commun.js"></script>
</body>
</html>
"""
    with open(os.path.join(SITE, nom_fichier), "w", encoding="utf-8") as f:
        f.write(html)
    print("écrit", nom_fichier)


def page_404():
    """Page « introuvable ». Elle sert aussi de relais pour les anciens liens directs vers des fichiers
    (…/wp-content/uploads/2016/09/x.pdf) : le JavaScript renvoie vers le même fichier sur Azure."""
    html = entete("Page introuvable", "Cette page n'existe pas ou plus.")
    # Affichée à n'importe quelle adresse : <base> pour que les liens relatifs partent de la racine du site
    html = html.replace('<meta charset="utf-8">', '<meta charset="utf-8">\n  <base href="/">\n  <meta name="robots" content="noindex">', 1)
    return html + f"""
<main class="conteneur introuvable">
  <img src="images/themes/tutoriels.webp" alt="" width="220" height="257">
  <div>
    <h1>Oups, cette page n'existe pas</h1>
    <p>Le site de Methodolodys a été refait : la page que vous cherchez a peut-être changé d'adresse.</p>
    <p>Essayez la recherche, ou repartez de l'accueil.</p>
    <div class="recherche" role="search">
      <label for="champ-recherche" class="visuellement-cache">Rechercher une fiche</label>
      <div class="champ">
        <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" aria-hidden="true"><circle cx="11" cy="11" r="7"/><path d="m20 20-4-4"/></svg>
        <input id="champ-recherche" type="search" placeholder="Chercher une fiche…" autocomplete="off">
      </div>
      <p class="compte" id="compte" aria-live="polite"></p>
    </div>
    <ul class="resultats" id="resultats"></ul>
    <p><a class="bouton" href="index.html">Retour à l'accueil</a> <a class="bouton secondaire" href="index.html#ressources">Tous les outils</a></p>
  </div>
</main>
{PIED}
<script src="js/commun.js"></script>
<script>
  // Ancien lien direct vers un fichier WordPress : on renvoie vers le même fichier sur Azure.
  (function () {{
    var debut = location.pathname.indexOf("/wp-content/uploads/");
    if (debut < 0 || typeof FICHIERS === "undefined") return;
    var chemin = decodeURIComponent(location.pathname.slice(debut + "/wp-content/uploads/".length)).normalize("NFC");
    location.replace(FICHIERS + chemin.split("/").map(encodeURIComponent).join("/"));
  }})();
</script>
<script>
  brancherRecherche(document.getElementById("champ-recherche"), document.getElementById("resultats"), document.getElementById("compte"));
</script>
</body>
</html>
"""


def anciennes_adresses():
    """Ancienne adresse WordPress (« /sciences-histoire-geographie/histoire/ ») -> nouvelle page."""
    nouvelles = {s: fichier_page(t, court) for t, _, liste in THEMES for s, _, court, *_ in liste}
    nouvelles.update(PAGES_TEXTE)
    nouvelles.update({"sciences-histoire-geographie": "sciences.html", "dictionnaire-visuo-sementique-2": "dictionnaire.html"})
    posts = json.load(open(os.path.join(SAUVEGARDE, "analyse", "posts.json")))
    publies = {p["ID"]: p for p in posts if p["post_status"] == "publish" and p["post_type"] in ("page", "project")}
    adresses = {}
    for p in publies.values():
        if p["post_name"] not in nouvelles:
            continue
        chemin, parent = [p["post_name"]], publies.get(p["post_parent"])
        while parent:
            chemin.insert(0, parent["post_name"])
            parent = publies.get(parent["post_parent"])
        prefixe = "/project/" if p["post_type"] == "project" else "/"
        adresses[prefixe + "/".join(chemin)] = "/" + nouvelles[p["post_name"]]
    return adresses


def fichiers_deploiement():
    """Fichiers pour la mise en ligne sur Azure Static Web Apps."""
    with open(os.path.join(SITE, "404.html"), "w", encoding="utf-8") as f:
        f.write(page_404())

    routes = []
    for ancienne, nouvelle in sorted(anciennes_adresses().items()):
        # Azure traite « /x » et « /x/ » comme la même adresse : une seule règle suffit
        routes.append({"route": ancienne, "redirect": nouvelle, "statusCode": 301})
    config = {
        "routes": routes + [
            {"route": "/images/*", "headers": {"cache-control": "public, max-age=2592000"}},
            # Données, scripts et styles changent à chaque mise à jour : le navigateur revérifie à chaque visite
            {"route": "/data/*", "headers": {"cache-control": "no-cache"}},
            {"route": "/js/*", "headers": {"cache-control": "no-cache"}},
            {"route": "/css/*", "headers": {"cache-control": "no-cache"}},
        ],
        "responseOverrides": {"404": {"rewrite": "/404.html", "statusCode": 404}},
        "mimeTypes": {".json": "application/json", ".webp": "image/webp"},
    }
    # YouTube refuse de lire une vidéo intégrée s'il ne sait pas sur quel site elle est (erreur 153) :
    # Azure envoie « same-origin » par défaut, on envoie donc au moins l'adresse du site.
    config["globalHeaders"] = {"Referrer-Policy": "strict-origin-when-cross-origin"}
    if not INDEXATION:
        config["globalHeaders"]["X-Robots-Tag"] = "noindex, nofollow"
    with open(os.path.join(SITE, "staticwebapp.config.json"), "w", encoding="utf-8") as f:
        json.dump(config, f, ensure_ascii=False, indent=2)

    pages = sorted(f for f in os.listdir(SITE) if f.endswith(".html") and f != "404.html")
    with open(os.path.join(SITE, "sitemap.xml"), "w", encoding="utf-8") as f:
        f.write('<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n')
        for page in pages:
            adresse = ADRESSE_SITE + "/" + ("" if page == "index.html" else page)
            f.write(f"  <url><loc>{escape(adresse)}</loc></url>\n")
        f.write("</urlset>\n")
    with open(os.path.join(SITE, "robots.txt"), "w", encoding="utf-8") as f:
        f.write(f"User-agent: *\nAllow: /\n\nSitemap: {ADRESSE_SITE}/sitemap.xml\n")
    print(f"écrit 404.html, staticwebapp.config.json ({len(routes)} redirections), sitemap.xml ({len(pages)} pages), robots.txt")


def main():
    n = 0
    for tid, titre, liste in THEMES:
        with open(os.path.join(SITE, f"{tid}.html"), "w", encoding="utf-8") as f:
            f.write(page_theme(tid, titre))
        infos = {s: (fichier_page(tid, court), nom) for s, nom, court, *_ in liste}
        for s, nom, court, *parent in liste:
            if not court:
                continue  # affichée sur la page du thème
            # Le dictionnaire (page du thème) n'a pas besoin d'apparaître deux fois dans le fil d'Ariane
            par = infos[parent[0]] if parent and infos[parent[0]][0] != f"{tid}.html" else None
            with open(os.path.join(SITE, fichier_page(tid, court)), "w", encoding="utf-8") as f:
                f.write(page_theme(tid, titre, (s, nom), par))
            n += 1
    print(f"écrit {len(THEMES)} pages de thème et {n} pages de parties")
    fichiers_deploiement()

    if "--textes" not in sys.argv and os.path.exists(os.path.join(SITE, "a-propos.html")):
        print("Pages de texte déjà présentes : non écrasées (ajouter --textes pour les recréer).")
        return

    posts = json.load(open(os.path.join(SAUVEGARDE, "analyse", "posts.json")))
    pages_wp = {p["post_name"]: p for p in posts if p["post_type"] == "page" and p["post_status"] == "publish"}
    conv = Convertisseur()
    page_texte("vous-etes.html", "Vous êtes…", "Conseils de Martine Jiménez selon votre situation.", [
        ("enseignants", "Enseignant·e", ["instituteurs-professeurs"]),
        ("parents", "Parent d'enfant dys", ["parents-denfants-dys"]),
        ("autodidacte", "Autodidacte dys", ["autodidacte-dys"]),
        ("orthophoniste", "Orthophoniste", ["othophoniste"]),
    ], conv, pages_wp)
    page_texte("a-propos.html", "À propos", "Qui est Martine Jiménez, ses collaborations et ses invités.", [
        ("introduction", "Introduction", ["introduction"]),
        ("invites", "Mes invités", ["mes-invites", "marlyse-narbel"]),
        ("formation", "Cours, formation continue", ["cours-formation-continue"]),
        ("collaborations", "Outils en collaboration", ["mes-collaborateurs"]),
        ("liens", "Autres sites à consulter", ["pour-en-savoir-plus"]),
        ("medias", "Médias", ["medias"]),
    ], conv, pages_wp)
    page_texte("mentions-legales.html", "Mentions légales", "Mentions légales du site Methodolodys.", [
        ("mentions", "Mentions légales", ["mentions-legales"]),
    ], conv, pages_wp)


if __name__ == "__main__":
    main()
