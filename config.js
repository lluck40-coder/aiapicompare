// =====================================================================
//  config.js – zentrale Einstellungen für alle Seiten
// =====================================================================
window.SITE_CONFIG = {

  seitenname: "aiapicompare",

  // Startseiten der Anbieter – für „Zum Anbieter“ / „Konto erstellen“ und
  // damit die Statistik Klicks dem richtigen Anbieter zuordnen kann.
  anbieter: {
    openrouter:   "https://openrouter.ai",
    uplinkswitch: "https://uplinkswitch.ai",
    anymodel:     "https://anymodel.org",
    nanogpt:      "https://nano-gpt.com",
    chutes:       "https://chutes.ai",
    deepinfra:    "https://deepinfra.com",
    novita:       "https://novita.ai",
    cometapi:     "https://www.cometapi.com",
    kyma:         "https://kymaapi.com"
  },

  // Besucherstatistik mit Umami Cloud (ohne Cookies). Das Skript wird NUR
  // geladen, nachdem jemand im Cookie-Fenster „Akzeptieren“ gewählt hat
  // (siehe einwilligung.js).
  // So füllst du es aus: Umami-Dashboard → Websites → Website bearbeiten →
  // „Tracking-Code“. Dort stehen src="…" (→ script) und data-website-id="…"
  // (→ websiteId). Enthält der Code data-host-url="…", das bei hostUrl eintragen.
  // Solange websiteId leer ist, bleibt die Statistik aus und es erscheint
  // KEIN Cookie-Fenster (es gibt dann nichts, wozu man einwilligen müsste).
  statistik: {
    websiteId: "0afb117f-50e6-446a-a1d4-c40c433b9b47",    // aus dem Umami-Tracking-Code (24.11.2026)
    script:    "https://cloud.umami.is/script.js",
    hostUrl:   "",
    domains:   "aiapicompare.com,www.aiapicompare.com"    // nur auf diesen Adressen zählen (nicht bei Tests)
  }
};

// ---------------------------------------------------------------------
//  Hilfsfunktionen (nicht ändern)
// ---------------------------------------------------------------------
(function () {
  "use strict";
  const C = window.SITE_CONFIG;

  // Liefert {url}. url leer/null = Startseite des Anbieters.
  C.link = function (anbieterKey, url) {
    return { url: url || (C.anbieter || {})[anbieterKey] || "" };
  };

  C.linkHtml = function (anbieterKey, url, text, cls, titel) {
    const l = C.link(anbieterKey, url);
    if (!l.url) return "";
    const esc = function (s) { return String(s).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;"); };
    return '<a class="' + (cls || "") + '" href="' + esc(l.url) + '" target="_blank" rel="noopener"' +
      (anbieterKey ? ' data-anbieter="' + esc(anbieterKey) + '"' : "") +
      (titel ? ' title="' + esc(titel) + '"' : "") + ">" + text + "</a>";
  };
})();
