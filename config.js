// =====================================================================
//  config.js – zentrale Einstellungen für alle Seiten
//  Hier tragen Sie Ihre Affiliate-/Empfehlungslinks ein.
//
//  So funktioniert es:
//   aktiv      : true  = Programm ist eingerichtet, Links werden gekennzeichnet
//   startseite : Ihr persönlicher Empfehlungslink (z. B. https://nano-gpt.com/r/CODE).
//                Wird für die Buttons "Zum Anbieter" / "Konto erstellen" verwendet.
//   parameter  : NUR wenn das Programm einen Link-Zusatz erlaubt (z. B. "ref=CODE"
//                oder "via=CODE"). Dann werden auch alle Modell-Links zum Anbieter
//                zu Affiliate-Links. Leer lassen, wenn es nur einen festen Link gibt.
//
//  Gekennzeichnet ("Anzeige", rel="sponsored") wird ein Link nur, wenn er
//  wirklich Ihre Partnerkennung enthält – also nicht versehentlich normale Links.
//
//  Die Felder "programm", "provision" und "anmeldung" sind nur Notizen für Sie
//  (Stand: Recherche 22.11.2026 – Bedingungen ändern sich, bitte vor Anmeldung prüfen).
// =====================================================================
window.SITE_CONFIG = {

  seitenname: "aiapicompare",

  // Kennzeichnung direkt am Link. Empfehlung: "Anzeige" oder "Werbung".
  kennzeichnung: "Anzeige",

  affiliate: {
    // ---------- Anbieter mit bezahltem Partnerprogramm ----------
    cometapi: {
      aktiv: false, parameter: "", startseite: "https://www.cometapi.com",
      programm: "Affiliate (Tolt)", provision: "20 % jeder Aufladung, 120 Tage Cookie",
      anmeldung: "https://www.cometapi.com/affiliate/"
    },
    uplinkswitch: {
      aktiv: false, parameter: "", startseite: "https://uplinkswitch.ai",
      programm: "Affiliate über Whop", provision: "30 % (Whop-Standard), Auszahlung nach 30 Tagen",
      anmeldung: "https://whop.com/uplinkswitch-0fbc/"
    },
    kyma: {
      aktiv: false, parameter: "", startseite: "https://kymaapi.com",
      programm: "Affiliate (Affitor)", provision: "12 % wiederkehrend für 18 Monate, 30 Tage Cookie, ab 20 $",
      anmeldung: "https://openaffiliate.dev/programs/kyma-api"
    },
    novita: {
      aktiv: false, parameter: "", startseite: "https://novita.ai",
      programm: "Affiliate (Tapfiliate)", provision: "10 % der Ausgaben für 180 Tage, Auszahlung ab 50 $",
      anmeldung: "https://novita.ai/affiliate"
    },
    nanogpt: {
      aktiv: false, parameter: "", startseite: "https://nano-gpt.com",
      programm: "Empfehlungslink (Konto → Earn)", provision: "10 % Umsatzbeteiligung (in Nano), Geworbene erhalten 5 % Rabatt",
      anmeldung: "https://nano-gpt.com/earn"
    },

    // ---------- Anbieter ohne bekanntes Partnerprogramm (normale Links) ----------
    openrouter: { aktiv: false, parameter: "", startseite: "https://openrouter.ai",  programm: "keins gefunden (nur Startup-Programm)" },
    anymodel:   { aktiv: false, parameter: "", startseite: "https://anymodel.org",   programm: "keins gefunden" },
    chutes:     { aktiv: false, parameter: "", startseite: "https://chutes.ai",      programm: "keins gefunden" },
    deepinfra:  { aktiv: false, parameter: "", startseite: "https://deepinfra.com",  programm: "keins gefunden (nur Startup-Credits)" }
  }
};

// ---------------------------------------------------------------------
//  Hilfsfunktionen (nicht ändern)
// ---------------------------------------------------------------------
(function () {
  "use strict";
  const C = window.SITE_CONFIG;

  // Liefert {url, affiliate}. url leer/null = Startseite (Empfehlungslink) des Anbieters.
  C.link = function (anbieterKey, url) {
    const a = (C.affiliate || {})[anbieterKey];
    const startseite = (a && a.startseite) || "";
    const istStart = !url;
    url = url || startseite;
    if (!a || !a.aktiv || !url) return { url: url, affiliate: false };
    if (a.parameter) {
      const hashPos = url.indexOf("#");
      const hash = hashPos >= 0 ? url.slice(hashPos) : "";
      const basis = hashPos >= 0 ? url.slice(0, hashPos) : url;
      return { url: basis + (basis.indexOf("?") >= 0 ? "&" : "?") + a.parameter + hash, affiliate: true };
    }
    // Ohne Parameter trägt nur der Empfehlungslink selbst die Partnerkennung
    return { url: url, affiliate: istStart };
  };

  C.linkHtml = function (anbieterKey, url, text, cls, titel) {
    const l = C.link(anbieterKey, url);
    if (!l.url) return "";
    const esc = function (s) { return String(s).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;"); };
    const rel = l.affiliate ? "sponsored noopener" : "noopener";
    const t = l.affiliate ? (titel ? titel + " – " : "") + C.kennzeichnung + ": Affiliate-Link, wir erhalten ggf. eine Provision" : (titel || "");
    return '<a class="' + (cls || "") + (l.affiliate ? " aff" : "") + '" href="' + esc(l.url) + '" target="_blank" rel="' + rel + '"' +
      (t ? ' title="' + esc(t) + '"' : "") + ">" + text +
      (l.affiliate ? ' <span class="adlabel">' + esc(C.kennzeichnung) + "</span>" : "") + "</a>";
  };

  C.hatAffiliate = function () {
    return Object.keys(C.affiliate || {}).some(function (k) { return C.affiliate[k].aktiv; });
  };
})();
