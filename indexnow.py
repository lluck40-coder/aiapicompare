#!/usr/bin/env python3
"""
Meldet neue und geänderte Seiten per IndexNow an Suchmaschinen (u. a. Bing, Yandex, Seznam, Naver).
Läuft im GitHub-Workflow NACH der Veröffentlichung.

- Schlüssel: Datei <32 Hex-Zeichen>.txt im Projektordner (wird mit veröffentlicht).
- Gemeldet wird nur, wenn die Domain schon live ist (Schlüsseldatei unter https://aiapicompare.com/ abrufbar).
- Täglich: Startseiten, Bestenliste, Neuigkeiten, Vergleiche und die Modellseiten mit Preisänderungen/neuen Modellen.
  Montags zusätzlich alle Adressen aus der Sitemap (höchstens 10.000).
Nur Python-Standardbibliothek.  Aufruf: python3 indexnow.py [Ordner der fertigen Website, Standard _site]
"""
import json
import re
import sys
import time
import urllib.request
from pathlib import Path

BASIS = Path(__file__).resolve().parent
SITE = Path(sys.argv[1] if len(sys.argv) > 1 else "_site").resolve()
HOST = "aiapicompare.com"
DOMAIN = f"https://{HOST}/"
ENDPUNKT = "https://api.indexnow.org/indexnow"
SPRACHEN = ["", "de/", "zh/", "ru/"]


def schluessel():
    for f in BASIS.glob("*.txt"):
        if re.fullmatch(r"[0-9a-f]{32}\.txt", f.name):
            return f.stem
    return None


def live(key):
    try:
        req = urllib.request.Request(DOMAIN + key + ".txt", headers={"User-Agent": "aiapicompare-indexnow"})
        with urllib.request.urlopen(req, timeout=20) as r:
            return r.read().decode("utf-8", "replace").strip() == key
    except Exception as e:
        print(f"Domain noch nicht erreichbar ({e})")
        return False


def slug(k):
    s = re.sub(r":free$", "", str(k))
    s = re.sub(r"^media-", "", s).lower()
    return re.sub(r"-+", "-", re.sub(r"[^a-z0-9-]+", "-", s)).strip("-")


def adressen():
    urls = [DOMAIN, DOMAIN + "bestenliste.html", DOMAIN + "news.html", DOMAIN + "kosten.html", DOMAIN + "llms.txt"]
    for sp in SPRACHEN:
        for rest in ("free.html", "models/index.html", "compare/index.html", "feed.xml"):
            if (SITE / (sp + rest)).exists():
                urls.append(DOMAIN + sp + rest)
    # Modellseiten mit Neuigkeiten (Preisänderung, neues Modell)
    news = SITE / "out" / "news.js"
    if news.exists():
        roh = news.read_text(encoding="utf-8")
        try:
            n = json.loads(roh[roh.index("=") + 1:].rstrip().rstrip(";"))
            for x in n.get("preis", []) + n.get("neu", []):
                for sp in SPRACHEN:
                    rest = f"models/{slug(x['k'])}.html"
                    if (SITE / (sp + rest)).exists():
                        urls.append(DOMAIN + sp + rest)
        except Exception:
            pass
    # montags: komplette Sitemap
    if time.gmtime().tm_wday == 0 and (SITE / "sitemap.xml").exists():
        urls += re.findall(r"<loc>([^<]+)</loc>", (SITE / "sitemap.xml").read_text(encoding="utf-8"))
    eindeutig = list(dict.fromkeys(u for u in urls if u.startswith(DOMAIN)))
    return eindeutig[:10000]


def main():
    key = schluessel()
    if not key:
        print("Kein IndexNow-Schlüssel gefunden – übersprungen")
        return 0
    if not live(key):
        print("IndexNow übersprungen: Domain zeigt noch nicht auf die Website")
        return 0
    urls = adressen()
    body = json.dumps({"host": HOST, "key": key, "keyLocation": DOMAIN + key + ".txt", "urlList": urls}).encode("utf-8")
    req = urllib.request.Request(ENDPUNKT, data=body, method="POST",
                                 headers={"Content-Type": "application/json; charset=utf-8", "User-Agent": "aiapicompare-indexnow"})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            print(f"IndexNow: {len(urls)} Adressen gemeldet (Status {r.status})")
    except Exception as e:
        print(f"IndexNow-Meldung fehlgeschlagen: {e}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
