# aiapicompare.com online bringen – Schritt für Schritt

Danach läuft alles von selbst: Jede Nacht um ca. 04:17 Uhr holt GitHub die aktuellen Preise
und veröffentlicht die Website neu. Kosten: nur die Domain (ca. 10–15 € pro Jahr).

---

## 1. Vorher erledigen (rechtlich nötig)
- [ ] `impressum.html` – gelb markierte Angaben im **deutschen** Teil ausfüllen
- [ ] `datenschutz.html` – Name, Anschrift, E-Mail, Datum, Aufsichtsbehörde und die
      Rechtsgrundlage für die Übermittlung in die USA eintragen (Hinweis steht direkt im Text)
- [ ] Partnerlinks in `config.js` eintragen (siehe `PARTNERPROGRAMME.md`)

## 2. Domain kaufen
Bei einem Anbieter deiner Wahl **aiapicompare.com** registrieren (z. B. Cloudflare Registrar,
INWX, Namecheap). Optional zusätzlich **aiapicompare.de** – diese später per Weiterleitung auf
die .com-Adresse zeigen lassen.

## 3. GitHub-Konto und Repository
1. Konto anlegen auf https://github.com (kostenlos).
2. Oben rechts **+ → New repository**
   - Name: `aiapicompare`
   - **Public** (für kostenloses GitHub Pages nötig)
   - nichts weiter ankreuzen → **Create repository**

## 4. Dateien hochladen
Am einfachsten mit **GitHub Desktop** (https://desktop.github.com):
1. GitHub Desktop installieren und anmelden.
2. **File → Add local repository** → den Ordner `api-token-vergleich` wählen
   → „create a repository“ bestätigen.
3. **Publish repository** → Name `aiapicompare`, Haken bei „Keep this code private“ **entfernen**.

Die Datei `.gitignore` sorgt dafür, dass interne Dateien (z. B. `PARTNERPROGRAMME.md`,
die Mobil-Datei) **nicht** hochgeladen werden.

## 4b. Automatik einschalten (einmalig, 1 Minute)
Die Datei für die nächtliche Aktualisierung liegt im Ordner `github-workflow/preise.yml`.
GitHub erwartet sie unter `.github/workflows/` – so legst du sie dort an:
1. Im Repository auf github.com: **Add file → Create new file**
2. Als Dateinamen eintippen: `.github/workflows/preise.yml`
   (die Schrägstriche legen die Ordner automatisch an)
3. Den kompletten Inhalt von `github-workflow/preise.yml` hineinkopieren → **Commit changes**

## 5. Geheime Schlüssel hinterlegen
Im Repository: **Settings → Secrets and variables → Actions → New repository secret**

| Name | Wert |
|---|---|
| `ANYMODEL_API_KEY` | dein AnyModel-Key (steht in deiner Hermes-`.env` bei `HERMES_CUSTOM_ANYMODEL_ORG`) |
| `NOVITA_API_KEY` | optional, nur falls Novita ohne Key nicht abrufbar ist |

Schlüssel niemals in Dateien schreiben, die hochgeladen werden.

## 6. GitHub Pages einschalten
1. **Settings → Pages → Build and deployment → Source: „GitHub Actions“**
2. **Actions** (oben) → „Preise aktualisieren & veröffentlichen“ → **Run workflow**
3. Nach 2–5 Minuten ist die Seite unter `https://DEINNAME.github.io/aiapicompare/` erreichbar.

## 7. Eigene Domain verbinden
1. **Settings → Pages → Custom domain:** `aiapicompare.com` → **Save**
   (zuerst hier eintragen, dann DNS – so empfiehlt es GitHub)
2. Beim Domain-Anbieter im DNS-Bereich eintragen:

| Typ | Name | Wert |
|---|---|---|
| A | @ | 185.199.108.153 |
| A | @ | 185.199.109.153 |
| A | @ | 185.199.110.153 |
| A | @ | 185.199.111.153 |
| AAAA | @ | 2606:50c0:8000::153 |
| AAAA | @ | 2606:50c0:8001::153 |
| AAAA | @ | 2606:50c0:8002::153 |
| AAAA | @ | 2606:50c0:8003::153 |
| CNAME | www | DEINNAME.github.io |

3. Warten (meist unter 1 Stunde, maximal 24 Stunden), dann in **Settings → Pages**
   den Haken **„Enforce HTTPS“** setzen.
4. Empfohlen: unter **Profil → Settings → Pages** die Domain **verifizieren**
   (schützt davor, dass jemand anderes sie bei GitHub verwendet).

## 8. Bei Google anmelden
1. https://search.google.com/search-console → Domain `aiapicompare.com` hinzufügen
   (Bestätigung per DNS-TXT-Eintrag beim Domain-Anbieter).
2. **Sitemaps → `https://aiapicompare.com/sitemap.xml`** einreichen.

---

## Im Alltag
- **Änderungen** (z. B. neue Partnerlinks in `config.js`): Datei lokal ändern → in GitHub Desktop
  **Commit** → **Push**. Die Seite ist wenige Minuten später aktualisiert.
- **Preise sofort aktualisieren:** Actions → Run workflow.
- **Wenn ein Anbieter ausfällt:** Seine letzten Preise bleiben stehen, oben auf der Seite erscheint
  „⚠ nicht aktualisiert: …“. Fehlermeldungen findest du unter **Actions** im jeweiligen Lauf.
- **Preisverlauf:** Jeder nächtliche Lauf speichert die Preise (`out/verlauf.json`) im Repository – daraus
  entstehen die Verlaufsdiagramme auf den Modellseiten und die ↓/↑-Markierungen.
- **Modellseiten:** werden bei jedem Lauf automatisch neu erzeugt (über 5.000 Seiten in 4 Sprachen) –
  nichts davon musst du hochladen.
