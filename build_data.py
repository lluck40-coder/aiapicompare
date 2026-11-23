#!/usr/bin/env python3
"""
build_data.py — zieht reale Preise von OpenRouter, UplinkSwitch und anymodel
und schreibt out/data.js (JS-Export). Läuft lokal (file://) UND auf GitHub Pages,
weil die Daten eingebettet sind, nicht abgefragt werden.
"""
import json, urllib.request, time, re, os, sys
from pathlib import Path

OUT = Path(__file__).resolve().parent / "out"
OUT.mkdir(exist_ok=True)
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"


def get(url, key=None, timeout=90):
    h = {"User-Agent": UA, "Accept": "application/json"}
    if key:
        h["Authorization"] = f"Bearer {key}"
    req = urllib.request.Request(url, headers=h)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read().decode("utf-8", "replace")


def load_anymodel_key():
    """Key zuerst aus der Umgebungsvariable (GitHub-Secret ANYMODEL_API_KEY),
    sonst aus der lokalen Hermes-.env auf dem eigenen Rechner."""
    if os.environ.get("ANYMODEL_API_KEY"):
        return os.environ["ANYMODEL_API_KEY"].strip()
    env = Path.home() / "AppData/Local/hermes/profiles/bot1/.env"
    if not env.exists():
        return None
    for line in env.read_text(encoding="utf-8").splitlines():
        if line.startswith("HERMES_CUSTOM_ANYMODEL_ORG") and "=" in line:
            return line.split("=", 1)[1].strip()
    return None


def ctx_zahl(v):
    """Kontextfenster als ganze Zahl. Manche Anbieter liefern Text wie "200k", "1,000k tokens" oder "1M"."""
    if isinstance(v, bool) or v is None:
        return 0
    if isinstance(v, (int, float)):
        return int(v) if v > 0 else 0
    s = str(v).strip().lower().replace(",", "").replace("_", "").replace(" ", "")
    m = re.match(r"^(\d+(?:\.\d+)?)(k|m)?", s)
    if not m:
        return 0
    return int(float(m.group(1)) * {"k": 1_000, "m": 1_000_000}.get(m.group(2), 1))


def kanon(name):
    """Normalisiert Modell-IDs (ggf. mit Anbieter-Präfix) zu einem Familien-Kürzel."""
    s = name.split("/")[-1].lower().strip()
    return re.sub(r"[.\-_]+", "-", s).strip("-")


# Entwickler-Prefixe -> kanonischer Name (für bekannte-Anbieter-Sortierung)
ENTW_MAP = {
    "openai": "OpenAI", "anthropic": "Anthropic", "google": "Google",
    "gemini": "Google", "deepseek": "DeepSeek", "deepseek-ai": "DeepSeek",
    "z-ai": "Z.ai", "zai-org": "Z.ai", "qwen": "Qwen", "moonshotai": "Moonshot AI",
    "moonshot": "Moonshot AI", "meta-llama": "Meta", "meta": "Meta",
    "mistralai": "Mistral", "mistral": "Mistral", "minimax": "MiniMax",
    "xai": "xAI", "nvidia": "NVIDIA", "nvidia-nim": "NVIDIA", "tencent": "Tencent",
    "xiaomi": "Xiaomi", "microsoft": "Microsoft", "inclusionai": "inclusionAI",
    "perplexity": "Perplexity", "cohere": "Cohere", "amazon": "Amazon",
}
def entw_of(pid, fallback=""):
    pre = pid.split("/")[0].lower() if "/" in pid else ""
    return ENTW_MAP.get(pre, fallback or pre)


# ---------- AnyModel: Bild/Video ----------
VIDEO_RE = re.compile(r"(video|veo|kling|sora|seedance|hailuo|wan-?\d|runway|imagine-vid)", re.I)
BILD_RE  = re.compile(r"(image|seedream|banana|fibo|flux|imagen|dall-?e|imagine-img)", re.I)

def am_typ(m):
    """Typ eines AnyModel-API-Eintrags: 'video' | 'bild' | 'text'."""
    for feld in ("type", "kind", "modality", "category"):
        v = str(m.get(feld) or "").lower()
        if "video" in v: return "video"
        if "image" in v or "bild" in v: return "bild"
    oms = [str(x).lower() for x in ((m.get("architecture") or {}).get("output_modalities") or m.get("output_modalities") or [])]
    if "video" in oms: return "video"
    if "image" in oms: return "bild"
    mid = m.get("id", "")
    if VIDEO_RE.search(mid): return "video"
    if BILD_RE.search(mid): return "bild"
    return "text"

