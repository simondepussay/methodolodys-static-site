// Pages des thèmes, construites à partir de data/ressources.json.
// <main data-theme="francais">                       -> page d'entrée du thème (francais.html)
// <main data-theme="francais" data-page="conjugaison"> -> page d'une partie (francais-conjugaison.html)

const main = document.querySelector("main[data-theme]");
const themeId = main.dataset.theme;
const pageId = main.dataset.page;

/** Remplace les liens « fichier:… » des textes par l'adresse de téléchargement. */
function liensFichiers(html) {
  return html.replace(/href="fichier:([^"]+)"/g, (_, f) => `href="${lienFichier({ fichier: f.replace(/&amp;/g, "&") })}"`);
}

/** Carte d'une fiche à télécharger. Vidéos et sons se lisent directement dans la page. */
function carteFiche(r) {
  const url = lienFichier(r);
  if (["m4v", "mp4"].includes(r.type)) {
    return `<figure class="media"><video controls preload="none" src="${url}"${r.image ? ` poster="${r.image}"` : ""}></video>
      <figcaption>${echapper(r.titre)}</figcaption></figure>`;
  }
  if (r.type === "mp3") {
    return `<figure class="media son"><figcaption>${echapper(r.titre)}</figcaption>
      <audio controls preload="none" src="${url}"></audio></figure>`;
  }
  const image = r.image
    ? `<img src="${r.image}" alt="" loading="lazy">`
    : `<span class="sans-image" aria-hidden="true">${r.type.toUpperCase().slice(0, 4)}</span>`;
  return `<a class="fiche" href="${url}" target="_blank" rel="noopener">
    <span class="apercu">${image}</span>
    <span class="nom">${echapper(r.titre)}</span>
    <span class="details"><span class="etiquette ${r.type}">${r.type}</span> ${poids(r.taille)}</span>
  </a>`;
}

/** Dictionnaire : « bain » et « bain explication » deviennent un seul mot avec deux liens. */
function listeMots(fiches) {
  const mots = new Map();
  for (const r of fiches) {
    const expl = /\s+explication\s*$/i.test(r.titre);
    const mot = r.titre.replace(/\s+explication\s*$/i, "").trim();
    if (!mots.has(mot)) mots.set(mot, {});
    mots.get(mot)[expl ? "explication" : "carte"] = r;
  }
  return `<ul class="mots">${[...mots].map(([mot, { carte, explication }]) => `<li>
    ${carte ? `<a href="${lienFichier(carte)}" target="_blank" rel="noopener">${echapper(mot)}</a>` : echapper(mot)}
    ${explication ? `<a class="explication" href="${lienFichier(explication)}" target="_blank" rel="noopener">explication</a>` : ""}
  </li>`).join("")}</ul>`;
}

function video(b) {
  // L'image d'aperçu est affichée d'abord ; le lecteur YouTube ne se charge qu'au clic.
  const titre = b.legende || b.titre || "Vidéo";
  return `<figure class="youtube">
    <button type="button" data-youtube="${b.youtube}" aria-label="Lire la vidéo : ${echapper(titre)}">
      <img src="https://i.ytimg.com/vi/${b.youtube}/hqdefault.jpg" alt="" loading="lazy">
      <span class="lecture" aria-hidden="true"></span>
    </button>
    ${b.legende ? `<figcaption>${echapper(b.legende)}</figcaption>` : ""}
  </figure>`;
}

/** Le contenu d'une page (titres, textes, images, vidéos, fiches), avec son sommaire. */
function contenuPage(blocs, ressources, estMot) {
  const html = [];
  let videos = [];
  const viderVideos = () => {
    if (videos.length) html.push(`<div class="videos">${videos.join("")}</div>`);
    videos = [];
  };
  for (const b of blocs) {
    if (b.t !== "video") viderVideos();
    if (b.t === "titre") {
      const h = Math.min(b.niveau, 4);
      html.push(`<h${h} id="${b.ancre}">${echapper(b.texte)}</h${h}>`);
    } else if (b.t === "texte") {
      html.push(`<div class="texte">${liensFichiers(b.html)}</div>`);
    } else if (b.t === "image") {
      html.push(`<img class="illustration" src="${b.src}" alt="${echapper(b.alt)}" loading="lazy">`);
    } else if (b.t === "video") {
      videos.push(video(b));
    } else if (b.t === "lien") {
      const externe = /^https?:/.test(b.href);
      html.push(`<p><a class="bouton secondaire" href="${echapper(b.href)}"${externe ? ' target="_blank" rel="noopener"' : ""}>${echapper(b.texte)}</a></p>`);
    } else if (b.t === "fiches") {
      const fiches = b.ids.map((i) => ressources[i]);
      html.push(estMot ? listeMots(fiches) : `<div class="fiches">${fiches.map(carteFiche).join("")}</div>`);
    }
  }
  viderVideos();

  const titres = blocs.filter((b) => b.t === "titre" && b.niveau <= 3);
  const sommaire = titres.length >= 4 && !estMot
    ? `<nav class="sommaire-page" aria-label="Dans cette page"><p>Dans cette page :</p><ul>${titres
      .map((t) => `<li><a href="#${t.ancre}">${echapper(t.texte)}</a></li>`).join("")}</ul></nav>`
    : "";
  return sommaire + html.join("\n");
}

