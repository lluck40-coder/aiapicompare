#!/usr/bin/env python3
"""Automatische Kontrolle nach jedem Lauf.

Prüft:
  1. Preisdaten: Anbieter, deren Abruf fehlgeschlagen ist (meta.veraltet), oder die leer sind
  2. Bestenliste / Neuigkeiten / Preisindex: Dateien vorhanden und nicht veraltet
  3. Tote interne Links in der fertigen Website (_site)

Ergebnis:
  - Ausgabe im Protokoll des Laufs
  - Auf GitHub (GITHUB_TOKEN + GITHUB_REPOSITORY gesetzt): ein Issue
    „Automatische Kontrolle: Probleme gefunden“ wird angelegt bzw. aktualisiert
    (Kommentar nur, wenn sich die Probleme geändert haben) und automatisch
    geschlossen, sobald alles wieder in Ordnung ist. GitHub schickt dir dazu eine E-Mail.

Aufruf:  python3 pruefen.py _site
"""
import datetime as dt
import html.parser
import json
import os
import pathlib
import re
import sys
import urllib.parse
import urllib.request

SITE = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else "_site")
OUT = pathlib.Path("out")
TITEL = "Automatische Kontrolle: Probleme gefunden"
MARKE = "<!-- aiapicompare-kontrolle -->"
heute = dt.datetime.now(dt.timezone.utc).date()


def js_json(pfad):
    s = pfad.read_text(encoding="utf-8")
    return json.loads(s[s.index("{"):s.rindex("}") + 1])


def alter_tage(datum):
    try:
        return (heute - dt.date.fromisoformat(str(datum)[:10])).days
    except ValueError:
        return None


probleme = []      # (Bereich, Text)
hinweise = []

# ---------- 1. Preisdaten ----------
try:
    daten = js_json(OUT / "data.js")
    meta = daten.get("meta") or {}
    for q, seit in sorted((meta.get("veraltet") or {}).items()):
        probleme.append(("Preise", f"Abruf von **{q}** schlägt fehl – es werden die Daten vom {seit} angezeigt."))
    for q, v in daten.items():
        if q != "meta" and isinstance(v, dict) and not v:
            probleme.append(("Preise", f"Anbieter **{q}** liefert keine Modelle."))
    a = alter_tage(meta.get("erstellt", ""))
    if a is not None and a > 2:
        probleme.append(("Preise", f"Die Preisdaten sind {a} Tage alt (Stand {meta.get('erstellt')})."))
    hinweise.append(f"Preisdaten: {sum(len(v) for k, v in daten.items() if k != 'meta' and isinstance(v, dict))} Einträge, Stand {meta.get('erstellt')}")
except Exception as e:  # noqa: BLE001
    probleme.append(("Preise", f"out/data.js konnte nicht gelesen werden: {e}"))

# ---------- 2. Bestenliste, Neuigkeiten, Preisindex ----------
for datei, name, feld in [("staerken.js", "Bestenliste (Arena)", ("meta", "abgerufen")),
                          ("news.js", "Neuigkeiten", ("stand",)),
                          ("preisindex.js", "Preisindex", ("stand",))]:
    p = OUT / datei
    if not p.exists():
        probleme.append(("Daten", f"{name}: out/{datei} fehlt."))
        continue
    try:
        j = js_json(p)
        for f in feld:
            j = j.get(f, {}) if isinstance(j, dict) else {}
        a = alter_tage(j) if isinstance(j, str) else None
        if a is not None and a > 3:
            probleme.append(("Daten", f"{name} ist {a} Tage alt – der Abruf in build_news.py schlägt vermutlich fehl."))
    except Exception as e:  # noqa: BLE001
        probleme.append(("Daten", f"{name}: out/{datei} ist beschädigt ({e})."))

# ---------- 2b. Von Hand gepflegte Anbieter-Angaben ----------
try:
    _fakten = json.loads(pathlib.Path("anbieter_info.json").read_text(encoding="utf-8"))
    a = alter_tage(_fakten.get("stand", ""))
    if a is not None and a > 120:
        probleme.append(("Anbieter", f"Die Anbieter-Angaben (anbieter_info.json, Stand {_fakten.get('stand')}) sind {a} Tage alt – bitte Zahlungsarten, Mindestaufladung und Datenschutz bei den Anbietern nachprüfen."))
except FileNotFoundError:
    pass
except Exception as e:  # noqa: BLE001
    probleme.append(("Anbieter", f"anbieter_info.json ist beschädigt ({e})."))

# ---------- 3. Tote interne Links ----------
class Links(html.parser.HTMLParser):
    def __init__(self):
        super().__init__()
        self.links = []

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        for k in ("href", "src"):
            if a.get(k) and tag in ("a", "link", "script", "img", "iframe", "source"):
                if tag == "link" and a.get("rel") in ("canonical", "alternate") and k == "href":
                    continue   # absolute Adressen auf die Domain
                self.links.append(a[k])