# Rückfallwerte laut https://anymodel.org/en/pricing (Stand 2026-11-22),
# falls die Tabelle auf der Preisseite nicht ausgelesen werden kann.
# Angabe in "Balance-Tokens" pro Einheit; 1 Mio. Balance-Tokens = 0,05 USD.
ANYMODEL_MEDIA_FALLBACK = [
    ("Grok Imagine Video 480p",      "second", 125000),
    ("Grok Imagine Video 720p",      "second", 175000),
    ("Grok Imagine Video 1.5 480p",  "second", 200000),
    ("Grok Imagine Video 1.5 720p",  "second", 350000),
    ("Grok Imagine Video 1.5 1080p", "second", 625000),
    ("Image (gpt-image-2.5)",        "image",  131700),
]
AM_TOKEN_USD = 0.05 / 1e6

def scrape_anymodel_media():
    """Liest die Medien-Tabelle (Modell | Einheit | Balance-Tokens) von der Preisseite.
    Gibt Liste (name, einheit, tokens) zurück; bei Fehler die Rückfallwerte."""
    try:
        html = get("https://anymodel.org/en/pricing", timeout=35)
        txt = re.sub(r"<[^>]+>", " | ", html)
        txt = re.sub(r"&nbsp;|&#160;", " ", txt)
        txt = re.sub(r"\s+", " ", txt)
        zeilen = []
        for mm in re.finditer(r"((?:Grok|Image|Veo|Kling|Sora|Seedance|Wan|Hailuo|Runway)[^|]{0,60}?)\s*(?:\|\s*)+per\s+(second|image|video|generation|minute)[^|]*(?:\|\s*)+([0-9][0-9,.\s]*[0-9])", txt, re.I):
            name = mm.group(1).strip()
            einheit = mm.group(2).lower()
            tokens = int(re.sub(r"[^0-9]", "", mm.group(3)))
            if tokens > 0:
                zeilen.append((name, einheit, tokens))
        if zeilen:
            print(f"  Preisseite: {len(zeilen)} Medien-Zeilen gelesen", flush=True)
            return zeilen
        print("  (!) Medien-Tabelle nicht gefunden – nutze Rückfallwerte", flush=True)
    except Exception as e:
        print(f"  (!) Preisseite nicht lesbar ({e}) – nutze Rückfallwerte", flush=True)
    return ANYMODEL_MEDIA_FALLBACK


def scrape_anymodel_page(slug, key):
    """Einzelne anymodel-Modellseite: liest den eingebetteten Preis-Block aus."""
    url = f"https://anymodel.org/en/models/{slug}"
    body = get(url, timeout=35)
    i3 = body.find("text-3xl font-black")
    if i3 < 0:
        return None
    blk = body[i3 - 10: i3 + 400]
    vals = re.findall(r'"\$?([0-9]+\.[0-9]+)', blk)
    if not vals:
        vals = re.findall(r"\$([0-9]+\.[0-9]+)", blk)
    if not vals:
        return None
    return {"price": float(vals[0]), "url": url}


# ---------- Fähigkeiten von Bild-/Video-Modellen ----------
# Abgeleitet aus den Eingabefeldern ("params") bzw. Merkmalen ("features") der
# Anbieter-Kataloge und – nur wo eindeutig – aus dem Modellnamen.
AUFL_ORDNUNG = ["480p", "720p", "768p", "1080p", "1k", "1.5k", "2k", "3k", "4k"]

