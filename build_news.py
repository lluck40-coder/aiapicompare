#!/usr/bin/env python3
"""
Erzeugt zwei Datendateien für die Website (nur Python-Standardbibliothek):

  out/staerken.js – "Welches Modell wofür?": Ranglisten der Arena (arena.ai, ehemals LMArena)
                    je Anwendungsbereich, den eigenen Preisdaten zugeordnet.
                    Quelle: Datensatz "lmarena-ai/leaderboard-dataset" auf Hugging Face,
                    Lizenz CC BY 4.0 (https://creativecommons.org/licenses/by/4.0/).
                    Übernommen werden nur Name, Entwickler, Punktzahl und Stimmenzahl.
  out/news.js     – Neuigkeiten aus den EIGENEN Preisdaten: neue Modelle und Preisänderungen
                    der letzten 30 Tage (aus out/data.js und out/verlauf.json).
                    Es werden bewusst keine fremden Schlagzeilen oder Artikeltexte übernommen.

Schlägt der Abruf der Ranglisten fehl, bleibt die vorhandene out/staerken.js unverändert.
Aufruf:  python3 build_news.py
"""
import datetime
import json
import re
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

BASIS = Path(__file__).resolve().parent
OUT = BASIS / "out"
UA = "aiapicompare.com (https://aiapicompare.com) price-comparison bot"
HF_FILTER = "https://datasets-server.huggingface.co/filter"
HF_ROWS = "https://datasets-server.huggingface.co/rows"
DATENSATZ = "lmarena-ai/leaderboard-dataset"
ANZAHL = 50          # je Bereich übernommene Plätze

# (Schlüssel, Teil-Datensatz, Kategorie, Art der Preise)
BEREICHE = [
    ("allround",    "text_style_control",   "overall",               "text"),
    ("coding",      "text_style_control",   "coding",                "text"),
    ("webdev",      "webdev",               "overall",               "text"),
    ("math",        "text_style_control",   "math",                  "text"),
    ("creative",    "text_style_control",   "creative_writing",      "text"),
    ("anweisungen", "text_style_control",   "instruction_following", "text"),
    ("schwer",      "text_style_control",   "hard_prompts",          "text"),
    ("deutsch",     "text_style_control",   "german",                "text"),
    ("englisch",    "text_style_control",   "english",               "text"),
    ("chinesisch",  "text_style_control",   "chinese",               "text"),
    ("russisch",    "text_style_control",   "russian",               "text"),
    ("vision",      "vision_style_control", "overall",               "text"),
    ("bild",        "text_to_image",        "overall",               "bild"),
    ("bildedit",    "image_edit",           "overall",               "bild"),
    ("video",       "text_to_video",        "overall",               "video"),
    ("bildvideo",   "image_to_video",       "overall",               "video"),
]


def hole_json(url, versuche=4):
    for i in range(versuche):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/json"})
            with urllib.request.urlopen(req, timeout=60) as r:
                return json.loads(r.read().decode("utf-8"))
        except Exception as e:
            if i == versuche - 1:
                raise
            print(f"  (Wiederholung {i + 1}: {e})", flush=True)
            time.sleep(3 * (i + 1))


def lade_bereich(config, kategorie):
    """Beste Plätze eines Bereichs (aktuelle Veröffentlichung), sortiert nach Rang."""
    q = {"dataset": DATENSATZ, "config": config, "split": "latest",
         "where": f"\"category\"='{kategorie}'", "orderby": "\"rank\"", "offset": 0, "length": ANZAHL + 30}
    d = hole_json(HF_FILTER + "?" + urllib.parse.urlencode(q))
    zeilen = [r["row"] for r in d.get("rows", [])]
    if not zeilen and kategorie == "overall":          # manche Bereiche haben nur eine Kategorie
        q.pop("where")
        d = hole_json(HF_FILTER + "?" + urllib.parse.urlencode(q))
        zeilen = [r["row"] for r in d.get("rows", [])]
    return zeilen


# ------------------------------------------------------------------ eigene Daten laden
def lade_preisdaten():
    t = (OUT / "data.js").read_text(encoding="utf-8")
    return json.loads(t[t.index("{"):t.rstrip().rstrip(";").rindex("}") + 1])


def norm(name):
    """Vergleichbare Schreibweise: Klammerzusätze (z. B. "(High)") weg, nur a–z/0–9 und Bindestriche."""
    s = re.sub(r"\([^)]*\)", " ", str(name or "")).lower()
    return re.sub(r"[^a-z0-9]+", "-", s).strip("-")


# Zusätze, die dasselbe Modell bezeichnen (Vorschau, Datum, "-it" usw.) – bewusst eng gehalten
ZUSATZ = re.compile(r"^(-(preview|latest|exp|experimental|instruct|it|chat|\d{2,8}))+$")