tote = {}
if SITE.is_dir():
    dateien = sorted(SITE.rglob("*.html"))
    vorhanden = {str(p.relative_to(SITE)).replace(os.sep, "/") for p in SITE.rglob("*") if p.is_file()}
    for p in dateien:
        rel = str(p.relative_to(SITE)).replace(os.sep, "/")
        if rel == "404.html":
            ordner = ""          # 404 wird unter beliebigen Adressen ausgeliefert – nutzt absolute Pfade
        else:
            ordner = rel.rsplit("/", 1)[0] + "/" if "/" in rel else ""
        par = Links()
        try:
            par.feed(p.read_text(encoding="utf-8", errors="replace"))
        except Exception:  # noqa: BLE001
            continue
        for l in par.links:
            u = urllib.parse.urlsplit(l)
            if u.scheme or l.startswith(("//", "#", "mailto:", "tel:", "javascript:", "data:")):
                continue
            if "'" in l or "+" in l and "(" in l:
                continue          # in JavaScript zusammengesetzte Adressen
            pfad = urllib.parse.unquote(u.path)
            if not pfad:
                continue
            ziel = pfad.lstrip("/") if pfad.startswith("/") else os.path.normpath(ordner + pfad).replace(os.sep, "/")
            if ziel.endswith("/") or ziel in ("", "."):
                ziel = (ziel.rstrip("/") + "/index.html").lstrip("/")
            if ziel not in vorhanden:
                tote.setdefault(ziel, set()).add(rel)
    hinweise.append(f"Linkprüfung: {len(dateien)} Seiten geprüft, {len(tote)} tote Ziele")
    for ziel, von in sorted(tote.items())[:40]:
        bsp = sorted(von)[:3]
        probleme.append(("Links", f"`{ziel}` fehlt – verlinkt von {', '.join('`'+b+'`' for b in bsp)}{' u. a.' if len(von) > 3 else ''}"))
    if len(tote) > 40:
        probleme.append(("Links", f"… und {len(tote) - 40} weitere tote Ziele."))
else:
    hinweise.append(f"Linkprüfung übersprungen ({SITE} nicht gefunden)")

# ---------- Ausgabe ----------
for h in hinweise:
    print("ℹ", h)
if probleme:
    print(f"\n⚠ {len(probleme)} Probleme:")
    for b, t in probleme:
        print(f"  [{b}] {t}")
else:
    print("\n✓ Alles in Ordnung.")

# ---------- GitHub-Issue ----------
TOKEN = os.environ.get("GITHUB_TOKEN")
REPO = os.environ.get("GITHUB_REPOSITORY")
if not (TOKEN and REPO):
    sys.exit(0)

def api(methode, pfad, daten=None):
    req = urllib.request.Request("https://api.github.com/repos/" + REPO + pfad, method=methode,
                                 data=json.dumps(daten).encode() if daten is not None else None,
                                 headers={"Authorization": "Bearer " + TOKEN, "Accept": "application/vnd.github+json",
                                          "X-GitHub-Api-Version": "2022-11-28", "User-Agent": "aiapicompare-kontrolle"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read() or b"null")

try:
    offen = [i for i in api("GET", "/issues?state=open&per_page=50") if MARKE in (i.get("body") or "") and "pull_request" not in i]
    lauf = os.environ.get("GITHUB_SERVER_URL", "https://github.com") + "/" + REPO + "/actions/runs/" + os.environ.get("GITHUB_RUN_ID", "")
    if probleme:
        liste = "\n".join(f"- **{b}:** {t}" for b, t in probleme)
        text = (f"{MARKE}\nDie tägliche Kontrolle vom {heute} hat Folgendes gefunden:\n\n{liste}\n\n"
                f"Die Website läuft weiter – betroffene Anbieter zeigen die letzten funktionierenden Daten.\n\n"
                f"[Protokoll des Laufs]({lauf})\n\n_Dieses Issue wird automatisch geschlossen, sobald alles wieder in Ordnung ist._")
        if offen:
            nr = offen[0]["number"]
            alt = offen[0].get("body") or ""
            if alt.split("\n\nDie Website")[0].split(":\n\n", 1)[-1] != liste:
                api("PATCH", f"/issues/{nr}", {"body": text})
                api("POST", f"/issues/{nr}/comments", {"body": f"Stand {heute}: Die Probleme haben sich geändert.\n\n{liste}"})
                print(f"Issue #{nr} aktualisiert.")
            else:
                print(f"Issue #{nr} unverändert.")
        else:
            nr = api("POST", "/issues", {"title": TITEL, "body": text})["number"]
            print(f"Issue #{nr} angelegt.")
    else:
        for i in offen:
            api("POST", f"/issues/{i['number']}/comments", {"body": f"Stand {heute}: Alles wieder in Ordnung – Issue wird geschlossen."})
            api("PATCH", f"/issues/{i['number']}", {"state": "closed", "state_reason": "completed"})
            print(f"Issue #{i['number']} geschlossen.")
except Exception as e:  # noqa: BLE001
    print("GitHub-Issue konnte nicht bearbeitet werden:", e)