def faehigkeiten(kind, name, params=None, features=None, tags=None):
    n = (name or "").lower()
    p = params if isinstance(params, dict) else {}
    f = set(str(x).lower() for x in (features or []))
    t = set(str(x).lower() for x in (tags or []))
    caps = []

    def has(*ks):
        return any(k in p for k in ks)

    def spec(k):
        v = p.get(k)
        return v if isinstance(v, dict) else {}

    def req(k):
        return bool(spec(k).get("required"))

    def werte(k):
        return [str(x).lower() for x in (spec(k).get("values") or [])]

    def add(c):
        if c not in caps:
            caps.append(c)

    if kind == "video":
        i2v_name = re.search(r"image[- ]?to[- ]?video|\bi2v\b", n)
        t2v_name = re.search(r"text[- ]?to[- ]?video|\bt2v\b", n)
        motion = "motion" in n
        avatar = "avatar" in n
        ref_name = "reference" in n
        bild_pflicht = any(req(k) for k in ("image_url", "image_urls", "start_image_url"))
        if ("text-to-video" in f or t2v_name or
                (has("prompt") and not bild_pflicht and not (i2v_name or motion or avatar or ref_name)
                 and not has("video_url", "video_urls"))):
            add("t2v")
        if "image-to-video" in f or i2v_name or has("image_url", "image_urls", "start_image_url"):
            add("start")
        if (has("end_image_url") or "frame" in werte("generation_type")
                or (spec("image_urls").get("max_items") == 2 and not has("reference_image_urls"))):
            add("ende")
        if (has("reference_image_urls", "elements", "kling_elements") or "reference" in werte("generation_type")
                or ref_name):
            add("ref")
        if motion:
            add("motion")
        elif has("video_url", "video_urls") or "video-editing" in f:
            add("v2v")
        if has("generate_audio", "sound") or spec("audio").get("type") == "boolean":
            add("ton")
        if has("audio_url", "reference_audio_urls") or avatar:
            add("audio_in")
        if has("multi_shots", "multi_prompt"):
            add("multishot")
    elif kind in ("bild", "image"):
        edit_name = "edit" in n
        spezial = re.search(r"upscal|resiz|extend", n)
        if ("text-to-image" in f or
                (has("prompt") and not edit_name and not spezial
                 and not any(req(k) for k in ("image_url", "image_urls")))):
            add("t2i")
        if "image-editing" in f or edit_name or (has("image_url", "image_urls") and not spezial):
            add("edit")
        if (spec("image_urls").get("max_items") or 0) >= 3:
            add("multiref")
        if has("mask_url"):
            add("maske")
        if "transparent" in werte("background"):
            add("transparent")
        if "upscal" in n:
            add("upscale")
        if "extend" in n:
            add("outpaint")

    # höchste Auflösung und längste Dauer
    aufl = None
    for v in werte("resolution") + (["4k"] if re.search(r"\b4k\b", n) else []):
        v = v.replace(" ", "")
        if v in AUFL_ORDNUNG and (aufl is None or AUFL_ORDNUNG.index(v) > AUFL_ORDNUNG.index(aufl)):
            aufl = v
    if aufl == "4k":
        add("4k")
    d = spec("duration")
    dwerte = [x for x in (d.get("values") or []) if isinstance(x, (int, float))]
    dauer = d.get("max") or (max(dwerte, default=None))
    dauer_fix = dwerte[0] if len(dwerte) == 1 else (d.get("min") if d.get("min") and d.get("min") == d.get("max") else None)
    if "uncensored" in t or "uncensored" in n:
        add("unzensiert")
    erg = {"faeh": caps}
    if aufl:
        erg["aufl"] = aufl.upper() if aufl.endswith("k") else aufl
    if dauer:
        erg["dauer"] = dauer
    if dauer_fix:
        erg["dauer_fix"] = dauer_fix
    mi = spec("image_urls").get("max_items") or spec("reference_image_urls").get("max_items")
    if mi and mi >= 2:
        erg["refmax"] = mi
    return erg


print("=== OpenRouter ===", flush=True)
or_prices = {}
TYP_MAP = {"text": "text", "image": "bild", "video": "video", "audio": "audio"}
try:
    or_data = json.loads(get("https://openrouter.ai/api/v1/models"))["data"]
    for m in or_data:
        pid = m.get("id", "")
        p = m.get("pricing") or {}
        if not p:
            continue
        inp = float(p.get("prompt", "0") or 0)
        out = float(p.get("completion", "0") or 0)
        arch = m.get("architecture") or {}
        typ = [TYP_MAP[om] for om in (arch.get("output_modalities") or ["text"]) if om in TYP_MAP] or ["text"]
        # Media-Preise (Bild-Generierung): pricing.image = $ pro Bild
        media_preis = None
        try:
            mp = float(p.get("image", "0") or 0)
            if mp > 0:
                media_preis = round(mp, 4)
        except (TypeError, ValueError):
            pass
        def _null(v):
            try:
                return float(v) == 0
            except (TypeError, ValueError):
                return True   # nicht-numerische Felder ignorieren
        gratis = (inp == 0 and out == 0 and media_preis is None and str(p.get("prompt")) in ("0", "0.0")
                  and str(p.get("completion")) in ("0", "0.0") and all(_null(v) for v in p.values()))
        if inp < 0 or out < 0 or (inp <= 0 and out <= 0 and media_preis is None and not gratis):
            continue
        or_prices[kanon(pid)] = {
            "anbieter": "OpenRouter", "roh_id": pid, "name": m.get("name", pid),
            "context": m.get("context_length") or 0,
            "in": 0.0 if gratis else (round(inp * 1e6, 4) if inp > 0 else None),
            "out": 0.0 if gratis else (round(out * 1e6, 4) if out > 0 else None),
            "typ": typ,
        }
        if gratis:
            or_prices[kanon(pid)]["gratis"] = True
        if media_preis is not None:
            or_prices[kanon(pid)]["media_preis"] = media_preis
            or_prices[kanon(pid)]["einheit"] = "image"
    print(f"  {len(or_prices)} Modelle mit Preis", flush=True)
except Exception as e:
    print(f"  FEHLER OpenRouter: {e}", flush=True)