def zuordnung(daten):
    """norm(Modellname) -> Liste eigener Modell-Schlüssel (wie im Preisvergleich, ":free" zusammengefasst)."""
    nach_norm = {}
    for q, eintraege in daten.items():
        if q == "meta" or not isinstance(eintraege, dict):
            continue
        for k in eintraege:
            basis = re.sub(r":free$", "", k)
            if ":" in basis:              # z. B. ":batch", ":thinking" – eigene Varianten, nicht zuordnen
                continue
            n = norm(basis[6:] if basis.startswith("media-") else basis)
            nach_norm.setdefault(n, set()).add(basis)
    return nach_norm


def finde(n, nach_norm, art):
    treffer = set(nach_norm.get(n, set()))
    for m, schluessel in nach_norm.items():
        if m != n and ((m.startswith(n + "-") and ZUSATZ.match(m[len(n):])) or
                       (n.startswith(m + "-") and ZUSATZ.match(n[len(m):]))):
            treffer |= schluessel
    # Bild-/Video-Platzierungen nur echten Bild-/Video-Angeboten zuordnen, Text-Platzierungen nur Text-Angeboten
    medien = art in ("bild", "video")
    return sorted(k for k in treffer if k.startswith("media-") == medien)


def baue_staerken(daten):
    nach_norm = zuordnung(daten)
    bereiche, stand = {}, ""
    for key, config, kategorie, art in BEREICHE:
        try:
            zeilen = lade_bereich(config, kategorie)
        except Exception as e:
            print(f"  (!) {key}: nicht abrufbar ({e})", flush=True)
            continue
        liste, gesehen = [], set()
        for z in zeilen:                      # Varianten mit anderem Denkaufwand zusammenfassen (beste zählt)
            n = norm(z.get("model_name"))
            if not n or n in gesehen:
                continue
            gesehen.add(n)
            stand = max(stand, str(z.get("leaderboard_publish_date") or "")[:10])
            wert = z.get("rating") if z.get("rating") is not None else z.get("score")
            liste.append({"p": len(liste) + 1, "n": z.get("model_name"), "o": z.get("organization") or "",
                          "r": round(float(wert)) if wert is not None else None,
                          "v": int(z.get("vote_count") or z.get("observation_count") or 0),
                          "k": finde(n, nach_norm, art)})
            if len(liste) >= ANZAHL:
                break
        if liste:
            bereiche[key] = {"art": art, "liste": liste}
            print(f"  {key}: {len(liste)} Plätze, {sum(1 for x in liste if x['k'])} mit Preisen", flush=True)
        time.sleep(0.5)
    modelle = {}
    for key, b in bereiche.items():
        for x in b["liste"]:
            for k in x["k"]:
                modelle.setdefault(k, {})
                if key not in modelle[k] or x["p"] < modelle[k][key]:
                    modelle[k][key] = x["p"]
    return {"meta": {"stand": stand, "abgerufen": time.strftime("%Y-%m-%d", time.gmtime()),
                     "quelle": "Arena (arena.ai, ehemals LMArena)",
                     "datensatz": "https://huggingface.co/datasets/" + DATENSATZ,
                     "lizenz": "CC BY 4.0", "lizenz_url": "https://creativecommons.org/licenses/by/4.0/"},
            "bereiche": bereiche, "modelle": modelle}


# ------------------------------------------------------------------ Neuigkeiten aus eigenen Daten
def baue_news(daten):
    try:
        verlauf = json.loads((OUT / "verlauf.json").read_text(encoding="utf-8"))
    except Exception:
        verlauf = {}
    grenze = (datetime.date.today() - datetime.timedelta(days=30)).isoformat()
    neu, preis = [], []
    for q, eintraege in daten.items():
        if q == "meta" or not isinstance(eintraege, dict):
            continue
        for k, v in eintraege.items():
            name = v.get("name") or v.get("roh_id") or k
            basis = re.sub(r":free$", "", k)
            h = verlauf.get(q + "|" + k) or {}
            if v.get("seit") and v["seit"] >= grenze:
                neu.append({"d": v["seit"], "q": q, "k": basis, "n": name,
                            "in": v.get("in"), "out": v.get("out"), "ab": v.get("price"),
                            "mp": v.get("media_preis"), "e": v.get("einheit") or "", "g": bool(v.get("gratis"))})
            p = h.get("p") or []
            if len(p) > 1 and p[-1][0] >= grenze and p[-2][1] and p[-1][1] != p[-2][1]:
                alt, jetzt = p[-2][1], p[-1][1]
                # Einheit nur bei Medienpreisen (der Verlauf speichert sonst den Input-Preis pro 1 Mio. Token)
                text = isinstance(v.get("in"), (int, float)) or isinstance(v.get("price"), (int, float))
                preis.append({"d": p[-1][0], "q": q, "k": basis, "n": name, "alt": alt, "neu": jetzt,
                              "pz": round((jetzt / alt - 1) * 100) if alt else None,
                              "e": "" if text else (v.get("einheit") or "")})
    neu.sort(key=lambda x: (x["d"], x["n"]), reverse=True)
    preis.sort(key=lambda x: (x["d"], abs(x["pz"] or 0)), reverse=True)
    return {"stand": (daten.get("meta") or {}).get("erstellt", ""), "neu": neu[:150], "preis": preis[:150]}


