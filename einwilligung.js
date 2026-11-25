/* =====================================================================
   einwilligung.js – Cookie-Fenster (Einwilligung) und Besucherstatistik
   ---------------------------------------------------------------------
   • Beim ersten Besuch erscheint ein Fenster mit „Ablehnen“ und
     „Akzeptieren“ – beide gleich groß und gleich gestaltet (DSGVO/TDDDG).
   • Erst nach „Akzeptieren“ wird das Statistik-Skript (Umami, ohne
     Cookies) geladen. Vorher wird nichts übertragen. Gespeichert wird nur
     die Entscheidung selbst (localStorage „einwilligung“, 12 Monate).
   • Gezählt werden Seitenaufrufe und Klicks: Links zu Anbietern und zu
     anderen Websites, Sprache, hell/dunkel, Filter und Auswahlfelder,
     Kopier-Knöpfe. Eingaben in Text-, Zahlen- und Suchfeldern nie.
   • In jeder Fußzeile (.legal) erscheint automatisch „Cookie-Einstellungen“.
     Darüber lässt sich die Entscheidung jederzeit ändern (Widerruf).
   • Einstellungen stehen in config.js unter „statistik“. Ohne Website-ID
     bleibt alles aus: kein Fenster, kein Skript, keine Zählung.
   • Seiten-Skripte können eigene Ereignisse melden: window.aacEreignis(name, {…})
     (ohne Einwilligung passiert dabei nichts).
   ===================================================================== */