print("=== UplinkSwitch ===", flush=True)
up_prices = {}
try:
    up_raw = json.loads(get("https://api.uplinkswitch.com/v1/catalog"))
    up_items = up_raw["data"]
    for m in up_items:
        if m.get("type") != "chat":
            continue
        pid = m.get("id", "")
        pr = m.get("pricing") or {}
        if not pr:
            continue
        inp = pr.get("input")
        out = pr.get("output")
        if inp is None and out is None:
            continue
        up_prices[kanon(pid)] = {
            "anbieter": "UplinkSwitch", "roh_id": pid, "name": m.get("display_name", pid),
            "entwickler": m.get("developer", ""), "context": m.get("context_window") or 0,
            "in": round(inp, 4) if inp else None, "out": round(out, 4) if out else None,
            "typ": ["text"],
        }
    print(f"  {len(up_prices)} Chat-Modelle mit Preis", flush=True)

    # Media-Katalog: Bild / Video / Audio / 3D — Preise pro Einheit (nicht pro 1M Token)
    KIND_MAP = {"image": "bild", "video": "video", "audio": "audio", "3d": "3d"}
    EINHEIT_LABEL = {"image": "image", "second": "second", "1k_characters": "1k_chars",
                     "generation": "generation", "minute": "minute", "1k_bytes": "1k_bytes"}
    up_media = json.loads(get("https://api.uplinkswitch.com/v1/catalog/media"))
    med_items = up_media.get("data", up_media) if isinstance(up_media, dict) else up_media
    n_media = 0
    for m in med_items:
        kind = m.get("kind", "")
        if kind not in KIND_MAP:
            continue
        pid = m.get("id", "")
        prs = m.get("pricing") or []
        preise = []
        for pr in prs:
            try:
                v = float(pr.get("price_usd") or 0)
                if v > 0:
                    preise.append(v)
            except (TypeError, ValueError):
                continue
        if not preise:
            continue
        key_ = "media-" + kanon(pid)   # gleicher Schlüssel wie bei AnyModel -> vergleichbar
        up_prices[key_] = {
            "anbieter": "UplinkSwitch", "roh_id": pid, "name": m.get("display_name", pid),
            "entwickler": m.get("developer", ""), "context": 0,
            "in": None, "out": None,
            "typ": [KIND_MAP[kind]],
            "media_preis": round(min(preise), 4),
            "einheit": EINHEIT_LABEL.get(str(m.get("unit")), str(m.get("unit"))),
            "media": True,
        }
        up_prices[key_].update(faehigkeiten(KIND_MAP[kind], m.get("display_name", pid) + " " + pid,
                                            m.get("params"), None, m.get("tags")))
        n_media += 1
    print(f"  + {n_media} Media-Modelle (Bild/Video/Audio)", flush=True)
    print(f"  {len(up_prices)} Einträge gesamt", flush=True)
except Exception as e:
    print(f"  FEHLER UplinkSwitch: {e}", flush=True)

