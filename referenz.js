/* Referenzpreis und Kennzeichnung „weit unter Referenzpreis“ – gemeinsam für alle Seiten.
   Dieselben Regeln stehen in build_pages.py (Abschnitt „Referenzpreis“) und auf methodik.html.

   - Nur Textangebote mit Preis (keine Bild/Video-Modelle, keine Gratis-Angebote).
   - Verglichen wird ein gemischter Preis: 3 Teile Input + 1 Teil Output (Pauschalpreis = beides).
   - Geschlossene Modelle (GPT, Claude, Gemini, Grok …): Referenz = OpenRouter
     (entspricht bei diesen Modellen in der Regel dem Listenpreis des Herstellers),
     sonst Median aller Anbieter (ab 3 Angeboten). Gekennzeichnet: mehr als 50 % darunter.
   - Offene Modelle (DeepSeek, Qwen, Llama …): Referenz = Median aller Anbieter (ab 3 Angeboten),
     sonst OpenRouter. Gekennzeichnet: mehr als 80 % darunter – nur wenn die Referenz mindestens
     $0.20 pro 1 Mio. Token beträgt (bei sehr kleinen, billigen Modellen sind große Abstände normal).
   - Varianten geschlossener Modelle ohne eigene Referenz (z. B. „…-uncensored“, „…-thinking“)
     werden mit dem Referenzpreis des Grundmodells verglichen.
   - Anbieter, deren letzter Abruf fehlgeschlagen ist (meta.veraltet), werden mit Datum gezeigt;
     sind die Daten älter als 3 Tage, zählen sie nicht für Empfehlungen. */
