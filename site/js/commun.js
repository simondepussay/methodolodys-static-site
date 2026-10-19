// Methodolodys — code commun à toutes les pages.

// Adresse où sont stockés les fichiers à télécharger.
// En local : le dossier « azure » à côté du site. En ligne : l'adresse du Blob Storage Azure,
// (compte de stockage methodolodysfichiers, groupe rg-methodolodys, abonnement Azure for Students).
const FICHIERS = location.protocol === "file:" || location.hostname === "localhost" || location.hostname === "127.0.0.1"
  ? "../azure/"
  : "https://methodolodysfichiers.blob.core.windows.net/fichiers/";

// Adresse de l'ancien site WordPress, proposée dans une bande en haut de chaque page
// pendant la période de test. Mettre "" pour retirer la bande.
const ANCIEN_SITE = "https://methodolodys.ch/";

let donneesPromesse = null;

/** Charge data/ressources.json une seule fois. */
function chargerDonnees() {
  if (!donneesPromesse) {
    donneesPromesse = fetch("data/ressources.json", { cache: "no-cache" }).then((r) => r.json()); // toujours la dernière version
  }
  return donneesPromesse;
}

/** Lien de téléchargement d'une ressource. */
function lienFichier(ressource) {
  return FICHIERS + ressource.fichier.split("/").map(encodeURIComponent).join("/");
}

/** Lien vers la page d'une partie (objet page de ressources.json). */
function lienPage(page) {
  return page.fichier;
}

/** « 2,4 Mo » */
function poids(octets) {
  if (octets < 1e6) return Math.max(1, Math.round(octets / 1e3)) + " ko";
  return (octets / 1e6).toLocaleString("fr-CH", { maximumFractionDigits: 1 }) + " Mo";
}

/** Texte sans accents ni majuscules, pour comparer. */
function normaliser(texte) {
  return (texte || "").normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase();
}

function echapper(texte) {
  return String(texte ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]);
}

/** Même calcul que slug() dans outils/extraire.py : sert aux ancres des titres de section. */
function ancre(texte) {
  return normaliser(texte).replace(/[^a-z0-9]+/g, "-").replace(/^-+|-+$/g, "").slice(0, 60);
}

/** Un résultat : la fiche à télécharger, et en dessous un lien vers l'endroit où elle se trouve. */
function ligneRessource(r, page) {
  const image = r.image
    ? `<img src="${r.image}" alt="" loading="lazy">`
    : `<span class="vignette-vide" aria-hidden="true">${r.type.toUpperCase().slice(0, 4)}</span>`;
  const ou = page
    ? `<a class="voir-page" href="${page.fichier}${r.section ? "#" + ancre(r.section) : ""}">
        Dans : ${echapper(page.nom)}${r.section ? " › " + echapper(r.section) : ""}</a>`
    : "";
  return `<li class="resultat"><a class="ressource" href="${lienFichier(r)}" target="_blank" rel="noopener">
    ${image}
    <span class="infos"><span class="titre">${echapper(r.titre)}</span></span>
    <span class="etiquette ${r.type}">${r.type}</span>
    <span class="poids">${poids(r.taille)}</span>
  </a>${ou}</li>`;
}

/** Recherche : tous les mots tapés doivent se trouver dans le titre, la section ou la page.
 *  « garder » limite la recherche (par exemple aux fiches d'un seul thème). */
function brancherRecherche(champ, liste, compte, garder = () => true) {
  chargerDonnees().then((donnees) => {
    const themes = donnees.themes;
    const ressources = donnees.ressources.filter(garder);
    const pagesParId = {};
    for (const t of themes) for (const p of t.pages) pagesParId[p.id] = { fichier: p.fichier, nom: `${t.titre} › ${p.titre}` };
    const index = ressources.map((r) => normaliser(`${r.titre} ${r.section || ""} ${pagesParId[r.page]?.nom || ""}`));

    let minuteur;
    champ.addEventListener("input", () => {
      clearTimeout(minuteur);
      minuteur = setTimeout(() => {
        const mots = normaliser(champ.value).split(/\s+/).filter(Boolean);
        if (!mots.length) {
          liste.innerHTML = "";
          compte.textContent = "";
          return;
        }
        const trouves = ressources.filter((_, i) => mots.every((m) => index[i].includes(m)));
        const MAX = 40;
        liste.innerHTML = trouves.slice(0, MAX).map((r) => ligneRessource(r, pagesParId[r.page])).join("");
        compte.textContent = trouves.length === 0
          ? "Aucune fiche trouvée. Essayez un autre mot."
          : trouves.length > MAX
            ? `${trouves.length} fiches trouvées — les ${MAX} premières sont affichées, précisez votre recherche.`
            : `${trouves.length} fiche${trouves.length > 1 ? "s" : ""} trouvée${trouves.length > 1 ? "s" : ""}.`;
      }, 150);
    });
  });
}

// ---------- Confort de lecture (police dys, taille du texte, espacement) ----------
// Les choix sont mémorisés dans le navigateur du visiteur et appliqués sur toutes les pages.

const CONFORT_DEFAUT = { police: "normale", taille: "1", espacement: "normal" };

function lireConfort() {
  try {
    return { ...CONFORT_DEFAUT, ...JSON.parse(localStorage.getItem("confort") || "{}") };
  } catch {
    return { ...CONFORT_DEFAUT };
  }
}