print("=== anymodel (Web-Scraper) ===", flush=True)
am_prices = {}
try:
    key = load_anymodel_key()
    am_raw = json.loads(get("https://anymodel.org/v1/models", key=key))
    am_items = am_raw.get("data", am_raw) if isinstance(am_raw, dict) else am_raw

    # Kanonische Modell-URLs aus llms.txt (kein Slug-Raten)
    llms = get("https://anymodel.org/llms.txt", timeout=35)
    url_map = {}   # slug -> canonical URL
    for mu in re.findall(r"https://anymodel\.org/en/models/([a-z0-9\-]+)", llms):
        url_map.setdefault(mu, f"https://anymodel.org/en/models/{mu}")
    print(f"  llms.txt: {len(url_map)} Modell-URLs", flush=True)

    # ID -> Slug-Kandidaten: 1) URL-Map via kanon-Match 2) Punkt-zu-Strich-Fallback
    am_by_kanon = {}
    for m in am_items:
        am_by_kanon.setdefault(kanon(m.get("id", "")), m)
    for slug, url in url_map.items():
        m = am_by_kanon.get(kanon(slug))
        if m is None:
            continue
        mid = m["id"]
        ctx = m.get("context_length") or 0
        page = None
        for attempt in range(2):
            try:
                page = scrape_anymodel_page(slug, key)
                break
            except Exception as e:
                print(f"  (!) retry {slug}: {e}", flush=True)
                time.sleep(1.0)
        if page:
            am_prices[kanon(mid)] = {
                "anbieter": "AnyModel", "roh_id": mid, "slug": slug,
                "name": mid.split("/")[-1],  # Modellname ohne Vendor-Prefix (z.B. "claude-sonnet-5")
                "context": ctx, "price": round(page["price"], 5),
                "url": page["url"], "einzeln": True, "typ": ["text"],
            }
        time.sleep(0.3)

    # Modelle OHNE eigene Modellseite: Preis aus dem Billing-Modell ableiten.
    # Modellseite bestätigt: Basis 5¢/1M × coefficient = Endpreis (flat, in=out).
    # Verifiziert an 4 gescrapten Seiten (glm-5.3-flash 0.5→0.025, ds-vision 1→0.05,
    # gemini-4-argon 6→0.30, claude-fable-5 16→0.80).
    erfasst_k = set(am_prices.keys())
    n_abgeleitet = 0
    am_bild_coeff = {}
    for m in am_items:
        k = kanon(m.get("id", ""))
        if k in erfasst_k:
            continue
        coeff = ((m.get("billing") or {}).get("coefficient") or {}).get("input")
        try:
            coeff = float(coeff)
        except (TypeError, ValueError):
            continue
        if coeff <= 0:
            continue   # keine klare Preisbasis (gratis/intern) — bewusst weglassen
        typ = am_typ(m)
        if typ == "video":
            continue   # Video wird pro Sekunde abgerechnet -> siehe Preisseite unten
        if typ == "bild":
            am_bild_coeff[k] = (m, coeff)
            continue
        am_prices[k] = {
            "anbieter": "AnyModel", "roh_id": m.get("id", ""), "slug": None,
            "name": m.get("id", "").split("/")[-1],
            "context": m.get("context_length") or 0,
            "price": round(0.05 * coeff, 5),
            "url": "https://anymodel.org/en/pricing",
            "einzeln": True, "typ": ["text"],
        }
        n_abgeleitet += 1
    print(f"  + {n_abgeleitet} abgeleitete Preise (5¢-Basis × coefficient)", flush=True)

    # ---- Medien: Preise pro Einheit (Sekunde Video / Bild) ----
    media_rows = scrape_anymodel_media()
    # Video-Modelle gruppieren: "Grok Imagine Video 1.5 720p" -> Modell + Auflösung
    video = {}
    bild_ref = None
    for name, einheit, tokens in media_rows:
        usd = tokens * AM_TOKEN_USD
        if einheit == "image":
            ref = re.search(r"\(([^)]+)\)", name)
            bild_ref = (kanon(ref.group(1)) if ref else None, usd)
            continue
        mres = re.match(r"(.+?)\s+(\d{3,4}p)$", name)
        modell, aufl = (mres.group(1), mres.group(2)) if mres else (name, "")
        video.setdefault(modell, []).append((aufl, usd, einheit))
    for modell, varianten in video.items():
        varianten.sort(key=lambda v: v[1])
        k = "media-" + kanon(modell.replace(" ", "-"))
        am_prices[k] = {
            "anbieter": "AnyModel", "roh_id": k.replace("media-", ""), "slug": None,
            "name": f"{modell} ({varianten[0][0]}+)" if varianten[0][0] else modell,
            "context": 0, "in": None, "out": None, "typ": ["video"],
            "media_preis": round(varianten[0][1], 5), "einheit": varianten[0][2], "media": True,
            "hinweis": " · ".join(f"{a} ${u:.4f}/s" for a, u, _ in varianten if a),
            "url": "https://anymodel.org/en/pricing",
        }
        am_prices[k].update(faehigkeiten("video", modell))
    # Bildmodelle: Preis pro Bild ≈ coefficient × Faktor. Faktor wird an dem
    # Referenzbild der Preisseite kalibriert (gpt-image-2.5, 1024², medium).
    faktor = 0.005   # Rückfall: 100.000 Balance-Tokens × coefficient
    if bild_ref and bild_ref[0] in am_bild_coeff:
        faktor = bild_ref[1] / am_bild_coeff[bild_ref[0]][1]
    for k, (m, coeff) in am_bild_coeff.items():
        am_prices["media-" + k] = {
            "anbieter": "AnyModel", "roh_id": m.get("id", ""), "slug": None,
            "name": m.get("id", "").split("/")[-1], "context": 0,
            "in": None, "out": None, "typ": ["bild"],
            "media_preis": round(coeff * faktor, 5), "einheit": "image", "media": True,
            "geschaetzt": not (bild_ref and bild_ref[0] == k),
            "hinweis": "1024×1024 · medium",
            "url": "https://anymodel.org/en/pricing",
        }
        am_prices["media-" + k].update(faehigkeiten("bild", m.get("id", "")))
    print(f"  + {len(video)} Video- und {len(am_bild_coeff)} Bildmodelle (Preis pro Einheit)", flush=True)
    print(f"  {len(am_prices)} anymodel-Modelle mit Preis", flush=True)
except Exception as e:
    print(f"  FEHLER anymodel: {e}", flush=True)

print("=== NanoGPT ===", flush=True)
ng_prices = {}
try:
    ng = json.loads(get("https://api.nano-gpt.com/api/v1/models?detailed=true"))["data"]
    for m in ng:
        pid = m.get("id", "")
        p = m.get("pricing") or {}
        try:
            inp = float(p.get("prompt") or 0)
            out = float(p.get("completion") or 0)
        except (TypeError, ValueError):
            continue
        if inp <= 0 and out <= 0:
            continue
        ng_prices[kanon(pid)] = {
            "anbieter": "NanoGPT", "roh_id": pid, "name": m.get("name") or pid,
            "entwickler": entw_of(pid), "context": m.get("context_length") or 0,
            "in": round(inp, 4), "out": round(out, 4), "typ": ["text"],
            "url": "https://nano-gpt.com/api-pricing",
        }
    print(f"  {len(ng_prices)} Modelle mit Preis", flush=True)