/** Cartes menant aux pages d'une partie (image, titre, nombre de fiches, sous-pages). */
function cartesPages(liste, theme, ressources) {
  const enfants = (id) => theme.pages.filter((p) => p.parent === id);
  return `<div class="parties">${liste.map((p) => {
    const ids = new Set([p.id, ...enfants(p.id).map((e) => e.id)]);
    const fiches = ressources.filter((r) => ids.has(r.page));
    const image = fiches.find((r) => r.image)?.image || `images/themes/${theme.id}.webp`;
    const n = fiches.length;
    const sous = enfants(p.id);
    return `<article class="partie">
      <a href="${p.fichier}">
        <span class="image"><img src="${image}" alt="" loading="lazy"></span>
        <span class="corps"><span class="titre">${echapper(p.titre)}</span>
        <span class="nombre">${n ? `${n} ${themeId === "tutoriels" ? "vidéo" : "fiche"}${n > 1 ? "s" : ""}` : "Vidéos"}</span></span>
      </a>
      ${sous.length ? `<ul>${sous.map((e) => `<li><a href="${e.fichier}">${echapper(e.titre)}</a></li>`).join("")}</ul>` : ""}
    </article>`;
  }).join("")}</div>`;
}

function barreLettres(lettres, active) {
  return `<p class="lettres">${lettres.map((p) => {
    const l = p.titre.slice(-1);
    return p.id === active
      ? `<span aria-current="page">${l}</span>`
      : `<a href="${p.fichier}" aria-label="La lettre ${l}">${l}</a>`;
  }).join("")}</p>`;
}

chargerDonnees().then(({ themes, pages, ressources }) => {
  const theme = themes.find((t) => t.id === themeId);
  const propre = theme.pages.find((p) => p.fichier === `${themeId}.html`); // contenu affiché sur la page du thème
  const enfants = (id) => theme.pages.filter((p) => p.parent === id);
  const zone = document.getElementById("pages");
  const nombre = document.getElementById("nombre");
  const unite = themeId === "tutoriels" ? "vidéos et films" : "fiches";

  if (!pageId) {
    // ---- Page d'entrée du thème ----
    const n = ressources.filter((r) => r.theme === themeId).length;
    nombre.textContent = `${n.toLocaleString("fr-CH")} ${unite} à télécharger gratuitement`;
    const html = [];
    if (propre) {
      const lettres = themeId === "dictionnaire" ? enfants(propre.id) : [];
      if (lettres.length) html.push(`<nav class="sommaire" aria-label="Lettres">${barreLettres(lettres)}</nav>`);
      html.push(contenuPage(pages[propre.id] || [], ressources, false));
    }
    const parties = theme.pages.filter((p) => !p.parent && p !== propre);
    if (parties.length) html.unshift(cartesPages(parties, theme, ressources));
    zone.innerHTML = html.join("\n");
  } else {
    // ---- Page d'une partie ----
    const page = theme.pages.find((p) => p.id === pageId);
    const estMot = themeId === "dictionnaire";
    const ids = new Set([page.id, ...enfants(page.id).map((e) => e.id)]);
    const n = ressources.filter((r) => ids.has(r.page)).length;
    nombre.textContent = n ? `${n.toLocaleString("fr-CH")} ${estMot ? "fiches (mots et explications)" : unite}` : "";

    const html = [];
    if (estMot) html.push(`<nav class="sommaire" aria-label="Lettres">${barreLettres(enfants(page.parent), page.id)}</nav>`);
    html.push(contenuPage(pages[page.id] || [], ressources, estMot));
    // Pages rattachées à celle-ci (les histoires sous « Lecture compréhension »…), en fin de page
    if (enfants(page.id).length) {
      html.push(`<section class="a-voir"><h2>À découvrir aussi</h2>
        <p>D'autres pages liées à « ${echapper(page.titre)} » :</p>
        ${cartesPages(enfants(page.id), theme, ressources)}</section>`);
    }

    // Précédent / suivant, dans l'ordre du thème
    const suite = theme.pages.filter((p) => p !== propre && (estMot ? p.parent === page.parent : true));
    const i = suite.indexOf(page);
    const prec = suite[i - 1];
    const suiv = suite[i + 1];
    html.push(`<nav class="suite" aria-label="Pages voisines">
      ${prec ? `<a href="${prec.fichier}"><span>← Précédent</span>${echapper(prec.titre)}</a>` : "<span></span>"}
      ${suiv ? `<a class="suivant" href="${suiv.fichier}"><span>Suivant →</span>${echapper(suiv.titre)}</a>` : ""}
    </nav>`);
    zone.innerHTML = html.join("\n");
  }

  // Le contenu est construit après le chargement : on va à l'ancre demandée dans l'adresse
  // (deux fois : les images au-dessus peuvent encore changer la hauteur de la page)
  const cible = location.hash && document.getElementById(decodeURIComponent(location.hash.slice(1)));
  if (cible) {
    cible.scrollIntoView({ behavior: "instant" });
    setTimeout(() => cible.scrollIntoView({ behavior: "instant" }), 400);
  }
});

// Vidéos YouTube : on remplace l'aperçu par le lecteur au clic
document.addEventListener("click", (e) => {
  const bouton = e.target.closest("button[data-youtube]");
  if (!bouton) return;
  const iframe = document.createElement("iframe");
  iframe.src = `https://www.youtube-nocookie.com/embed/${bouton.dataset.youtube}?autoplay=1`;
  iframe.title = bouton.getAttribute("aria-label");
  iframe.allow = "autoplay; encrypted-media; picture-in-picture";
  iframe.allowFullscreen = true;
  iframe.referrerPolicy = "strict-origin-when-cross-origin"; // sans ça, YouTube affiche « Erreur 153 »
  bouton.replaceWith(iframe);
});

brancherRecherche(
  document.getElementById("champ-recherche"),
  document.getElementById("resultats"),
  document.getElementById("compte"),
  (r) => r.theme === themeId,
);