function appliquerConfort(confort) {
  const racine = document.documentElement;
  racine.dataset.police = confort.police;
  racine.dataset.taille = confort.taille;
  racine.dataset.espacement = confort.espacement;
  // La police OpenDyslexic n'est téléchargée que si quelqu'un la choisit.
  if (confort.police === "dys" && !document.getElementById("police-dys")) {
    for (const graisse of ["400", "700"]) {
      const lien = document.createElement("link");
      lien.rel = "stylesheet";
      lien.href = `https://cdn.jsdelivr.net/npm/@fontsource/opendyslexic@5.3.0/${graisse}.css`;
      if (graisse === "400") lien.id = "police-dys";
      document.head.appendChild(lien);
    }
  }
}

appliquerConfort(lireConfort());

function brancherConfort() {
  const entete = document.querySelector(".entete .conteneur");
  if (!entete) return;
  const choix = [
    ["police", "Police", [["normale", "Habituelle"], ["dys", "Adaptée dys"]]],
    ["taille", "Taille du texte", [["1", "A"], ["2", "A+"], ["3", "A++"]]],
    ["espacement", "Espacement", [["normal", "Normal"], ["large", "Large"]]],
  ];
  const conteneur = document.createElement("div");
  conteneur.className = "confort";
  conteneur.innerHTML = `
    <button type="button" class="bouton-confort" aria-expanded="false" aria-controls="panneau-confort" title="Confort de lecture">
      <span aria-hidden="true">Aa</span><span class="libelle">Confort de lecture</span>
    </button>
    <div class="panneau-confort" id="panneau-confort" hidden>
      ${choix.map(([cle, titre, options]) => `<fieldset>
        <legend>${titre}</legend>
        ${options.map(([valeur, nom]) => `<button type="button" data-cle="${cle}" data-valeur="${valeur}">${nom}</button>`).join("")}
      </fieldset>`).join("")}
      <button type="button" class="reinitialiser">Revenir à l'affichage habituel</button>
    </div>`;
  entete.appendChild(conteneur);

  const bouton = conteneur.querySelector(".bouton-confort");
  const panneau = conteneur.querySelector(".panneau-confort");
  const actualiser = () => {
    const confort = lireConfort();
    for (const b of panneau.querySelectorAll("[data-cle]")) {
      b.setAttribute("aria-pressed", confort[b.dataset.cle] === b.dataset.valeur);
    }
  };
  const enregistrer = (confort) => {
    try {
      localStorage.setItem("confort", JSON.stringify(confort));
    } catch {
      // navigation privée : le choix vaut seulement pour cette page
    }
    appliquerConfort(confort);
    actualiser();
  };
  const ouvrir = (ouvert) => {
    panneau.hidden = !ouvert;
    bouton.setAttribute("aria-expanded", ouvert);
  };

  bouton.addEventListener("click", () => ouvrir(panneau.hidden));
  panneau.addEventListener("click", (e) => {
    const b = e.target.closest("button");
    if (!b) return;
    if (b.classList.contains("reinitialiser")) {
      try { localStorage.removeItem("confort"); } catch { /* rien à effacer */ }
      appliquerConfort(CONFORT_DEFAUT);
      actualiser();
      return;
    }
    enregistrer({ ...lireConfort(), [b.dataset.cle]: b.dataset.valeur });
  });
  // Fermer en cliquant ailleurs ou avec Échap
  document.addEventListener("click", (e) => {
    if (!conteneur.contains(e.target)) ouvrir(false);
  });
  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape" && !panneau.hidden) {
      ouvrir(false);
      bouton.focus();
    }
  });
  actualiser();
}

function brancherBandeAncienSite() {
  if (!ANCIEN_SITE) return;
  const bande = document.createElement("div");
  bande.className = "bande-ancien-site";
  bande.innerHTML = `<div class="conteneur">
    <span>Bienvenue sur le nouveau site de Methodolodys.</span>
    <a href="${ANCIEN_SITE}" rel="noopener">Aller sur l'ancien site <span aria-hidden="true">→</span></a>
  </div>`;
  document.body.prepend(bande);
}

document.addEventListener("DOMContentLoaded", () => {
  brancherBandeAncienSite();
  brancherConfort();

  // Liens vers des fichiers écrits « fichier:2016/09/x.pdf » dans les pages de texte
  for (const a of document.querySelectorAll('a[href^="fichier:"]')) {
    a.href = lienFichier({ fichier: a.getAttribute("href").slice("fichier:".length) });
  }

  // Bouton pour remonter en haut, qui apparaît quand on a descendu dans la page
  const haut = document.createElement("button");
  haut.className = "remonter";
  haut.type = "button";
  haut.setAttribute("aria-label", "Remonter en haut de la page");
  haut.title = "Remonter en haut";
  haut.innerHTML = '<svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M12 19V5M5 12l7-7 7 7"/></svg>';
  haut.addEventListener("click", () => window.scrollTo({ top: 0, behavior: "smooth" }));
  document.body.appendChild(haut);
  const montrer = () => haut.classList.toggle("visible", window.scrollY > 600);
  window.addEventListener("scroll", montrer, { passive: true });
  montrer();

  // Menu sur téléphone
  const bouton = document.querySelector(".bouton-menu");
  const menu = document.querySelector(".menu");
  if (bouton && menu) {
    bouton.addEventListener("click", () => {
      const ouvert = menu.classList.toggle("ouvert");
      bouton.setAttribute("aria-expanded", ouvert);
    });
    menu.addEventListener("click", (e) => {
      if (e.target.closest("a")) {
        menu.classList.remove("ouvert");
        bouton.setAttribute("aria-expanded", false);
      }
    });
  }
});