except Exception as e:
    print(f"  FEHLER NanoGPT: {e}", flush=True)

print("=== Chutes ===", flush=True)
ch_prices = {}
try:
    ch = json.loads(get("https://llm.chutes.ai/v1/models"))
    ch_items = ch.get("data", ch) if isinstance(ch, dict) else ch
    for m in ch_items:
        pid = m.get("id", "")
        p = m.get("pricing") or {}
        try:
            inp = float(p.get("prompt") or 0)
            out = float(p.get("completion") or 0)
        except (TypeError, ValueError):
            continue
        if inp <= 0 and out <= 0:
            continue
        # Heuristik: Werte < 1e-4 sind pro Token, sonst pro 1M (Docs: flat USD)
        if inp < 1e-4:
            inp *= 1e6
        if out < 1e-4:
            out *= 1e6
        typ = [TYP_MAP[om] for om in (m.get("output_modalities") or ["text"]) if om in TYP_MAP] or ["text"]
        ch_prices[kanon(pid)] = {
            "anbieter": "Chutes", "roh_id": pid,
            "name": pid.split("/")[-1].replace("-", " "),
            "entwickler": entw_of(pid), "context": m.get("context_length") or 0,
            "in": round(inp, 4), "out": round(out, 4), "typ": typ,
            "url": "https://chutes.ai/models",
        }
    print(f"  {len(ch_prices)} Modelle mit Preis", flush=True)
except Exception as e:
    print(f"  FEHLER Chutes: {e}", flush=True)

print("=== DeepInfra ===", flush=True)
di_prices = {}
try:
    di = json.loads(get("https://api.deepinfra.com/models/list"))
    di_items = di.get("data", di) if isinstance(di, dict) else di
    for m in di_items:
        if m.get("reported_type") != "text-generation":
            continue
        p = m.get("pricing") or {}
        if p.get("type") != "tokens":
            continue
        try:
            inp = float(p.get("cents_per_input_token") or 0) * 1e4   # cents/token -> $/1M
            out = float(p.get("cents_per_output_token") or 0) * 1e4
        except (TypeError, ValueError):
            continue
        if inp <= 0 and out <= 0:
            continue
        pid = m.get("model_name", "")
        di_prices[kanon(pid)] = {
            "anbieter": "DeepInfra", "roh_id": pid,
            "name": pid.split("/")[-1].replace("-", " "),
            "entwickler": entw_of(pid), "context": m.get("max_tokens") or 0,
            "in": round(inp, 4), "out": round(out, 4), "typ": ["text"],
            "url": "https://deepinfra.com/" + pid,
        }
    print(f"  {len(di_prices)} Modelle mit Preis", flush=True)
except Exception as e:
    print(f"  FEHLER DeepInfra: {e}", flush=True)

print("=== Novita AI ===", flush=True)
nv_prices = {}
try:
    # Öffentlicher Katalog; falls Novita einen Key verlangt, wird NOVITA_API_KEY genutzt.
    nv = json.loads(get("https://api.novita.ai/openai/v1/models", key=os.environ.get("NOVITA_API_KEY")))
    for m in nv.get("data", []):
        pid = m.get("id", "")
        try:
            # Novita gibt Preise in 0,0001 USD pro 1 Mio. Token an (3900 = 0,39 $)
            inp = float(m.get("input_token_price_per_m") or 0) / 10000
            out = float(m.get("output_token_price_per_m") or 0) / 10000
        except (TypeError, ValueError):
            continue
        if inp <= 0 and out <= 0:
            continue
        nv_prices[kanon(pid)] = {
            "anbieter": "Novita AI", "roh_id": pid, "name": m.get("title") or pid,
            "entwickler": entw_of(pid), "context": m.get("context_size") or 0,
            "in": round(inp, 4) if inp > 0 else None, "out": round(out, 4) if out > 0 else None,
            "typ": ["text"], "url": "https://novita.ai/pricing",
        }
    print(f"  {len(nv_prices)} Modelle mit Preis", flush=True)
except Exception as e:
    print(f"  FEHLER Novita: {e}  (ggf. NOVITA_API_KEY als Umgebungsvariable setzen)", flush=True)