(function(){
  "use strict";
  var D = window.API_DATEN || {};
  var GESCHLOSSEN = /^(claude|gpt-(?!oss)|chatgpt|o[1-9](-|$)|gemini|grok|nova-|sonar)/;
  var GRENZE_GESCHLOSSEN = 0.5, GRENZE_OFFEN = 0.2, MIN_REF_OFFEN = 0.2, ALT_TAGE = 3;
  var VARIANTE = /-(uncensored|thinking|fast|highspeed|nitro)$/;   // Varianten geschlossener Modelle → Grundmodell

  function zahl(x){ return typeof x === "number" && isFinite(x); }
  function misch(v){
    if (zahl(v.in) && zahl(v.out)) return (3 * v.in + v.out) / 4;
    if (zahl(v.in)) return v.in;
    if (zahl(v.price)) return v.price;
    return null;
  }
  function textAngebot(k, v){
    return !/^media-/.test(k) && !v.gratis && !v.media && (zahl(v.in) || zahl(v.price)) && misch(v) > 0;
  }
  function median(a){
    a = a.slice().sort(function(x, y){ return x - y; });
    var n = a.length, h = Math.floor(n / 2);
    return n % 2 ? a[h] : (a[h - 1] + a[h]) / 2;
  }

  var proBasis = {};
  Object.keys(D).sort().forEach(function(q){
    if (q === "meta" || !D[q] || typeof D[q] !== "object") return;
    Object.keys(D[q]).forEach(function(k){
      var v = D[q][k];
      if (!v || !textAngebot(k, v)) return;
      var b = k.replace(/:free$/, "");
      (proBasis[b] = proBasis[b] || []).push({q:q, k:k, v:v, m:misch(v)});
    });
  });

  var REF = {}, ERG = {}, EIGEN = {};
  // 1. eigene Referenz je Modell
  Object.keys(proBasis).forEach(function(b){
    var l = proBasis[b], zu = GESCHLOSSEN.test(b), or = null;
    l.forEach(function(x){ if (x.q === "openrouter" && (!or || x.m < or.m)) or = x; });
    var orRef = or ? {inp: zahl(or.v.in) ? or.v.in : null, out: zahl(or.v.out) ? or.v.out : null, m: or.m, src: "openrouter"} : null;
    var medRef = l.length >= 3 ? {inp: null, out: null, m: median(l.map(function(x){ return x.m; })), src: "median"} : null;
    var r = zu ? (orRef || medRef) : (medRef || orRef);
    if (!r || !(r.m > 0)) return;
    r.geschlossen = zu; r.via = "";
    EIGEN[b] = r;
  });
  // 2. Varianten geschlossener Modelle ohne eigene Referenz → Referenz des Grundmodells
  Object.keys(proBasis).forEach(function(b){
    if (EIGEN[b]) { REF[b] = EIGEN[b]; return; }
    var x = b;
    while (VARIANTE.test(x)) {
      x = x.replace(VARIANTE, "");
      var g = EIGEN[x];
      if (g && g.geschlossen) { REF[b] = {inp: g.inp, out: g.out, m: g.m, src: g.src, geschlossen: true, via: x}; break; }
    }
  });
  // 3. Abweichung je Angebot
  Object.keys(proBasis).forEach(function(b){
    var r = REF[b], l = proBasis[b];
    if (!r) return;
    var zu = r.geschlossen;
    var grenze = zu ? GRENZE_GESCHLOSSEN : (r.m >= MIN_REF_OFFEN ? GRENZE_OFFEN : 0);
    l.forEach(function(x){
      var v = x.v, ratio;
      if (r.src === "openrouter" && zahl(v.in) && zahl(v.out) && r.inp !== null && r.out !== null) ratio = x.m / r.m;
      else if (r.src === "openrouter" && zahl(v.in) && !zahl(v.out) && r.inp !== null) ratio = v.in / r.inp;
      else ratio = x.m / r.m;
      if (!(ratio > 0) || !isFinite(ratio)) return;
      ERG[x.q + "|" + x.k] = {ratio: ratio, pct: Math.round((1 - ratio) * 100), auff: ratio < grenze, src: r.src};
    });
  });

  var meta = D.meta || {}, stand = Date.parse(String(meta.erstellt || "").slice(0, 10)), ALT = {};
  Object.keys(meta.veraltet || {}).forEach(function(q){
    var seit = String(meta.veraltet[q] || "").slice(0, 10), t = Date.parse(seit);
    var tage = (isFinite(stand) && isFinite(t)) ? Math.round((stand - t) / 864e5) : 0;
    ALT[q] = {seit: seit, tage: tage, zuAlt: tage > ALT_TAGE};
  });

  function fmt(n){ return "$" + (n >= 100 ? n.toFixed(0) : n >= 1 ? n.toFixed(2) : n >= 0.01 ? n.toFixed(3) : n.toFixed(4)); }
  function datum(d, lang){
    var m = /^(\d{4})-(\d\d)-(\d\d)/.exec(d || "");
    if (!m) return d || "";
    return (lang === "de" || lang === "ru") ? m[3] + "." + m[2] + "." + m[1] : m[1] + "-" + m[2] + "-" + m[3];
  }
  function refPreis(r, t){
    return r.inp !== null && r.out !== null ? fmt(r.inp) + " / " + fmt(r.out) + " " + t.pro_io : fmt(r.m) + " " + t.pro_misch;
  }

  var TXT = {
    de: {tag: function(p){ return "⚠ " + p + " % unter Referenz"; },
      titel: function(p, ref){ return "Dieser Preis liegt " + p + " % unter dem Referenzpreis (" + ref + "). Wir können nicht nachvollziehen, wie er zustande kommt, und nicht prüfen, welches Modell tatsächlich geliefert wird. Vorher Bedingungen, Datenschutz und Zuverlässigkeit prüfen und mit kleinem Guthaben testen."; },
      alt_tag: function(d){ return "⏱ Stand " + d; },
      alt_titel: function(d){ return "Der letzte Abruf bei diesem Anbieter ist fehlgeschlagen – angezeigt werden die Preise vom " + d + "."; },
      batch_titel: "Batch-Variante: in der Regel günstiger, Anfragen werden aber gesammelt und verzögert verarbeitet – meist nicht für Chat oder Echtzeit geeignet.",
      ref: "Referenzpreis", pro_io: "pro 1 Mio. Token (Input / Output)", pro_misch: "pro 1 Mio. Token (gemischt 3:1)",
      src: {openrouter: "OpenRouter", openrouter_zu: "OpenRouter – bei diesem Modell in der Regel der Listenpreis des Herstellers", median: "Median aller Anbieter"}, via: "Grundmodell",
      trenner: "Weit unter dem Referenzpreis – bitte vorher prüfen", mehr: "So vergleichen wir →"},
    en: {tag: function(p){ return "⚠ " + p + "% below reference"; },
      titel: function(p, ref){ return "This price is " + p + "% below the reference price (" + ref + "). We cannot tell how it is possible or verify which model is actually served. Check terms, privacy and reliability first and test with a small balance."; },
      alt_tag: function(d){ return "⏱ as of " + d; },
      alt_titel: function(d){ return "The last update from this provider failed – prices shown are from " + d + "."; },
      batch_titel: "Batch variant: usually cheaper, but requests are collected and processed with a delay – usually not suitable for chat or real-time use.",
      ref: "Reference price", pro_io: "per 1M tokens (input / output)", pro_misch: "per 1M tokens (blended 3:1)",
      src: {openrouter: "OpenRouter", openrouter_zu: "OpenRouter – for this model usually the vendor's list price", median: "median of all providers"}, via: "base model",
      trenner: "Far below the reference price – please check first", mehr: "How we compare →"},
    zh: {tag: function(p){ return "⚠ 低于参考价 " + p + "%"; },
      titel: function(p, ref){ return "此价格比参考价低 " + p + "%（" + ref + "）。我们无法确认该价格如何实现，也无法核实实际提供的是哪个模型。使用前请先查看条款、隐私政策和可靠性，并先用少量余额测试。"; },
      alt_tag: function(d){ return "⏱ 数据日期 " + d; },
      alt_titel: function(d){ return "该提供商最近一次更新失败——显示的是 " + d + " 的价格。"; },
      batch_titel: "批处理版本：通常更便宜，但请求会被汇总并延迟处理——一般不适合聊天或实时场景。",
      ref: "参考价", pro_io: "每百万 Token（输入 / 输出）", pro_misch: "每百万 Token（按 3:1 混合）",
      src: {openrouter: "OpenRouter", openrouter_zu: "OpenRouter——对该模型通常即厂商官方价格", median: "所有提供商的中位数"}, via: "基础模型",
      trenner: "远低于参考价——使用前请先核实", mehr: "我们的比较方法 →"},
    ru: {tag: function(p){ return "⚠ на " + p + " % ниже эталона"; },
      titel: function(p, ref){ return "Эта цена на " + p + " % ниже эталонной (" + ref + "). Мы не можем объяснить, как она возможна, и проверить, какая модель реально используется. Перед использованием проверьте условия, конфиденциальность и надёжность и протестируйте с небольшим балансом."; },
      alt_tag: function(d){ return "⏱ на " + d; },
      alt_titel: function(d){ return "Последнее обновление у этого поставщика не удалось – показаны цены на " + d + "."; },
      batch_titel: "Пакетный вариант: обычно дешевле, но запросы собираются и обрабатываются с задержкой – как правило, не подходит для чата и работы в реальном времени.",
      ref: "Эталонная цена", pro_io: "за 1 млн токенов (вход / выход)", pro_misch: "за 1 млн токенов (смешанная 3:1)",
      src: {openrouter: "OpenRouter", openrouter_zu: "OpenRouter – для этой модели обычно прайс производителя", median: "медиана всех поставщиков"}, via: "базовая модель",
      trenner: "Намного ниже эталонной цены – проверьте заранее", mehr: "Как мы сравниваем →"}
  };
  function txt(lang){ return TXT[lang] || TXT.en; }
  function refText(basis, lang){
    var r = REF[String(basis).replace(/:free$/, "")], t = txt(lang);
    if (!r) return "";
    var src = r.src === "median" ? t.src.median : (r.geschlossen ? t.src.openrouter_zu : t.src.openrouter);
    return refPreis(r, t) + ", " + src + (r.via ? " (" + t.via + ": " + r.via + ")" : "");
  }

  window.REFERENZ = {
    ref: function(basis){ return REF[String(basis).replace(/:free$/, "")] || null; },
    pruefe: function(q, k){ return ERG[q + "|" + k] || null; },
    alt: function(q){ return ALT[q] || null; },
    /* für Empfehlungen geeignet: nicht weit unter Referenz und Daten nicht älter als 3 Tage */
    ok: function(q, k){ var e = ERG[q + "|" + k], a = ALT[q]; return !(e && e.auff) && !(a && a.zuAlt); },
    batch: function(k, name){ return /:batch$/.test(k || "") || /\(batch\)/i.test(name || ""); },
    txt: txt, datum: datum, refText: refText,
    /* fertige Kennzeichen (HTML) für Tabellen */
    tags: function(q, k, lang, name){
      var t = txt(lang), h = "", e = ERG[q + "|" + k], a = ALT[q], b = String(k).replace(/:free$/, "");
      if (e && e.auff) h += '<span class="tag warn" title="' + esc(t.titel(e.pct, refText(b, lang))) + '">' + esc(t.tag(e.pct)) + '</span>';
      if (a) h += '<span class="tag alt" title="' + esc(t.alt_titel(datum(a.seit, lang))) + '">' + esc(t.alt_tag(datum(a.seit, lang))) + '</span>';
      if (/:batch$/.test(k || "") || /\(batch\)/i.test(name || "")) h += '<span class="tag batch" title="' + esc(t.batch_titel) + '">Batch</span>';
      return h;
    },
    stats: function(){ var n = 0, a = 0; Object.keys(ERG).forEach(function(k){ n++; if (ERG[k].auff) a++; }); return {geprueft: n, auffaellig: a}; }
  };
  function esc(s){ return String(s).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;"); }
})();
