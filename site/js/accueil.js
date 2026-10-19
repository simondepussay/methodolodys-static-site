// Page d'accueil : thèmes et recherche, construits à partir de data/ressources.json.

/** Une carte par grand thème, avec ses sous-parties. */
function afficherThemes(themes, ressources) {
  const parTheme = {};
  for (const r of ressources) parTheme[r.theme] = (parTheme[r.theme] || 0) + 1;

  document.getElementById("themes").innerHTML = themes.map((t) => {
    const n = parTheme[t.id] || 0;
    const unite = t.id === "tutoriels" ? "vidéo" : "fiche";
    // Seules les parties principales : les histoires, les lettres du dictionnaire… sont rangées dessous.
    const sousPages = t.pages.filter((p) => !p.parent);
    return `<article class="theme">
      <a href="${t.id}.html">
        <div class="image"><img src="images/themes/${t.id}.webp" alt="" loading="lazy"></div>
        <div class="corps">
          <h3>${echapper(t.titre)}</h3>
          <span class="nombre">${n.toLocaleString("fr-CH")} ${unite}${n > 1 ? "s" : ""}</span>
        </div>
      </a>
      ${sousPages.length > 1 ? `<ul>${sousPages.map((p) =>
        `<li><a href="${lienPage(p)}">${echapper(p.titre)}</a></li>`).join("")}</ul>` : ""}
    </article>`;
  }).join("");
}

chargerDonnees().then(({ themes, ressources }) => {
  document.getElementById("total").textContent = ressources.length.toLocaleString("fr-CH");
  afficherThemes(themes, ressources);
});

brancherRecherche(
  document.getElementById("champ-recherche"),
  document.getElementById("resultats"),
  document.getElementById("compte"),
);