print("=== CometAPI ===", flush=True)
cm_prices = {}
try:
    cm = json.loads(get("https://api.cometapi.com/api/models"))   # öffentlicher Katalog
    for m in cm.get("data", []):
        if m.get("upcoming"):
            continue
        pid = m.get("id", "")
        pr = m.get("pricing") or {}
        mtyp = str(m.get("model_type") or "text").lower()
        typ = [TYP_MAP.get(mtyp, "text")]
        eintrag = {
            "anbieter": "CometAPI", "roh_id": pid, "name": m.get("name") or pid,
            "entwickler": m.get("provider") or "", "context": m.get("context_length") or 0,
            "in": None, "out": None, "typ": typ, "url": "https://www.cometapi.com/pricing/",
        }
        if typ[0] in ("video", "bild"):
            eintrag.update(faehigkeiten(typ[0], (m.get("name") or "") + " " + pid, None, m.get("features"), m.get("tags")))
        waehrung = str(pr.get("currency") or "")
        inp, out = pr.get("input"), pr.get("output")
        if isinstance(inp, (int, float)) and inp > 0 and "token" in waehrung.lower():
            eintrag["in"] = round(float(inp), 4)
            if isinstance(out, (int, float)) and out > 0:
                eintrag["out"] = round(float(out), 4)
            cm_prices[kanon(pid)] = eintrag
        elif isinstance(pr.get("per_second"), (int, float)) and pr["per_second"] > 0:
            eintrag.update({"media": True, "media_preis": round(float(pr["per_second"]), 5), "einheit": "second"})
            cm_prices["media-" + kanon(pid)] = eintrag
        elif isinstance(pr.get("per_request"), (int, float)) and pr["per_request"] > 0:
            eintrag.update({"media": True, "media_preis": round(float(pr["per_request"]), 5),
                            "einheit": "image" if typ == ["bild"] else "generation"})
            cm_prices["media-" + kanon(pid)] = eintrag
    print(f"  {len(cm_prices)} Modelle mit Preis", flush=True)
except Exception as e:
    print(f"  FEHLER CometAPI: {e}", flush=True)

print("=== Kyma API ===", flush=True)
ky_prices = {}
try:
    ky = json.loads(get("https://kymaapi.com/v1/models"))
    for m in ky.get("data", []):
        pid = m.get("id", "")
        pr = m.get("pricing") or {}
        if str(pr.get("mode") or m.get("pricing_mode") or "") != "per-token":
            continue   # andere Abrechnungsarten (pro Bild/Sekunde) haben keine klare Einheit
        try:
            inp = float(pr.get("input") or 0)
            out = float(pr.get("output") or 0)
        except (TypeError, ValueError):
            continue
        if inp <= 0 and out <= 0:
            continue
        oms = m.get("output_modalities") or ["text"]
        ky_prices[kanon(pid)] = {
            "anbieter": "Kyma API", "roh_id": pid, "name": m.get("name") or pid,
            "entwickler": ENTW_MAP.get(str(m.get("owned_by") or "").lower(), m.get("owned_by") or ""),
            "context": m.get("context_window") or 0,
            "in": round(inp, 4) if inp > 0 else None, "out": round(out, 4) if out > 0 else None,
            "typ": [TYP_MAP[o] for o in oms if o in TYP_MAP] or ["text"],
            "url": "https://kymaapi.com",
        }
    print(f"  {len(ky_prices)} Modelle mit Preis", flush=True)
except Exception as e:
    print(f"  FEHLER Kyma: {e}", flush=True)

# ---------------- Zusammenbau ----------------
meta = {
    "erstellt": time.strftime("%Y-%m-%d %H:%M UTC", time.gmtime()),
    "quellen": {
        "OpenRouter": {"anbieter": "OpenRouter", "typ": "Aggregator", "auto": True},
        "UplinkSwitch": {"anbieter": "UplinkSwitch", "typ": "Reseller", "auto": True},
        "AnyModel": {"anbieter": "AnyModel", "typ": "Reseller", "auto": True,
                     "hinweis": "Bild/Video pro Einheit; Bildpreise teils geschätzt (coefficient × Referenzbild)"},
        "NanoGPT": {"anbieter": "NanoGPT", "typ": "Reseller", "auto": True},
        "Chutes": {"anbieter": "Chutes", "typ": "Reseller", "auto": True},
        "DeepInfra": {"anbieter": "DeepInfra", "typ": "Infrastruktur", "auto": True},
        "Novita AI": {"anbieter": "Novita AI", "typ": "Infrastruktur", "auto": True},
        "CometAPI": {"anbieter": "CometAPI", "typ": "Aggregator", "auto": True},
        "Kyma API": {"anbieter": "Kyma API", "typ": "Aggregator", "auto": True},
    },
    "hinweis": "Preise sind $/1M Token, Stand je Anbieter. Runde/Rate-Limits/Zahlungsarten koennen abweichen. Preise aendern sich laufend.",
}
payload = {"meta": meta, "openrouter": or_prices, "uplinkswitch": up_prices, "anymodel": am_prices,
           "nanogpt": ng_prices, "chutes": ch_prices, "deepinfra": di_prices,
           "novita": nv_prices, "cometapi": cm_prices, "kyma": ky_prices}

