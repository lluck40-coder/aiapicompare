# API-Token-Vergleich – Kurzanleitung

## Dateien
| Datei | Zweck |
|---|---|
| `index.html` | Preisvergleich (Hauptseite) |
| `kosten.html` | Kostenrechner (Text, Bilder, Video) und Token-Rechner („Text einfügen“: Token-Schätzung im Browser, der Text wird nicht gespeichert oder übertragen) |
| `bestenliste.html` | „Welches Modell wofür?“ – Platzierungen aus der Arena-Bestenliste (CC BY 4.0) mit günstigstem Preis |
| `news.html` | Neuigkeiten: neue Modelle und Preisänderungen aus den eigenen Preisdaten (keine fremden Texte) |
| `build_news.py` | erzeugt `out/staerken.js` (Arena-Ranglisten) und `out/news.js` (Neuigkeiten); läuft nachts nach `build_data.py` |
| `compare/…` (erzeugt) | Vergleichsseiten „Modell A vs. B“ (Preis & Arena-Platzierungen), 4 Sprachen |
| `feed.xml` (erzeugt) | RSS-Feed mit Preisänderungen und neuen Modellen (auch /de/, /zh/, /ru/) |
| `llms.txt` (erzeugt) | Kurzbeschreibung der Website für KI-Assistenten |
| `indexnow.py` + `<Schlüssel>.txt` | meldet neue/geänderte Seiten nachts an Bing & Co. (IndexNow), sobald die Domain live ist |
| `bereiche.js` | Namen der Anwendungsbereiche in 4 Sprachen |
| `methodik.html` | „So vergleichen wir“: Datenquellen, Einheiten, Referenzpreis und Kennzeichnung, veraltete Daten, Unabhängigkeit |
| `anbieter_info.json` | **von Hand gepflegt:** Firmensitz, Zahlungsarten, Mindestaufladung, Gebühren, Datenschutz je Anbieter (mit Quellen) → Kasten „Auf einen Blick“ auf den Anbieter-Seiten und Tabelle „Bedingungen im Vergleich“. Nach dem Prüfen `stand` anpassen; die Kontrolle erinnert nach 120 Tagen |
| `referenz.js` | Referenzpreis je Modell und Kennzeichnung „⚠ weit unter Referenzpreis“ / „⏱ Stand …“ / „Batch“ – dieselben Regeln stehen in `build_pages.py` |
| `finder.html` | Modell-Finder: 3 Fragen (Zweck, Budget, Qualität vs. Preis) → passende Modelle aus Arena-Platzierung + Preis |
| `preisindex.html` | KI-Preisindex: Entwicklung der API-Preise seit dem Starttag (Daten: `out/preisindex.js`, erzeugt von `build_news.py`) |
| `einbetten.html` | Preis-Widget für fremde Websites (Code zum Kopieren); die Widgets selbst liegen unter `widget/<modell>.html` (erzeugt) |
| `providers/…` (erzeugt) | Anbieter-Seiten (Modelle, günstigste Modelle, Arena-Top, Anbindung), 4 Sprachen |
| `404.html` (erzeugt) | eigene Fehlerseite mit Suche und Links |
| `pruefen.py` | automatische Kontrolle nach jedem Lauf: fehlgeschlagene Abrufe, veraltete Daten, tote Links → GitHub-Issue (E-Mail von GitHub), schließt sich selbst, wenn alles wieder geht |
| `free.html` | Kostenlose Modelle (funktioniert auch lokal; online ersetzt durch die Sprachfassungen aus `build_pages.py`) |
| `build_pages.py` | erzeugt Modellseiten (4 Sprachen), Seite „Kostenlose Modelle“, A–Z-Verzeichnis, Sitemap und `/api/prices.json` |
| `theme.js` | heller/dunkler Modus |
| `github-workflow/preise.yml` | nächtliche Aktualisierung + Veröffentlichung (siehe `ANLEITUNG-ONLINE.md`) |
| `anbindung.html` | Anleitungen: Anbieter in Hermes, VS Code, Cursor, Open WebUI, Aider, eigenen Code einbinden |
| `impressum.html`, `datenschutz.html` | Vorlagen – **gelb markierte Platzhalter ausfüllen** |
| `config.js` | Startseiten der Anbieter und **Besucherstatistik** (Umami-Website-ID) – nur hier ändern |
| `einwilligung.js` | Cookie-Fenster beim ersten Besuch („Ablehnen“ / „Akzeptieren“, gleichwertig) und Besucherstatistik – lädt Umami erst nach Einwilligung; „Cookie-Einstellungen“ erscheint automatisch in jeder Fußzeile |
| `style.css`, `sprache.js` | gemeinsames Aussehen bzw. Sprachumschaltung (DE/EN/中文) der Unterseiten |
| `build_data.py` → `out/data.js` | Preise neu abrufen: `python build_data.py` (9 Anbieter; für Novita ggf. vorher `set NOVITA_API_KEY=…`) |
| `api-token-vergleich_mobil.html` | Preisvergleich als Einzeldatei (Daten eingebettet) |

## Cookie-Fenster und Besucherstatistik (Umami)
- **Einrichten:** kostenloses Konto bei Umami Cloud (cloud.umami.is) anlegen – bei der Anmeldung die
  **Datenregion EU** wählen (lässt sich später nicht ändern). Website `aiapicompare.com` hinzufügen und im
  Tracking-Code die `data-website-id` kopieren → in `config.js` bei `statistik.websiteId` eintragen.
  Den Auftragsverarbeitungsvertrag (DPA) schließt Umami mit dem Konto automatisch ab.
