"""Transforme le HTML chargé de WordPress/Divi en HTML simple et propre.

On garde les titres, paragraphes, listes, gras/italique, liens et images.
Tout le reste (styles, classes, <span>, <div>…) est retiré, le texte est conservé.
Les liens vers des fichiers deviennent « fichier:2016/09/x.pdf » : le JavaScript du site
les remplace par l'adresse du stockage Azure.
"""
import re
from html import escape, unescape
from html.parser import HTMLParser

GARDES = {"p", "br", "strong", "b", "em", "i", "u", "ul", "ol", "li", "a", "h1", "h2", "h3", "h4", "h5", "img",
          "blockquote"}
BLOCS = {"p", "ul", "ol", "li", "h1", "h2", "h3", "h4", "h5", "blockquote", "div", "table", "tr"}
IGNORES = {"script", "style", "iframe", "noscript"}


def autop(html):
    """Comme WordPress : les doubles retours à la ligne deviennent des paragraphes."""
    if not re.search(r"\n\s*\n", html):
        return html
    morceaux = re.split(r"\n\s*\n", html)
    return "".join(m if re.match(r"\s*<(p|ul|ol|h\d|blockquote|div|table)", m) else f"<p>{m}</p>" for m in morceaux)


class _Nettoyeur(HTMLParser):
    def __init__(self, convertir_lien, convertir_image):
        super().__init__(convert_charrefs=True)
        self.sortie = []
        self.pile = []          # balises ouvertes que l'on a gardées
        self.ignore = 0
        self.convertir_lien = convertir_lien
        self.convertir_image = convertir_image

    def handle_starttag(self, tag, attrs):
        if tag in IGNORES:
            self.ignore += 1
            return
        if self.ignore:
            return
        attrs = dict(attrs)
        if tag == "b":
            tag = "strong"
        if tag == "i":
            tag = "em"
        if tag == "h1":
            tag = "h2"
        if tag == "h5":
            tag = "h4"
        if tag == "br":
            self.sortie.append("<br>")
            return
        if tag == "img":
            src = self.convertir_image(attrs.get("src", ""))
            if src:
                self.sortie.append(f'<img src="{escape(src)}" alt="{escape(attrs.get("alt") or "")}" loading="lazy">')
            return
        if tag not in GARDES:
            if tag in BLOCS:
                self.sortie.append("\n")
            return
        if tag == "a":
            href = self.convertir_lien(attrs.get("href", ""))
            if not href:
                self.pile.append(None)
                return
            externe = href.startswith("http") or href.startswith("fichier:")
            cible = ' target="_blank" rel="noopener"' if externe else ""
            self.sortie.append(f'<a href="{escape(href)}"{cible}>')
            self.pile.append("a")
            return
        if tag in BLOCS:
            self.sortie.append("\n")
        self.sortie.append(f"<{tag}>")
        self.pile.append(tag)

    def handle_endtag(self, tag):
        if tag in IGNORES:
            self.ignore = max(0, self.ignore - 1)
            return
        if self.ignore:
            return
        tag = {"b": "strong", "i": "em", "h1": "h2", "h5": "h4"}.get(tag, tag)
        if tag not in GARDES or tag in ("br", "img"):
            if tag in BLOCS:
                self.sortie.append("\n")
            return
        # referme jusqu'à la balise correspondante (HTML de WordPress parfois mal imbriqué)
        if tag in self.pile or (tag == "a" and None in self.pile):
            while self.pile:
                t = self.pile.pop()
                if t:
                    self.sortie.append(f"</{t}>" + ("\n" if t in BLOCS else ""))
                if t == tag or (tag == "a" and t is None):
                    break

    def handle_data(self, data):
        if not self.ignore:
            # les retours à la ligne ne servent qu'à séparer les blocs (voir nettoyer_html)
            self.sortie.append(escape(re.sub(r"\s+", " ", data), quote=False))

    def resultat(self):
        while self.pile:
            t = self.pile.pop()
            if t:
                self.sortie.append(f"</{t}>")
        return "".join(self.sortie)


def nettoyer_html(html, convertir_lien=lambda h: h, convertir_image=lambda s: None):
    p = _Nettoyeur(convertir_lien, convertir_image)
    p.feed(autop(html))
    p.close()
    out = p.resultat()
    out = out.replace("\xa0", " ")
    # balises vides, espaces en trop
    for _ in range(3):
        out = re.sub(r"<(p|strong|em|u|li|h2|h3|h4|a[^>]*)>\s*(<br>\s*)*</\w+>", "", out)
    out = re.sub(r"(<br>\s*){2,}", "<br>", out)
    out = re.sub(r"<p>\s*<br>", "<p>", out)
    out = re.sub(r"<br>\s*</p>", "</p>", out)
    out = re.sub(r"[ \t]+", " ", out)
    out = re.sub(r"\s*\n\s*", "\n", out).strip()
    # du texte « nu » entre deux blocs devient un paragraphe
    lignes = []
    for ligne in out.split("\n"):
        ligne = ligne.strip()
        if not ligne:
            continue
        if not re.match(r"</?(p|ul|ol|li|h\d|blockquote)\b", ligne):
            ligne = f"<p>{ligne}</p>"
        lignes.append(ligne)
    return "\n".join(lignes)


def texte_seul(html):
    return " ".join(unescape(re.sub(r"<[^>]+>", " ", html)).split())