out_js = OUT / "data.js"

# ---------------- Absicherung für den automatischen Betrieb ----------------
# Fällt ein Anbieter aus (Fehler, Sperre, geänderte API) oder liefert er auffällig
# wenig Modelle, bleiben seine letzten bekannten Preise erhalten, statt dass er
# von der Website verschwindet. So geht nie eine "leere" Seite online.
alt = {}
if out_js.exists():
    try:
        roh = out_js.read_text(encoding="utf-8")
        alt = json.loads(roh[roh.index("=") + 1:].rstrip().rstrip(";"))
    except Exception as e:
        print(f"  (!) Alte Daten nicht lesbar: {e}", flush=True)
alt_stand = (alt.get("meta") or {}).get("erstellt", "?")
veraltet = dict((alt.get("meta") or {}).get("veraltet") or {})
for k in list(payload.keys()):
    if k == "meta":
        continue
    neu_n, alt_n = len(payload[k]), len(alt.get(k) or {})
    if alt_n and neu_n < 0.3 * alt_n:
        print(f"  (!) {k}: nur {neu_n} statt {alt_n} Modelle – behalte Daten vom {veraltet.get(k, alt_stand)}", flush=True)
        payload[k] = alt[k]
        veraltet.setdefault(k, alt_stand)
    else:
        veraltet.pop(k, None)
meta["veraltet"] = veraltet
if veraltet and all(k in veraltet for k, v in payload.items() if k != "meta" and v):
    meta["erstellt"] = alt_stand   # nichts wurde aktualisiert -> alten Stand anzeigen

# Kontextfenster überall als Zahl speichern (auch in übernommenen Altdaten)
for k, v in payload.items():
    if k != "meta":
        for e in v.values():
            if "context" in e:
                e["context"] = ctx_zahl(e["context"])

gesamt = sum(len(v) for k, v in payload.items() if k != "meta")
if gesamt == 0:
    print("FEHLER: keine Preisdaten – Abbruch, alte Datei bleibt unverändert.", flush=True)
    sys.exit(1)

# ---------------- Preisverlauf ----------------
# out/verlauf.json: je Anbieter+Modell das Datum der ersten Erfassung ("seit")
# und eine Liste [Datum, Hauptpreis], die nur bei Preisänderungen wächst.
def hauptpreis(v):
    for k in ("in", "price", "media_preis"):
        if isinstance(v.get(k), (int, float)):
            return v[k]
    return None

heute = time.strftime("%Y-%m-%d", time.gmtime())
vpfad = OUT / "verlauf.json"
try:
    verlauf = json.loads(vpfad.read_text(encoding="utf-8")) if vpfad.exists() else {}
except Exception:
    verlauf = {}
bekannt = verlauf.setdefault("_quellen", [])   # Anbieter, die schon einmal erfasst wurden
for q, eintraege in payload.items():
    if q == "meta" or q in veraltet or not eintraege:
        continue
    erste_erfassung = q not in bekannt            # dann ist nichts "neu", nur Ausgangsstand
    for k, v in eintraege.items():
        key = q + "|" + k
        preis = hauptpreis(v)
        h = verlauf.setdefault(key, {"seit": None if erste_erfassung else heute, "p": []})
        if preis is not None and (not h["p"] or h["p"][-1][1] != preis):
            if h["p"] and h["p"][-1][0] == heute:
                h["p"][-1][1] = preis
            else:
                h["p"].append([heute, preis])
    if erste_erfassung:
        bekannt.append(q)
for q, eintraege in payload.items():
    if q == "meta":
        continue
    for k, v in eintraege.items():
        h = verlauf.get(q + "|" + k) or {}
        if h.get("seit"):
            v["seit"] = h["seit"]
        if len(h.get("p") or []) > 1:
            v["vorher"] = h["p"][-2][1]       # letzter abweichender Preis
vpfad.write_text(json.dumps(verlauf, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
print(f"Preisverlauf: {len(verlauf) - 1} Einträge, erfasste Anbieter: {', '.join(bekannt)}")

# Öffentliche JSON-Schnittstelle (wird als /api/prices.json veröffentlicht)
(OUT / "prices.json").write_text(json.dumps(payload, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")

with open(out_js, "w", encoding="utf-8") as f:
    f.write("// Auto-generiert von build_data.py — nicht manuell bearbeiten.\n")
    f.write("window.API_DATEN = " + json.dumps(payload, ensure_ascii=False, indent=2) + ";\n")
print(f"\nGespeichert: {out_js} ({out_js.stat().st_size} Byte)")
print("Zusammenfassung: " + ", ".join(f"{k} {len(v)}" for k, v in payload.items() if k != "meta"))