- Solange `websiteId` leer ist, gibt es **kein** Fenster und keine Zählung.
- Mit ID: Beim ersten Besuch erscheint das Fenster. Erst nach „Akzeptieren“ wird das Umami-Skript geladen
  (ohne Cookies). „Ablehnen“ ist gleich groß und gleich gestaltet (Rechtsprechung: VG Hannover 2025).
  Die Wahl gilt 12 Monate; Widerruf jederzeit über „Cookie-Einstellungen“ in jeder Fußzeile.
- Gezählt werden Seitenaufrufe (ohne Teil nach dem #, ohne Parameter) und diese Ereignisse:
  „Zum Anbieter“ (Anbieter + Zielseite), „Externer Link“, „Vergleich geöffnet“ (Modell), „Auswahl“ (Filter,
  Sortierung, Ansicht, Finder-Antworten, Rechner-Modus …), „Sprache“, „Design“, „Kopiert“, „Datei“ (API/RSS),
  „E-Mail“, „Klick“ (übrige Knöpfe). Eingaben in Such-, Text- und Zahlenfeldern werden **nie** erfasst.
- Auswertung: im Umami-Dashboard unter „Events“ (Eigenschaften wie `anbieter`, `feld`, `wert`, `seite`).
- Gezählt wird nur auf `aiapicompare.com` (nicht bei lokalen Tests). Die Widgets auf fremden Seiten zählen nie.
- Wird ein anderer Dienst eingesetzt oder kommt etwas dazu: `einwilligung.js` (Texte) und `datenschutz.html`
  anpassen und in `einwilligung.js` `VERSION` erhöhen – dann wird jeder erneut gefragt.

## Vor der Veröffentlichung
1. `impressum.html` und `datenschutz.html` ausfüllen (der gelbe Vorlage-Hinweis verschwindet automatisch, wenn alle Platzhalter ersetzt sind).
2. Abschnitt „Hosting“ in der Datenschutzerklärung an den tatsächlichen Hoster anpassen (vorbereitet: GitHub Pages).
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

## Bestenliste & Neuigkeiten – rechtliche Hinweise
- Die Platzierungen stammen aus dem Datensatz „lmarena-ai/leaderboard-dataset“ (Arena, ehemals LMArena),
  Lizenz CC BY 4.0. Die Quellenangabe mit Lizenz-Link und Hinweis auf Änderungen steht auf der
  Bestenliste, auf jeder Modellseite und (per Link) im Preisvergleich – bitte nicht entfernen.
- Die Neuigkeiten entstehen nur aus den eigenen Preisdaten. Fremde Schlagzeilen oder Artikeltexte werden
  bewusst nicht übernommen; zu den Anbietern gibt es nur einfache Links.

## Suchmaschinen (einmalig von Hand, nach dem Umstellen der Domain)
1. **Google Search Console** (search.google.com/search-console): Domain `aiapicompare.com` hinzufügen,
   per DNS-TXT-Eintrag bei Porkbun bestätigen, dann unter „Sitemaps“ `sitemap.xml` einreichen.
2. **Bing Webmaster Tools** (bing.com/webmasters): „Import from Google Search Console“ wählen – fertig.
   Danach meldet `indexnow.py` neue und geänderte Seiten jede Nacht automatisch.

## Automatische Kontrolle
Nach jedem nächtlichen Lauf prüft `pruefen.py` die Daten und alle internen Links. Bei Problemen legt GitHub
ein Issue „Automatische Kontrolle: Probleme gefunden“ an – GitHub schickt dir dazu eine E-Mail
(Einstellung: github.com → Settings → Notifications). Ist alles wieder in Ordnung, wird das Issue automatisch geschlossen.
Lokal: `python pruefen.py vorschau`.

## Preisindex
Startet automatisch mit dem ersten Tag, an dem `out/verlauf.json` Daten hat. Aussagekräftig wird er nach einigen Wochen;
bis mindestens zwei Messpunkte vorliegen, zeigt die Seite einen Hinweis statt des Diagramms.

## Kennzeichnung „⚠ weit unter Referenzpreis“
Damit man dem „günstigsten Preis“ trauen kann, bekommt jedes Textmodell einen Referenzpreis (gemischt 3 Teile Input : 1 Teil Output):
- **Geschlossene Modelle** (GPT, Claude, Gemini, Grok …): Referenz = OpenRouter (in der Regel der Listenpreis des Herstellers).
  Gekennzeichnet wird, was mehr als 50 % darunter liegt. Varianten wie „…-uncensored“ / „…-thinking“ ohne eigene Referenz → Grundmodell.
- **Offene Modelle**: Referenz = Median aller Anbieter (ab 3 Angeboten). Gekennzeichnet: mehr als 80 % darunter, nur wenn die Referenz ≥ $0.20 ist.
- Preisvergleich: gekennzeichnete Angebote bleiben sichtbar, „★ günstigster“ und „+X %“ ignorieren sie; Filter „Angebote weit unter Referenzpreis ausblenden“.
- Modell-Finder, Bestenliste, Kostenrechner, A-vs-B-Seiten, Widget, Modellseiten-Text: standardmäßig ohne solche Angebote (zuschaltbar).
- Fehlgeschlagener Abruf: Preise mit „⏱ Stand …“; älter als 3 Tage → nicht mehr für Empfehlungen.
Schwellen ändern: `referenz.js` **und** `build_pages.py` (Abschnitt „Referenzpreis“) gleich anpassen, Text auf `methodik.html` nachziehen.