(function () {
  "use strict";
  var CFG = (window.SITE_CONFIG && window.SITE_CONFIG.statistik) || {};
  var AKTIV = !!(CFG.websiteId && CFG.script);
  var KEY = "einwilligung", VERSION = 1, GUELTIG_TAGE = 365;
  var skript = document.currentScript;
  var BASIS = skript && skript.src ? skript.src.replace(/[?#].*$/, "").replace(/[^\/]*$/, "") : "";
  var zustand = null;            // true = erlaubt, false = abgelehnt, null = noch keine Entscheidung
  var geladen = false, warte = [], fenster = null, vorherFokus = null;

  /* ---------------- Texte ---------------- */
  var TXT = {
    de: {
      titel: "Cookies &amp; Statistik",
      text: "Mit deiner Einwilligung zählen wir, wie viele Besucher kommen und was angeklickt wird (z.&nbsp;B. „Zum Anbieter“, Filter, Sprache). Dafür nutzen wir <b>Umami</b> – ohne Cookies, ohne Werbung, ohne Nutzerprofile; IP-Adressen werden nicht gespeichert. Anbieter: Umami Software, Inc. (USA); die Daten liegen in der EU, ein Zugriff aus den USA ist aber nicht ausgeschlossen. Ablehnen hat keine Nachteile.",
      noetig: "Immer aktiv (technisch nötig): Sprache, Ansicht, hell/dunkel und diese Wahl werden nur in deinem Browser gespeichert. Ändern kannst du deine Wahl jederzeit unten über „Cookie-Einstellungen“.",
      nein: "Ablehnen", ja: "Akzeptieren",
      stand_ja: "Aktuell: Statistik erlaubt.", stand_nein: "Aktuell: Statistik abgelehnt.", stand_offen: "Aktuell: noch keine Entscheidung.",
      datenschutz: "Datenschutzerklärung", impressum: "Impressum", einstellungen: "Cookie-Einstellungen", nutzung: "Nutzungsbedingungen", anker: "statistik"
    },
    en: {
      titel: "Cookies &amp; statistics",
      text: "With your consent, we count how many people visit and what they click (e.g. “Go to provider”, filters, language). We use <b>Umami</b> for this – no cookies, no ads, no user profiles; IP addresses are not stored. Provider: Umami Software, Inc. (USA); the data is stored in the EU, but access from the USA cannot be ruled out. Declining has no downside.",
      noetig: "Always active (technically necessary): language, view, light/dark mode and this choice are stored only in your browser. You can change your choice at any time via “Cookie settings” at the bottom.",
      nein: "Decline", ja: "Accept",
      stand_ja: "Current setting: statistics allowed.", stand_nein: "Current setting: statistics declined.", stand_offen: "Current setting: no choice made yet.",
      datenschutz: "Privacy policy", impressum: "Imprint", einstellungen: "Cookie settings", nutzung: "Terms of use", anker: "statistik-en"
    },
    zh: {
      titel: "Cookie 与访问统计",
      text: "经您同意后，我们会统计访问人数以及点击内容（例如“前往提供商”、筛选、语言）。为此我们使用 <b>Umami</b>：不使用 Cookie、无广告、不建立用户画像，也不保存 IP 地址。服务商：Umami Software, Inc.（美国）；数据存储在欧盟，但不能排除从美国访问的可能。拒绝不会带来任何不便。",
      noetig: "始终启用（技术必需）：语言、视图、浅色/深色模式以及本次选择仅保存在您的浏览器中。您可随时通过页面底部的“Cookie 设置”更改选择。",
      nein: "拒绝", ja: "接受",
      stand_ja: "当前设置：已允许统计。", stand_nein: "当前设置：已拒绝统计。", stand_offen: "当前设置：尚未选择。",
      datenschutz: "隐私政策", impressum: "网站信息", einstellungen: "Cookie 设置", nutzung: "使用条款", anker: "statistik-zh"
    },
    ru: {
      titel: "Cookie и статистика",
      text: "С вашего согласия мы считаем, сколько людей посещает сайт и что они нажимают (например, «К поставщику», фильтры, язык). Для этого мы используем <b>Umami</b> – без cookie, без рекламы, без профилей пользователей; IP-адреса не сохраняются. Поставщик: Umami Software, Inc. (США); данные хранятся в ЕС, но доступ из США исключить нельзя. Отказ ни на что не влияет.",
      noetig: "Всегда активно (технически необходимо): язык, вид, светлая/тёмная тема и этот выбор сохраняются только в вашем браузере. Изменить выбор можно в любой момент внизу страницы через «Настройки cookie».",
      nein: "Отклонить", ja: "Принять",
      stand_ja: "Сейчас: статистика разрешена.", stand_nein: "Сейчас: статистика отклонена.", stand_offen: "Сейчас: выбор ещё не сделан.",
      datenschutz: "Политика конфиденциальности", impressum: "Импрессум", einstellungen: "Настройки cookie", nutzung: "Условия использования", anker: "statistik-en"
    }
  };
  function sprache() {
    var l = (document.documentElement.getAttribute("lang") || "").slice(0, 2).toLowerCase();
    if (TXT[l]) return l;
    try { l = localStorage.getItem("lang") || ""; } catch (e) { l = ""; }
    if (TXT[l]) return l;
    l = (navigator.language || "").slice(0, 2).toLowerCase();
    return TXT[l] ? l : "en";
  }
  function T() { return TXT[sprache()]; }

  /* ---------------- Entscheidung speichern ---------------- */
  function speicher() { try { return window.localStorage; } catch (e) { return null; } }
  function lesen() {
    var r = null, s = speicher();
    try { r = s ? JSON.parse(s.getItem(KEY)) : null; } catch (e) { r = null; }
    if (!r || r.v !== VERSION || typeof r.statistik !== "boolean") return null;
    var t = Date.parse(r.datum);
    if (!t || (Date.now() - t) / 864e5 > GUELTIG_TAGE) return null;   // nach 12 Monaten neu fragen
    return r.statistik;
  }
  function merken(ja) {
    var s = speicher();
    try { if (s) s.setItem(KEY, JSON.stringify({ v: VERSION, statistik: ja, datum: new Date().toISOString().slice(0, 10) })); } catch (e) {}
  }

  /* ---------------- Statistik-Skript (erst nach Einwilligung) ---------------- */
  // Prüft vor JEDER Übertragung, ob die Einwilligung noch besteht (wirkt sofort beim Widerruf).
  window.aacVorSenden = function (typ, daten) { return zustand === true ? daten : false; };
  function laden() {
    if (geladen || !AKTIV) return;
    geladen = true;
    var s = document.createElement("script");
    s.async = true;
    s.src = CFG.script;
    s.setAttribute("data-website-id", CFG.websiteId);
    if (CFG.hostUrl) s.setAttribute("data-host-url", CFG.hostUrl);
    if (CFG.domains) s.setAttribute("data-domains", CFG.domains);
    s.setAttribute("data-exclude-search", "true");   // keine Suchparameter …
    s.setAttribute("data-exclude-hash", "true");     // … und nichts hinter dem # (Filter, Suchbegriffe)
    s.setAttribute("data-before-send", "aacVorSenden");
    s.onload = leeren;
    document.head.appendChild(s);
  }
  function senden(name, daten) {
    if (!AKTIV || zustand !== true) return;
    var u = window.umami;
    if (u && typeof u.track === "function") { try { u.track(name, daten); } catch (e) {} }
    else if (warte.length < 50) warte.push([name, daten]);
  }
  function leeren() { var w = warte; warte = []; w.forEach(function (x) { senden(x[0], x[1]); }); }
  function kurz(s, n) { s = String(s == null ? "" : s).replace(/\s+/g, " ").trim(); return s.length > n ? s.slice(0, n - 1) + "…" : s; }
  function seite() { return location.pathname || "/"; }
  window.aacEreignis = function (name, daten) {
    var d = {}, n = 0;
    Object.keys(daten || {}).forEach(function (k) {
      var v = daten[k];
      if (n < 10 && (typeof v === "string" || typeof v === "number" || typeof v === "boolean")) { d[k] = typeof v === "string" ? kurz(v, 200) : v; n++; }
    });
    if (!d.seite) d.seite = seite();
    senden(kurz(name, 50), d);
  };

  /* ---------------- Was angeklickt wird ---------------- */
  var FELD = {
    anb: "Anbieter", typ: "Modelltyp", cap: "Fähigkeit", fam: "Modellfamilie",
    bestchk: "Nur günstigster", multichk: "Mehrere Anbieter", gratischk: "Nur kostenlose", auffchk: "Weit unter Referenz ausblenden",
    ctxrange: "Kontext ab", prange: "Input-Preis bis", sortsel: "Sortierung", sort: "Sortierung", view: "Ansicht",
    zweck: "Finder: Zweck", budget: "Finder: Budget", prio: "Finder: Priorität",
    modus: "Rechner: Modus", ctx: "Kontext", gratis: "Kostenlose einbeziehen", auff: "Weit unter Referenz einbeziehen",
    batch: "Batch einbeziehen", nurpreis: "Nur mit Preis", auchauff: "Weit unter Referenz einbeziehen",
    tool: "Anbindung: Werkzeug", s: "Widget: Modell", wlang: "Widget: Sprache", wtheme: "Widget: Design",
    b: "Bestenliste: Bereich", f: "Neuigkeiten: Filter"
  };
  var WAHL = ["modus", "view", "tool", "anb", "s", "b", "f"];   // Knöpfe, die eine Auswahl treffen (data-…)
  function text(el) { return el.getAttribute("aria-label") || el.getAttribute("title") || el.textContent || ""; }
  function anbieterVonHost(h) {
    var A = (window.SITE_CONFIG && window.SITE_CONFIG.anbieter) || {};
    h = h.replace(/^www\./, "");
    for (var k in A) {
      var ah = "";
      try { ah = new URL(A[k]).hostname.replace(/^www\./, ""); } catch (e) { continue; }
      if (h === ah || h.slice(-(ah.length + 1)) === "." + ah) return k;
    }
    return "";
  }
  function link(a) {
    var href = a.getAttribute("href") || "", p = { seite: seite() }, u;
    if (/^mailto:/i.test(href)) return senden("E-Mail", p);
    if (a.hasAttribute("data-setlang")) { p.sprache = a.getAttribute("data-setlang"); return senden("Sprache", p); }
    try { u = new URL(a.href, location.href); } catch (e) { return; }
    if (u.protocol !== "http:" && u.protocol !== "https:") return;
    if (u.hostname === location.hostname) {
      if (/\.(json|xml|txt|csv)$/i.test(u.pathname)) { p.datei = u.pathname; return senden("Datei", p); }   // API, RSS …
      if (href.charAt(0) === "#" && href.length > 1) { p.element = kurz(href, 100); senden("Klick", p); }
      return;   // normale interne Links zählen als Seitenaufruf der Zielseite
    }
    var anb = a.getAttribute("data-anbieter") || a.getAttribute("data-anb") || anbieterVonHost(u.hostname);
    p.ziel = kurz(u.hostname.replace(/^www\./, "") + u.pathname.replace(/\/+$/, ""), 150);
    if (anb) { p.anbieter = anb; senden("Zum Anbieter", p); } else senden("Externer Link", p);
  }
  function knopf(b) {
    var d = b.dataset || {}, p = { seite: seite() };
    if (d.cmp !== undefined) return;                         // meldet die Seite selbst („Vergleich geöffnet“)
    if (d.lang) { p.sprache = d.lang; return senden("Sprache", p); }
    if (b.classList.contains("themebtn")) {
      p.modus = document.documentElement.getAttribute("data-theme") === "light" ? "dunkel" : "hell";   // Zustand NACH dem Umschalten
      return senden("Design", p);
    }
    if (b.tagName === "TH") { p.feld = FELD.sort; p.wert = d.sort; return senden("Auswahl", p); }
    if (/(^|\s)(copy|kopier)(\s|$)/.test(b.className) || b.id === "kopieren") {
      p.element = kurz(d.id || d.copy || b.id || text(b), 100); return senden("Kopiert", p);
    }
    if (d.k !== undefined) { p.feld = FELD[d.k] || d.k; p.wert = kurz(d.v || "", 100); return senden("Auswahl", p); }
    for (var i = 0; i < WAHL.length; i++) {
      if (d[WAHL[i]]) { p.feld = FELD[WAHL[i]] || WAHL[i]; p.wert = kurz(d[WAHL[i]], 100); return senden("Auswahl", p); }
    }
    p.element = kurz(b.id ? "#" + b.id : (d.t || (d.clear ? "clear=" + d.clear : text(b))), 80);
    senden("Klick", p);
  }
  function klick(e) {
    if (zustand !== true) return;
    var t = e.target;
    if (!t || !t.closest || t.closest("#aac-cmp,[data-cookie-einstellungen],[data-cookie-knopf]")) return;
    var a = t.closest("a[href]");
    if (a) return link(a);
    var b = t.closest("button,[role=button],th[data-sort]");
    if (b) knopf(b);
  }
  function aenderung(e) {
    if (zustand !== true) return;
    var el = e.target;
    if (!el || !el.tagName || (el.closest && el.closest("#aac-cmp"))) return;
    var tag = el.tagName, typ = (el.type || "").toLowerCase(), g = el.getAttribute("data-g"), wert;
    if (tag === "SELECT") wert = el.value;
    else if (tag === "INPUT" && (typ === "checkbox" || typ === "radio")) wert = g ? el.value + (el.checked ? "" : " (aus)") : (typ === "radio" ? el.value : (el.checked ? "an" : "aus"));
    else if (tag === "INPUT" && typ === "range") wert = el.value;
    else return;   // Text-, Zahlen- und Suchfelder werden nie erfasst
    var feld = g || el.id || el.name || "";
    senden("Auswahl", { feld: FELD[feld] || feld, wert: kurz(wert, 100), seite: seite() });
  }

  /* ---------------- Fenster ---------------- */
  var CSS =
    ".aac-cmp{position:fixed;inset:0;z-index:2147483000;display:flex;align-items:center;justify-content:center;padding:16px;background:rgba(0,0,0,.5);font:14px/1.5 system-ui,-apple-system,'Segoe UI',Roboto,Ubuntu,sans-serif;color:var(--fg,#e8e9eb)}" +
    "[data-theme=light] .aac-cmp{background:rgba(15,23,42,.35)}" +
    ".aac-cmp.aac-frei{background:none;pointer-events:none;align-items:flex-end}" +
    ".aac-box{pointer-events:auto;box-sizing:border-box;width:100%;max-width:560px;max-height:calc(100vh - 32px);max-height:calc(100dvh - 32px);overflow:auto;background:var(--panel,#121418);color:var(--fg,#e8e9eb);border:1px solid var(--border2,#2e323a);border-radius:14px;box-shadow:0 20px 60px rgba(0,0,0,.45);padding:20px 22px 16px;outline:none;text-align:left}" +
    "[data-theme=light] .aac-box{box-shadow:0 20px 60px rgba(15,23,42,.2)}" +
    ".aac-box h2{margin:0 0 8px;font-size:17px;line-height:1.3;font-weight:700;color:inherit}" +
    ".aac-box p{margin:0 0 10px}.aac-box b{font-weight:650}" +
    ".aac-klein{font-size:12.5px;color:var(--muted,#8d939c)}" +
    ".aac-knoepfe{display:flex;gap:10px;margin:14px 0 12px}" +
    ".aac-knoepfe button{flex:1 1 0;min-height:44px;padding:8px 14px;border-radius:9px;border:1px solid var(--border2,#2e323a);background:var(--panel2,#171a1f);color:var(--fg,#e8e9eb);font:inherit;font-weight:650;cursor:pointer}" +
    ".aac-knoepfe button:hover,.aac-knoepfe button:focus-visible{border-color:var(--accent,#4ade80);color:var(--accent,#4ade80);outline:none}" +
    ".aac-links{font-size:12.5px;color:var(--muted,#8d939c)}.aac-links a{color:inherit;text-decoration:underline}" +
    "@media (max-width:600px){.aac-cmp{align-items:flex-end;padding:8px}.aac-box{padding:14px 15px 10px;font-size:13.5px;line-height:1.45;max-height:calc(100vh - 16px);max-height:calc(100dvh - 16px)}.aac-box h2{font-size:16px;margin-bottom:6px}.aac-klein,.aac-links{font-size:12px}.aac-knoepfe{margin:10px 0}}" +
    "@media (prefers-reduced-motion:no-preference){.aac-box{animation:aac-ein .2s ease-out}}" +
    "@keyframes aac-ein{from{opacity:0;transform:translateY(10px)}to{opacity:1;transform:none}}" +
    "@media print{.aac-cmp{display:none!important}}";
  function stil() {
    if (document.getElementById("aac-cmp-stil")) return;
    var st = document.createElement("style");
    st.id = "aac-cmp-stil"; st.textContent = CSS;
    document.head.appendChild(st);
  }
  function oeffnen(erneut) {
    if (!AKTIV) return;
    var fokus = fenster ? vorherFokus : document.activeElement;
    schliessen(true);
    vorherFokus = fokus;
    stil();
    var t = T();
    var frei = /(^|\/)(datenschutz|impressum)\.html$/.test(location.pathname);   // Rechtstexte bleiben lesbar
    var d = document.createElement("div");
    d.id = "aac-cmp";
    d.className = "aac-cmp" + (frei ? " aac-frei" : "");
    d.setAttribute("role", "dialog");
    d.setAttribute("aria-modal", frei ? "false" : "true");
    d.setAttribute("aria-labelledby", "aac-cmp-t");
    d.setAttribute("aria-describedby", "aac-cmp-x");
    d.innerHTML = '<div class="aac-box" tabindex="-1">' +
      '<h2 id="aac-cmp-t">' + t.titel + '</h2>' +
      '<p id="aac-cmp-x">' + t.text + '</p>' +
      '<p class="aac-klein">' + t.noetig + '</p>' +
      (erneut && zustand !== null ? '<p class="aac-klein"><b>' + (zustand ? t.stand_ja : t.stand_nein) + '</b></p>' : '') +
      '<div class="aac-knoepfe"><button type="button" data-wahl="nein">' + t.nein + '</button><button type="button" data-wahl="ja">' + t.ja + '</button></div>' +
      '<div class="aac-links"><a href="' + BASIS + 'datenschutz.html#' + t.anker + '">' + t.datenschutz + '</a> · <a href="' + BASIS + 'impressum.html">' + t.impressum + '</a></div>' +
      '</div>';
    d.addEventListener("click", function (e) {
      var b = e.target.closest && e.target.closest("button[data-wahl]");
      if (b) entscheiden(b.getAttribute("data-wahl") === "ja");
    });
    d.addEventListener("keydown", tastatur);
    d.erneut = !!erneut;
    document.body.appendChild(d);
    fenster = d;
    var box = d.querySelector(".aac-box");
    try { box.focus({ preventScroll: true }); } catch (e) { box.focus(); }
  }
  function schliessen(still) {
    if (!fenster) return;
    if (fenster.parentNode) fenster.parentNode.removeChild(fenster);
    fenster = null;
    if (still) return;
    var f = vorherFokus; vorherFokus = null;
    if (f && f.focus && document.documentElement.contains(f)) { try { f.focus({ preventScroll: true }); } catch (e) {} }
  }
  function tastatur(e) {
    if (!fenster) return;
    if (e.key === "Escape" && fenster.erneut && zustand !== null) { e.preventDefault(); schliessen(); return; }   // nur beim erneuten Öffnen
    if (e.key !== "Tab" || fenster.classList.contains("aac-frei")) return;
    var f = fenster.querySelectorAll("button,a[href]");
    if (!f.length) return;
    var erstes = f[0], letztes = f[f.length - 1], akt = document.activeElement;
    if (e.shiftKey && (akt === erstes || akt === fenster.querySelector(".aac-box"))) { e.preventDefault(); letztes.focus(); }
    else if (!e.shiftKey && akt === letztes) { e.preventDefault(); erstes.focus(); }
  }
  function entscheiden(ja) {
    zustand = ja;
    merken(ja);
    if (ja) laden();
    schliessen();
    status();
  }

  /* ---------------- „Cookie-Einstellungen“ in jeder Fußzeile ---------------- */
  function fussLinks() {
    var t = T();
    document.querySelectorAll(".legal").forEach(function (l) {
      var n = l.querySelector("a[data-nutzung]");
      if (!n) {
        n = document.createElement("a"); n.setAttribute("data-nutzung", "");
        var im = l.querySelector('a[href$="impressum.html"]');
        n.href = im ? im.getAttribute("href").replace("impressum.html", "nutzungsbedingungen.html") : "nutzungsbedingungen.html";
        var ds = l.querySelector('a[href$="datenschutz.html"]');
        if (ds && ds.nextSibling) l.insertBefore(n, ds.nextSibling); else l.appendChild(n);
      }
      if (n.textContent !== t.nutzung) n.textContent = t.nutzung;
      var a = l.querySelector("a[data-cookie-einstellungen]");
      if (!a) { a = document.createElement("a"); a.href = "#"; a.setAttribute("data-cookie-einstellungen", ""); l.appendChild(a); }
      if (a.textContent !== t.einstellungen) a.textContent = t.einstellungen;
    });
    document.querySelectorAll("[data-cookie-knopf],[data-cookie-zeile]").forEach(function (b) { if (b.hidden) b.hidden = false; });
    status();
  }
  function status() {
    var t = T();
    var x = zustand === true ? t.stand_ja : zustand === false ? t.stand_nein : t.stand_offen;
    document.querySelectorAll("[data-cookie-status]").forEach(function (el) { if (el.textContent !== x) el.textContent = x; });
  }

  /* ---------------- Start ---------------- */
  function start() {
    if (!AKTIV) return;   // ohne Website-ID: nichts anzeigen, nichts laden
    zustand = lesen();
    document.addEventListener("click", klick, true);
    document.addEventListener("auxclick", function (e) { if (e.button === 1) klick(e); }, true);
    document.addEventListener("change", aenderung, true);
    document.addEventListener("click", function (e) {
      var a = e.target && e.target.closest && e.target.closest("[data-cookie-einstellungen],[data-cookie-knopf]");
      if (a) { e.preventDefault(); oeffnen(true); }
    });
    fussLinks();
    var letzte = sprache();
    if (window.MutationObserver) new MutationObserver(function () {   // Sprache auf der Seite umgeschaltet
      var l = sprache(); if (l === letzte) return; letzte = l;
      fussLinks();
      if (fenster) oeffnen(fenster.erneut);
    }).observe(document.documentElement, { attributes: true, attributeFilter: ["lang"] });
    var geplant = false;
    if (window.MutationObserver) new MutationObserver(function () {
      if (geplant) return; geplant = true;
      setTimeout(function () { geplant = false; fussLinks(); }, 60);
    }).observe(document.body, { childList: true, subtree: true });
    if (zustand === true) laden();
    else if (zustand === null) oeffnen(false);
  }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", start); else start();
})();
