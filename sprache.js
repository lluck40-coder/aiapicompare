// Gemeinsame Sprachumschaltung für Impressum und Datenschutz.
// Die deutsche Fassung ist maßgeblich; die übrigen Sprachen übernehmen
// die Angaben (Name, Anschrift …) automatisch aus dem deutschen Block.
(function () {
  "use strict";
  function lsGet(k){ try { return localStorage.getItem(k); } catch(e){ return null; } }
  function lsSet(k,v){ try { localStorage.setItem(k,v); } catch(e){} }
  const vorhanden = Array.prototype.map.call(document.querySelectorAll("[data-sprache]"), function(b){ return b.dataset.sprache; });
  let lang = lsGet("lang") || (navigator.language || "").slice(0,2);
  if (vorhanden.indexOf(lang) < 0) lang = vorhanden.indexOf("en") >= 0 && lang !== "de" ? "en" : "de";

  // Angaben aus dem deutschen Block in die Übersetzungen kopieren
  document.querySelectorAll("[data-v]").forEach(function(el){
    const q = document.getElementById(el.dataset.v);
    if (q) el.innerHTML = q.innerHTML;
  });

  const titel = {de: document.title};
  document.querySelectorAll("[data-titel]").forEach(function(el){ titel[el.dataset.titel.split("|")[0]] = el.dataset.titel.split("|")[1]; });

  function zeige(){
    document.querySelectorAll("[data-sprache]").forEach(function(b){ b.classList.toggle("zeigen", b.dataset.sprache === lang); });
    document.querySelectorAll(".langbtns button").forEach(function(b){ b.classList.toggle("active", b.dataset.lang === lang); });
    document.querySelectorAll("[data-nav]").forEach(function(a){ a.textContent = a.dataset["nav" + lang.charAt(0).toUpperCase() + lang.slice(1)] || a.dataset.nav; });
    document.documentElement.lang = lang === "zh" ? "zh-CN" : lang;
    if (titel[lang]) document.title = titel[lang];
  }
  document.querySelector(".langbtns").addEventListener("click", function(e){
    const b = e.target.closest("button[data-lang]"); if (!b) return;
    lang = b.dataset.lang; lsSet("lang", lang); zeige();
  });
  // Vorlage-Hinweis ausblenden, sobald alle Platzhalter ersetzt sind
  if (!document.querySelector('[data-sprache="de"] .ph')) document.querySelectorAll(".vorlage").forEach(function(v){ v.hidden = true; });
  zeige();
})();
