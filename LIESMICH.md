# API-Token-Vergleich – Kurzanleitung

## Dateien
| Datei | Zweck |
|---|---|
| `index.html` | Preisvergleich (Hauptseite) |
| `kosten.html` | Kostenrechner (Text, Bilder, Video) |
| `free.html` | Kostenlose Modelle (funktioniert auch lokal; online ersetzt durch die Sprachfassungen aus `build_pages.py`) |
| `build_pages.py` | erzeugt Modellseiten (4 Sprachen), Seite „Kostenlose Modelle“, A–Z-Verzeichnis, Sitemap und `/api/prices.json` |
| `theme.js` | heller/dunkler Modus |
| `github-workflow/preise.yml` | nächtliche Aktualisierung + Veröffentlichung (siehe `ANLEITUNG-ONLINE.md`) |
| `anbindung.html` | Anleitungen: Anbieter in Hermes, VS Code, Cursor, Open WebUI, Aider, eigenen Code einbinden |
| `impressum.html`, `datenschutz.html` | Vorlagen – **gelb markierte Platzhalter ausfüllen** |
| `config.js` | **Affiliate-Links** und Kennzeichnung – nur hier ändern |
| `PARTNERPROGRAMME.md` | interne Übersicht aller gefundenen Partnerprogramme (Provision, Anmeldung) – nicht veröffentlichen |
| `style.css`, `sprache.js` | gemeinsames Aussehen bzw. Sprachumschaltung (DE/EN/中文) der Unterseiten |
| `build_data.py` → `out/data.js` | Preise neu abrufen: `python build_data.py` (9 Anbieter; für Novita ggf. vorher `set NOVITA_API_KEY=…`) |
| `api-token-vergleich_mobil.html` | Preisvergleich als Einzeldatei (Daten eingebettet) |

## Affiliate-Links aktivieren
In `config.js` beim Anbieter `aktiv: true` setzen und entweder
- `parameter: "ref=MEINCODE"` (wird an jeden Link zu diesem Anbieter angehängt) und/oder
- `startseite: "https://…/mein-partnerlink"` (für „Zum Anbieter“/„Konto erstellen“)

eintragen. Alle Links zu diesem Anbieter bekommen dann automatisch den Hinweis **„Anzeige“**,
`rel="sponsored"`, und oben auf den Seiten erscheint der Transparenz-Hinweis.
Ohne aktiven Affiliate-Link wird nichts gekennzeichnet (dann ist es keine Werbung).

## Vor der Veröffentlichung
1. `impressum.html` und `datenschutz.html` ausfüllen (der gelbe Vorlage-Hinweis verschwindet automatisch, wenn alle Platzhalter ersetzt sind).
2. Abschnitt „Hosting“ in der Datenschutzerklärung an den tatsächlichen Hoster anpassen.
3. Nach jedem `python build_data.py` die Mobil-Datei neu erzeugen (Daten sind dort eingebettet).

## Sprachen
Preisvergleich: Deutsch, Englisch, Chinesisch, Russisch. Anbindung, Impressum, Datenschutz: Deutsch, Englisch, Chinesisch.
Impressum und Datenschutz: nur den **deutschen** Teil ausfüllen – die Übersetzungen übernehmen die Angaben automatisch. Die deutsche Fassung ist rechtlich maßgeblich.

## Fähigkeiten von Bild- und Videomodellen (Piktogramme)
Werden von `build_data.py` aus den Eingabefeldern der Anbieter-Kataloge abgeleitet (z. B. Feld für Endbild → ⏭️).
Bis zum nächsten Datenabruf sind sie nur aus den Modellnamen abgeleitet und daher unvollständig.

## Lokale Vorschau der kompletten Website
```
python build_data.py          # Preise holen (optional)
python build_pages.py vorschau
```
Danach `vorschau/index.html` öffnen. Dort funktionieren auch die Modellseiten und „Kostenlose Modelle“
(in der normalen `index.html` im Projektordner führen diese Links ins Leere, weil die Seiten erst erzeugt werden).

## Preisverlauf und „NEU“
`build_data.py` schreibt `out/verlauf.json`. Preisänderungen erscheinen im Vergleich als ↓/↑ in Prozent,
neue Modelle der letzten 7 Tage als „NEU“, auf den Modellseiten als Diagramm.
Beim allerersten Lauf wird nur der Ausgangsstand gespeichert (nichts wird als neu markiert).