# ------------------------------------------------------------------ KI-Preisindex aus dem eigenen Preisverlauf
def baue_preisindex(daten, staerken):
    """Index = 100 × geometrisches Mittel (Preis am Tag / Preis am Starttag) über einen festen Warenkorb:
    alle Textmodelle (Input-Preis > 0), die seit dem Starttag erfasst sind. Zweite Reihe: nur die
    Top 30 der Arena-Bestenliste (Allround). Dazu Monatswerte: Preissenkungen, -erhöhungen, neue Modelle."""
    import math
    try:
        verlauf = json.loads((OUT / "verlauf.json").read_text(encoding="utf-8"))
    except Exception:
        return None
    text = {}
    for q, eintraege in daten.items():
        if q == "meta" or not isinstance(eintraege, dict):
            continue
        for k, v in eintraege.items():
            if isinstance(v.get("in"), (int, float)) or isinstance(v.get("price"), (int, float)):
                text[q + "|" + k] = re.sub(r":free$", "", k)
    reihen = {key: h["p"] for key, h in verlauf.items() if key != "_quellen" and isinstance(h, dict) and h.get("p") and key in text}
    if not reihen:
        return None
    start = min(p[0][0] for p in reihen.values())
    heute = time.strftime("%Y-%m-%d", time.gmtime())
    korb = {key: p for key, p in reihen.items() if p[0][0] == start and p[0][1] and p[0][1] > 0}
    top = {k for k, b in ((staerken or {}).get("modelle") or {}).items() if b.get("allround") and b["allround"] <= 30}
    korb_top = {key: p for key, p in korb.items() if text[key] in top}
    tage = sorted({d for p in korb.values() for d, _ in p} | {heute})

    def preis_am(p, tag):
        wert = None
        for d, x in p:
            if d <= tag:
                wert = x
            else:
                break
        return wert

    def index(k, tag):
        logs = []
        for p in k.values():
            x = preis_am(p, tag)
            if x and x > 0:
                logs.append(math.log(x / p[0][1]))
        return round(100 * math.exp(sum(logs) / len(logs)), 2) if logs else None

    punkte = [[tag, index(korb, tag), index(korb_top, tag) if korb_top else None] for tag in tage]
    monate = {}
    for key, h in verlauf.items():
        if key == "_quellen" or not isinstance(h, dict):
            continue
        p = h.get("p") or []
        for (d0, a), (d1, b) in zip(p, p[1:]):
            m = monate.setdefault(d1[:7], {"runter": 0, "hoch": 0, "neu": 0})
            if a and b and b < a:
                m["runter"] += 1
            elif a and b and b > a:
                m["hoch"] += 1
        if h.get("seit"):
            monate.setdefault(h["seit"][:7], {"runter": 0, "hoch": 0, "neu": 0})["neu"] += 1
    return {"start": start, "stand": heute, "n_alle": len(korb), "n_top": len(korb_top), "punkte": punkte,
            "monate": [dict(m=k, **v) for k, v in sorted(monate.items(), reverse=True)]}


def schreibe_js(pfad, variable, obj):
    pfad.write_text(f"window.{variable} = " + json.dumps(obj, ensure_ascii=False, separators=(",", ":")) + ";\n",
                    encoding="utf-8")


def main():
    daten = lade_preisdaten()
    print("Ranglisten (Arena, CC BY 4.0) abrufen …", flush=True)
    try:
        st = baue_staerken(daten)
        if st["bereiche"]:
            schreibe_js(OUT / "staerken.js", "STAERKEN", st)
            print(f"out/staerken.js: {len(st['bereiche'])} Bereiche, Stand {st['meta']['stand']}")
        else:
            print("(!) Keine Ranglisten erhalten – vorhandene out/staerken.js bleibt bestehen")
    except Exception as e:
        print(f"(!) Ranglisten fehlgeschlagen: {e} – vorhandene Datei bleibt bestehen")
    try:
        st_daten = json.loads((OUT / "staerken.js").read_text(encoding="utf-8").split("=", 1)[1].rstrip().rstrip(";"))
    except Exception:
        st_daten = {}
    pi = baue_preisindex(daten, st_daten)
    if pi:
        schreibe_js(OUT / "preisindex.js", "PREISINDEX", pi)
        print(f"out/preisindex.js: Start {pi['start']}, Warenkorb {pi['n_alle']} Modelle (Top: {pi['n_top']}), {len(pi['punkte'])} Datenpunkte")
    nw = baue_news(daten)
    schreibe_js(OUT / "news.js", "NEWS", nw)
    print(f"out/news.js: {len(nw['neu'])} neue Modelle, {len(nw['preis'])} Preisänderungen (30 Tage)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
