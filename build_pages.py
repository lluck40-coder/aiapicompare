#!/usr/bin/env python3
"""
build_pages.py — stellt die komplette Website in einem Ordner zusammen und erzeugt
die statischen SEO-Seiten aus out/data.js:

  /models/<modell>.html          eine Seite pro Modell (Englisch)
  /de|zh|ru/models/<modell>.html dieselbe Seite auf Deutsch, Chinesisch, Russisch
  /[de|zh|ru/]models/index.html  Verzeichnis aller Modelle A–Z
  /[de|zh|ru/]free.html          kostenlose Modelle
  /api/prices.json               öffentliche Daten-Schnittstelle
  /sitemap.xml                   für Google (mit Sprachvarianten)

Aufruf:  python build_pages.py _site        (GitHub-Workflow)
         python build_pages.py vorschau     (lokale Vorschau, dann vorschau/index.html öffnen)
"""
import json, re, sys, shutil, html, urllib.parse, math
import datetime as dt
from pathlib import Path
from collections import Counter, defaultdict

BASIS = Path(__file__).resolve().parent
ZIEL = Path(sys.argv[1] if len(sys.argv) > 1 else "vorschau").resolve()
DOMAIN = "https://aiapicompare.com/"
SPRACHEN = ["en", "de", "zh", "ru"]          # en liegt im Stammverzeichnis

STATISCH = ["index.html", "anbindung.html", "kosten.html","free.html", "bestenliste.html", "news.html", "bereiche.js",
            "finder.html", "preisindex.html", "einbetten.html", "methodik.html", "referenz.js",
            "impressum.html", "datenschutz.html",
            "style.css", "sprache.js", "theme.js", "config.js", "einwilligung.js", "favicon.svg", "favicon-32.png",
            "apple-touch-icon.png", "og-image.png", "robots.txt", "CNAME"]

# ------------------------------------------------------------------ Daten laden
def lade_js(pfad):
    roh = pfad.read_text(encoding="utf-8")
    return json.loads(roh[roh.index("=") + 1:].rstrip().rstrip(";"))

D = lade_js(BASIS / "out" / "data.js")
VERLAUF = {}
if (BASIS / "out" / "verlauf.json").exists():
    VERLAUF = json.loads((BASIS / "out" / "verlauf.json").read_text(encoding="utf-8"))
STAND = (D.get("meta") or {}).get("erstellt", "")
STAERKEN = {}
if (BASIS / "out" / "staerken.js").exists():
    try:
        STAERKEN = lade_js(BASIS / "out" / "staerken.js")
    except Exception:
        STAERKEN = {}
BEREICH_NAMEN = {}
if (BASIS / "bereiche.js").exists():
    for zeile in (BASIS / "bereiche.js").read_text(encoding="utf-8").splitlines():
        felder = dict(re.findall(r'(\w+):"([^"]*)"', zeile))
        if "k" in felder:
            BEREICH_NAMEN[felder["k"]] = felder

ANBIETER = {   # Name, Farbe, OpenAI-kompatible Base-URL, Umgebungsvariable
    "openrouter":   ("OpenRouter",   "#a78bfa", "https://openrouter.ai/api/v1", "OPENROUTER_API_KEY"),
    "uplinkswitch": ("UplinkSwitch", "#f472b6", "https://api.uplinkswitch.com/v1", "UPLINKSWITCH_API_KEY"),
    "anymodel":     ("AnyModel",     "#fbbf24", "https://anymodel.org/v1", "ANYMODEL_API_KEY"),
    "nanogpt":      ("NanoGPT",      "#34d399", "https://nano-gpt.com/api/v1", "NANOGPT_API_KEY"),
    "chutes":       ("Chutes",       "#f87171", "https://llm.chutes.ai/v1", "CHUTES_API_KEY"),
    "deepinfra":    ("DeepInfra",    "#60a5fa", "https://api.deepinfra.com/v1/openai", "DEEPINFRA_API_KEY"),
    "novita":       ("Novita AI",    "#2dd4bf", "https://api.novita.ai/openai/v1", "NOVITA_API_KEY"),
    "cometapi":     ("CometAPI",     "#fb923c", "https://api.cometapi.com/v1", "COMETAPI_KEY"),
    "kyma":         ("Kyma API",     "#c084fc", "https://kymaapi.com/v1", "KYMA_API_KEY"),
}

FAEH = {
    "t2v": ("📝", {"de": "Text → Video", "en": "Text → video", "zh": "文生视频", "ru": "Текст → видео"}),
    "start": ("⏮️", {"de": "Startbild (Bild → Video)", "en": "First frame (image → video)", "zh": "首帧（图生视频）", "ru": "Первый кадр"}),
    "ende": ("⏭️", {"de": "Endbild", "en": "Last frame", "zh": "尾帧", "ru": "Последний кадр"}),
    "ref": ("🧩", {"de": "Referenzbilder / Figuren", "en": "Reference images / characters", "zh": "参考图 / 角色", "ru": "Референсы / персонажи"}),
    "v2v": ("🎞️", {"de": "Video bearbeiten", "en": "Video editing", "zh": "视频编辑", "ru": "Редактирование видео"}),
    "motion": ("🕺", {"de": "Bewegung übertragen", "en": "Motion transfer", "zh": "动作迁移", "ru": "Перенос движения"}),
    "ton": ("🔊", {"de": "Mit Ton", "en": "Native audio", "zh": "原生音频", "ru": "Со звуком"}),
    "audio_in": ("🎤", {"de": "Audio-Eingabe / Lippensync", "en": "Audio input / lip-sync", "zh": "音频输入 / 口型同步", "ru": "Аудиовход / липсинк"}),
    "multishot": ("🎬", {"de": "Mehrere Szenen", "en": "Multi-shot", "zh": "多镜头", "ru": "Несколько сцен"}),
    "t2i": ("📝", {"de": "Text → Bild", "en": "Text → image", "zh": "文生图", "ru": "Текст → изображение"}),
    "edit": ("✏️", {"de": "Bild bearbeiten", "en": "Image editing", "zh": "图像编辑", "ru": "Редактирование изображений"}),
    "multiref": ("🗂️", {"de": "Mehrere Eingabebilder", "en": "Multiple input images", "zh": "多图输入", "ru": "Несколько входных изображений"}),
    "maske": ("🖌️", {"de": "Maske / Inpainting", "en": "Mask / inpainting", "zh": "蒙版 / 局部重绘", "ru": "Маска / инпейнтинг"}),
    "transparent": ("🔳", {"de": "Transparenter Hintergrund", "en": "Transparent background", "zh": "透明背景", "ru": "Прозрачный фон"}),
    "upscale": ("🔍", {"de": "Hochskalieren", "en": "Upscaling", "zh": "超分放大", "ru": "Апскейл"}),
    "outpaint": ("↔️", {"de": "Bild erweitern", "en": "Outpainting", "zh": "扩图", "ru": "Расширение изображения"}),
    "4k": ("4K", {"de": "Bis 4K", "en": "Up to 4K", "zh": "最高 4K", "ru": "До 4K"}),
    "unzensiert": ("🔓", {"de": "Ohne Inhaltsfilter", "en": "No content filter", "zh": "无内容过滤", "ru": "Без фильтра контента"}),
}

T = {
"en": dict(htmllang="en", nav_finder="Model finder", fuss_anb="Providers", fuss_index="AI price index", fuss_widget="Embed widget", fuss_methodik="How we compare", nav_best="Leaderboard", nav_news="News", nav_vergleich="Price comparison", nav_kosten="Cost calculator", nav_gratis="Free models",
  nav_anbindung="Setup & integration", impressum="Imprint", datenschutz="Privacy", alle_modelle="All models", api="Data as JSON",
  titel1="{name} API pricing & capabilities | aiapicompare", lead_flat="{name} is available from {n} provider(s). Cheapest: <b>{prov}</b> at <b>{inp}</b> per 1M tokens (flat rate for input and output).",
  titel="{name} API pricing: {n} providers compared | aiapicompare",
  desc_text="{name} API price comparison: cheapest at {prov} with {inp} per 1M input tokens and {out} per 1M output tokens. Compare {n} providers, context window and setup.",
  desc_media="{name} API price comparison: from {preis} at {prov}. Compare {n} providers and capabilities.",
  h1="{name}: API pricing compared",
  lead_text="{name} is available from {n} provider(s). Cheapest: <b>{prov}</b> at <b>{inp}</b> per 1M input tokens and <b>{out}</b> per 1M output tokens.",
  lead_media="{name} is available from {n} provider(s). Cheapest: <b>{prov}</b> from <b>{preis}</b>.",
  ctx="Context window: up to {ctx} tokens.", gratis_bei="Free to use at {prov}.", entw="Developer: {e}.",
  th_anbieter="Provider", th_in="Input $/1M", th_out="Output $/1M", th_ctx="Context", th_preis="Price", th_faeh="Capabilities",
  zum="Go to provider ↗", einrichten="Set up", faeh_titel="Capabilities", arena_titel="Strengths in the Arena leaderboard", platz="Rank {p}", arena_quelle='Rankings: Arena (arena.ai, formerly LMArena), dataset <a href="{ds}" target="_blank" rel="noopener">lmarena-ai/leaderboard-dataset</a>, licensed under <a href="{lz}" target="_blank" rel="noopener">CC BY 4.0</a>, as of {stand}. Excerpt; variants with different reasoning effort merged and matched to our prices by aiapicompare. Not affiliated with Arena and not a recommendation.', verlauf_titel="Price history (cheapest provider)",
  verlauf_start="Price history is recorded daily – the chart appears after the first price change.", code_titel="Quick start with {prov}",
  verwandt="More models from {e}", faq_titel="FAQ",
  q1="Where is {name} cheapest?", a1="Currently at {prov} ({preis}). Prices are updated daily; the provider’s website is authoritative.",
  q2="How do I use {name} in my tools?", a2="All listed providers offer an OpenAI-compatible API. See the <a href=\"{link}\">setup guide</a> for Hermes Agent, VS Code, Cursor and more.",
  stand="Data as of {d}. Prices in USD, excluding taxes. No guarantee.", ranking="Sorted by price only – there are no paid placements.",
  gratis="free", pro5s="per 5 s clip", ab="from", hallo="Hello!",
  einheit={"image": "/image", "second": "/s", "generation": "/generation", "minute": "/min", "1k_chars": "/1k chars", "1k_bytes": "/1 kB"},
  free_titel="Free AI models via API: {n} models | aiapicompare", free_h1="Free AI models via API",
  free_desc="{n} AI models you can currently use via API for free – with context window and provider. Updated daily.",
  free_lead="These models can currently be used via API at no cost. Free models usually have strict rate limits, and providers may use requests to improve their services – check the provider’s terms before sending sensitive data.",
  free_leer="There are no free models in the current data. The list is updated daily.",
  idx_titel="All AI models & API prices A–Z | aiapicompare", idx_h1="All AI models A–Z",
  idx_desc="API prices for {n} AI models from {p} providers – text, image and video models, updated daily.",
  idx_lead="{n} models from {p} providers. Click a model for the full price comparison.",
  th_modell="Model", th_anz="Providers", th_ab="From", zurueck="← Back to the price comparison"),
"de": dict(htmllang="de", nav_finder="Modell-Finder", fuss_anb="Anbieter", fuss_index="KI-Preisindex", fuss_widget="Widget einbetten", fuss_methodik="So vergleichen wir", nav_best="Bestenliste", nav_news="Neuigkeiten", nav_vergleich="Preisvergleich", nav_kosten="Kostenrechner", nav_gratis="Kostenlose Modelle",
  nav_anbindung="Anbindung & Einrichtung", impressum="Impressum", datenschutz="Datenschutz", alle_modelle="Alle Modelle", api="Daten als JSON",
  titel1="{name} API-Preis & Fähigkeiten | aiapicompare", lead_flat="{name} ist bei {n} Anbieter(n) verfügbar. Am günstigsten: <b>{prov}</b> mit <b>{inp}</b> pro 1 Mio. Token (Pauschalpreis für Input und Output).",
  titel="{name} API-Preise: {n} Anbieter im Vergleich | aiapicompare",
  desc_text="{name} API-Preisvergleich: am günstigsten bei {prov} mit {inp} pro 1 Mio. Input-Token und {out} pro 1 Mio. Output-Token. {n} Anbieter, Kontextfenster und Einrichtung im Vergleich.",
  desc_media="{name} API-Preisvergleich: ab {preis} bei {prov}. {n} Anbieter und Fähigkeiten im Vergleich.",
  h1="{name}: API-Preise im Vergleich",
  lead_text="{name} ist bei {n} Anbieter(n) verfügbar. Am günstigsten: <b>{prov}</b> mit <b>{inp}</b> pro 1 Mio. Input-Token und <b>{out}</b> pro 1 Mio. Output-Token.",
  lead_media="{name} ist bei {n} Anbieter(n) verfügbar. Am günstigsten: <b>{prov}</b> ab <b>{preis}</b>.",
  ctx="Kontextfenster: bis {ctx} Token.", gratis_bei="Kostenlos nutzbar bei {prov}.", entw="Entwickler: {e}.",
  th_anbieter="Anbieter", th_in="Input $/1M", th_out="Output $/1M", th_ctx="Kontext", th_preis="Preis", th_faeh="Fähigkeiten",
  zum="Zum Anbieter ↗", einrichten="Einrichten", faeh_titel="Fähigkeiten", arena_titel="Stärken laut Arena-Bestenliste", platz="Platz {p}", arena_quelle='Platzierungen: Arena (arena.ai, ehemals LMArena), Datensatz <a href="{ds}" target="_blank" rel="noopener">lmarena-ai/leaderboard-dataset</a>, lizenziert unter <a href="{lz}" target="_blank" rel="noopener">CC BY 4.0</a>, Stand {stand}. Auszug; Varianten mit unterschiedlichem Denkaufwand zusammengefasst und unseren Preisen zugeordnet durch aiapicompare. Keine Verbindung zu Arena und keine Empfehlung.', verlauf_titel="Preisverlauf (günstigster Anbieter)",
  verlauf_start="Der Preisverlauf wird täglich aufgezeichnet – das Diagramm erscheint nach der ersten Preisänderung.", code_titel="Schnellstart mit {prov}",
  verwandt="Weitere Modelle von {e}", faq_titel="Häufige Fragen",
  q1="Wo ist {name} am günstigsten?", a1="Derzeit bei {prov} ({preis}). Die Preise werden täglich aktualisiert; maßgeblich ist die Seite des Anbieters.",
  q2="Wie nutze ich {name} in meinen Tools?", a2="Alle aufgeführten Anbieter bieten eine OpenAI-kompatible API. Die <a href=\"{link}\">Einrichtungsanleitung</a> zeigt Hermes Agent, VS Code, Cursor und mehr.",
  stand="Stand der Daten: {d}. Preise in USD, ohne Steuern. Ohne Gewähr.", ranking="Sortiert nur nach Preis – es gibt keine bezahlten Platzierungen.",
  gratis="kostenlos", pro5s="pro 5-s-Clip", ab="ab", hallo="Hallo!",
  einheit={"image": "/Bild", "second": "/s", "generation": "/Generierung", "minute": "/Min.", "1k_chars": "/1k Zeichen", "1k_bytes": "/1 kB"},
  free_titel="Kostenlose KI-Modelle per API: {n} Modelle | aiapicompare", free_h1="Kostenlose KI-Modelle per API",
  free_desc="{n} KI-Modelle, die du aktuell kostenlos per API nutzen kannst – mit Kontextfenster und Anbieter. Täglich aktualisiert.",
  free_lead="Diese Modelle lassen sich derzeit kostenlos per API nutzen. Kostenlose Modelle haben meist strenge Ratenlimits, und Anbieter dürfen Anfragen teils zur Verbesserung ihrer Dienste verwenden – vor sensiblen Daten die Bedingungen des Anbieters prüfen.",
  free_leer="In den aktuellen Daten gibt es keine kostenlosen Modelle. Die Liste wird täglich aktualisiert.",
  idx_titel="Alle KI-Modelle & API-Preise von A–Z | aiapicompare", idx_h1="Alle KI-Modelle von A–Z",
  idx_desc="API-Preise für {n} KI-Modelle von {p} Anbietern – Text-, Bild- und Videomodelle, täglich aktualisiert.",
  idx_lead="{n} Modelle von {p} Anbietern. Ein Klick auf ein Modell zeigt den vollständigen Preisvergleich.",
  th_modell="Modell", th_anz="Anbieter", th_ab="Ab", zurueck="← Zurück zum Preisvergleich"),
"zh": dict(htmllang="zh-CN", nav_finder="模型推荐", fuss_anb="提供商", fuss_index="AI 价格指数", fuss_widget="嵌入小组件", fuss_methodik="比较方法", nav_best="排行榜", nav_news="动态", nav_vergleich="价格对比", nav_kosten="成本计算器", nav_gratis="免费模型",
  nav_anbindung="接入与配置", impressum="网站信息", datenschutz="隐私政策", alle_modelle="全部模型", api="JSON 数据",
  titel1="{name} API 价格与功能 | aiapicompare", lead_flat="{name} 共有 {n} 家提供商。最便宜：<b>{prov}</b>，每百万 Token <b>{inp}</b>（输入输出统一价格）。",
  titel="{name} API 价格：{n} 家提供商对比 | aiapicompare",
  desc_text="{name} API 价格对比：{prov} 最便宜，每百万输入 Token {inp}，每百万输出 Token {out}。对比 {n} 家提供商、上下文窗口和接入方式。",
  desc_media="{name} API 价格对比：{prov} 起价 {preis}。对比 {n} 家提供商及功能。",
  h1="{name}：API 价格对比",
  lead_text="{name} 共有 {n} 家提供商。最便宜：<b>{prov}</b>，每百万输入 Token <b>{inp}</b>，每百万输出 Token <b>{out}</b>。",
  lead_media="{name} 共有 {n} 家提供商。最便宜：<b>{prov}</b>，<b>{preis}</b> 起。",
  ctx="上下文窗口：最高 {ctx} Token。", gratis_bei="可在 {prov} 免费使用。", entw="开发商：{e}。",
  th_anbieter="提供商", th_in="输入 $/1M", th_out="输出 $/1M", th_ctx="上下文", th_preis="价格", th_faeh="功能",
  zum="前往提供商 ↗", einrichten="配置", faeh_titel="功能", arena_titel="Arena 排行榜中的优势", platz="第 {p} 名", arena_quelle='排名来源：Arena（arena.ai，原 LMArena），数据集 <a href="{ds}" target="_blank" rel="noopener">lmarena-ai/leaderboard-dataset</a>，采用 <a href="{lz}" target="_blank" rel="noopener">CC BY 4.0</a> 许可，数据日期 {stand}。摘录；不同推理强度的版本已由 aiapicompare 合并并与我们的价格对应。与 Arena 无关联，亦非推荐。', verlauf_titel="价格走势（最便宜的提供商）",
  verlauf_start="价格走势每日记录——首次价格变动后显示图表。", code_titel="使用 {prov} 快速开始",
  verwandt="{e} 的更多模型", faq_titel="常见问题",
  q1="{name} 在哪里最便宜？", a1="目前是 {prov}（{preis}）。价格每日更新，以提供商网站为准。",
  q2="如何在我的工具中使用 {name}？", a2="所列提供商均提供 OpenAI 兼容 API。请参阅 Hermes Agent、VS Code、Cursor 等的<a href=\"{link}\">接入指南</a>。",
  stand="数据时间：{d}。价格单位为美元，不含税。仅供参考。", ranking="仅按价格排序——不存在付费排名。",
  gratis="免费", pro5s="每 5 秒片段", ab="起", hallo="你好！",
  einheit={"image": "/张", "second": "/秒", "generation": "/次", "minute": "/分钟", "1k_chars": "/千字符", "1k_bytes": "/1 kB"},
  free_titel="免费 AI 模型 API：{n} 个模型 | aiapicompare", free_h1="可免费调用的 AI 模型（API）",
  free_desc="目前可通过 API 免费使用的 {n} 个 AI 模型，含上下文窗口和提供商。每日更新。",
  free_lead="以下模型目前可通过 API 免费使用。免费模型通常有严格的速率限制，提供商可能会将请求用于改进服务——发送敏感数据前请查看提供商条款。",
  free_leer="当前数据中没有免费模型。列表每日更新。",
  idx_titel="全部 AI 模型及 API 价格（A–Z）| aiapicompare", idx_h1="全部 AI 模型（A–Z）",
  idx_desc="{p} 家提供商的 {n} 个 AI 模型的 API 价格——文本、图像和视频模型，每日更新。",
  idx_lead="来自 {p} 家提供商的 {n} 个模型。点击模型查看完整价格对比。",
  th_modell="模型", th_anz="提供商", th_ab="起价", zurueck="← 返回价格对比"),
"ru": dict(htmllang="ru", nav_finder="Подбор модели", fuss_anb="Поставщики", fuss_index="Индекс цен AI", fuss_widget="Виджет для сайта", fuss_methodik="Как мы сравниваем", nav_best="Рейтинг", nav_news="Новости", nav_vergleich="Сравнение цен", nav_kosten="Калькулятор", nav_gratis="Бесплатные модели",
  nav_anbindung="Подключение", impressum="Импрессум", datenschutz="Конфиденциальность", alle_modelle="Все модели", api="Данные в JSON",
  titel1="{name}: цена API и возможности | aiapicompare", lead_flat="{name} доступна у {n} поставщиков. Дешевле всего: <b>{prov}</b> — <b>{inp}</b> за 1 млн токенов (единая цена за вход и выход).",
  titel="{name}: цены API у {n} поставщиков | aiapicompare",
  desc_text="Сравнение цен API {name}: дешевле всего у {prov} — {inp} за 1 млн входных и {out} за 1 млн выходных токенов. {n} поставщиков, контекст и подключение.",
  desc_media="Сравнение цен API {name}: от {preis} у {prov}. {n} поставщиков и возможности.",
  h1="{name}: сравнение цен API",
  lead_text="{name} доступна у {n} поставщиков. Дешевле всего: <b>{prov}</b> — <b>{inp}</b> за 1 млн входных и <b>{out}</b> за 1 млн выходных токенов.",
  lead_media="{name} доступна у {n} поставщиков. Дешевле всего: <b>{prov}</b> от <b>{preis}</b>.",
  ctx="Контекстное окно: до {ctx} токенов.", gratis_bei="Бесплатно у {prov}.", entw="Разработчик: {e}.",
  th_anbieter="Поставщик", th_in="Вход $/1M", th_out="Выход $/1M", th_ctx="Контекст", th_preis="Цена", th_faeh="Возможности",
  zum="К поставщику ↗", einrichten="Настроить", faeh_titel="Возможности", arena_titel="Сильные стороны в рейтинге Arena", platz="Место {p}", arena_quelle='Места: Arena (arena.ai, ранее LMArena), набор данных <a href="{ds}" target="_blank" rel="noopener">lmarena-ai/leaderboard-dataset</a>, лицензия <a href="{lz}" target="_blank" rel="noopener">CC BY 4.0</a>, данные на {stand}. Выборка; варианты с разным уровнем рассуждения объединены и сопоставлены с нашими ценами aiapicompare. Не связано с Arena и не является рекомендацией.', verlauf_titel="История цен (самый дешёвый поставщик)",
  verlauf_start="История цен записывается ежедневно – график появится после первого изменения цены.", code_titel="Быстрый старт с {prov}",
  verwandt="Другие модели {e}", faq_titel="Вопросы и ответы",
  q1="Где {name} дешевле всего?", a1="Сейчас у {prov} ({preis}). Цены обновляются ежедневно; действует цена на сайте поставщика.",
  q2="Как использовать {name} в своих инструментах?", a2="Все поставщики предлагают API, совместимый с OpenAI. См. <a href=\"{link}\">руководство по подключению</a> для Hermes Agent, VS Code, Cursor и других.",
  stand="Данные от {d}. Цены в USD без налогов. Без гарантии.", ranking="Сортировка только по цене – платных размещений нет.",
  gratis="бесплатно", pro5s="за клип 5 с", ab="от", hallo="Привет!",
  einheit={"image": "/изобр.", "second": "/с", "generation": "/генерация", "minute": "/мин", "1k_chars": "/1k зн.", "1k_bytes": "/1 кБ"},
  free_titel="Бесплатные AI-модели по API: {n} моделей | aiapicompare", free_h1="Бесплатные AI-модели по API",
  free_desc="{n} AI-моделей, которые сейчас можно бесплатно использовать по API, с контекстом и поставщиком. Обновляется ежедневно.",
  free_lead="Эти модели сейчас можно использовать по API бесплатно. У бесплатных моделей обычно строгие лимиты, а поставщики могут использовать запросы для улучшения сервисов – проверьте условия перед отправкой конфиденциальных данных.",
  free_leer="В текущих данных нет бесплатных моделей. Список обновляется ежедневно.",
  idx_titel="Все AI-модели и цены API от A до Z | aiapicompare", idx_h1="Все AI-модели от A до Z",
  idx_desc="Цены API для {n} AI-моделей от {p} поставщиков – текст, изображения и видео, ежедневное обновление.",
  idx_lead="{n} моделей от {p} поставщиков. Нажмите на модель, чтобы увидеть полное сравнение цен.",
  th_modell="Модель", th_anz="Поставщики", th_ab="От", zurueck="← Назад к сравнению цен"),
}

# ------------------------------------------------------------------ Hilfen
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


def esc(s):
    return html.escape(str(s), quote=True)

def fmt(n):
    if n is None:
        return "—"
    return "$" + (f"{n:.0f}" if n >= 100 else f"{n:.2f}" if n >= 1 else f"{n:.3f}" if n >= 0.01 else f"{n:.4f}")

def fmt_ctx(n):
    if not n:
        return "—"
    if n >= 1_000_000:
        return (f"{n / 1_000_000:.2f}".rstrip("0").rstrip(".")) + "M"
    return f"{round(n / 1000)}K" if n >= 1000 else str(n)

def slug(k):
    s = re.sub(r"^media-", "", str(k).lower())
    s = re.sub(r"[^a-z0-9-]+", "-", s)
    return re.sub(r"-+", "-", s).strip("-")

def name_sauber(n):
    return re.sub(r"^[^:]{1,30}:\s*", "", n or "").strip()

# ------------------------------------------------------------------ Zeilen wie im Preisvergleich
ZEILEN = []
for q, (qname, farbe, base, env) in ANBIETER.items():
    for k, v in (D.get(q) or {}).items():
        inp = v.get("in") if isinstance(v.get("in"), (int, float)) else None
        out = v.get("out") if isinstance(v.get("out"), (int, float)) else None
        ab = v.get("price") if inp is None and isinstance(v.get("price"), (int, float)) else None
        mp = v.get("media_preis") if isinstance(v.get("media_preis"), (int, float)) else None
        typ = v.get("typ") or ["text"]
        z = dict(q=q, quelle=qname, farbe=farbe, kanon=k, slug=slug(re.sub(r":free$", "", k)), name=v.get("name") or v.get("roh_id") or k,
                 roh=v.get("roh_id") or k, entw=v.get("entwickler") or "", ctx=ctx_zahl(v.get("context")),
                 inp=inp, out=out, ab=ab, mp=mp, einheit=v.get("einheit") or "", typ=typ,
                 faeh=v.get("faeh") or [], aufl=v.get("aufl") or "", dauer=v.get("dauer") or 0,
                 dauer_fix=v.get("dauer_fix") or 0, gratis=bool(v.get("gratis")), url=v.get("url") or "")
        if not z["url"] and q == "openrouter":
            z["url"] = "https://openrouter.ai/" + z["roh"]
        z["ps"] = None
        if "video" in typ and mp is not None and inp is None:
            if z["einheit"] == "second":
                z["ps"] = mp
            elif z["einheit"] == "generation" and z["dauer_fix"]:
                z["ps"] = mp / z["dauer_fix"]
        z["preis"] = (z["ps"] if z["ps"] is not None else inp if inp is not None else ab if ab is not None
                      else mp if mp is not None else float("inf"))
        z["media"] = inp is None and ab is None and mp is not None
        if not z["slug"]:
            continue
        ZEILEN.append(z)

GRUPPEN = defaultdict(list)
for z in ZEILEN:
    GRUPPEN[z["slug"]].append(z)

# ------------------------------------------------------------------ Referenzpreis
# Gleiche Regeln wie referenz.js (Browser) – Erklärung auf methodik.html.
GESCHLOSSEN = re.compile(r"^(claude|gpt-(?!oss)|chatgpt|o[1-9](-|$)|gemini|grok|nova-|sonar)")
GRENZE_GESCHLOSSEN, GRENZE_OFFEN, MIN_REF_OFFEN, ALT_TAGE = 0.5, 0.2, 0.2, 3
VARIANTE = re.compile(r"-(uncensored|thinking|fast|highspeed|nitro)$")   # Varianten geschlossener Modelle → Grundmodell

def _zahl(x):
    return isinstance(x, (int, float)) and not isinstance(x, bool) and math.isfinite(x)

def _misch(v):
    if _zahl(v.get("in")) and _zahl(v.get("out")):
        return (3 * v["in"] + v["out"]) / 4
    if _zahl(v.get("in")):
        return v["in"]
    if _zahl(v.get("price")):
        return v["price"]
    return None

def _median(a):
    a = sorted(a)
    n, h = len(a), len(a) // 2
    return a[h] if n % 2 else (a[h - 1] + a[h]) / 2

REF, REF_ERG, _EIGEN = {}, {}, {}
_pro_basis = defaultdict(list)
for _q in sorted(k for k in D if k != "meta"):
    for _k, _v in (D.get(_q) or {}).items():
        if not isinstance(_v, dict) or _k.startswith("media-") or _v.get("gratis") or _v.get("media"):
            continue
        if not (_zahl(_v.get("in")) or _zahl(_v.get("price"))):
            continue
        _m = _misch(_v)
        if _m is None or not _m > 0:
            continue
        _pro_basis[re.sub(r":free$", "", _k)].append(dict(q=_q, k=_k, v=_v, m=_m))
for _b, _l in _pro_basis.items():
    _zu = bool(GESCHLOSSEN.match(_b))
    _or = None
    for _x in _l:
        if _x["q"] == "openrouter" and (_or is None or _x["m"] < _or["m"]):
            _or = _x
    _or_ref = (dict(inp=_or["v"]["in"] if _zahl(_or["v"].get("in")) else None,
                    out=_or["v"]["out"] if _zahl(_or["v"].get("out")) else None, m=_or["m"], src="openrouter") if _or else None)
    _med_ref = dict(inp=None, out=None, m=_median([x["m"] for x in _l]), src="median") if len(_l) >= 3 else None
    _r = (_or_ref or _med_ref) if _zu else (_med_ref or _or_ref)
    if not _r or not _r["m"] > 0:
        continue
    _r["geschlossen"] = _zu
    _r["via"] = ""
    _EIGEN[_b] = _r
for _b in _pro_basis:
    if _b in _EIGEN:
        REF[_b] = _EIGEN[_b]
        continue
    _x = _b
    while VARIANTE.search(_x):
        _x = VARIANTE.sub("", _x)
        _g = _EIGEN.get(_x)
        if _g and _g["geschlossen"]:
            REF[_b] = dict(inp=_g["inp"], out=_g["out"], m=_g["m"], src=_g["src"], geschlossen=True, via=_x)
            break
for _b, _l in _pro_basis.items():
    _r = REF.get(_b)
    if not _r:
        continue
    _zu = _r["geschlossen"]
    _grenze = GRENZE_GESCHLOSSEN if _zu else (GRENZE_OFFEN if _r["m"] >= MIN_REF_OFFEN else 0)
    for _x in _l:
        _v = _x["v"]
        if _r["src"] == "openrouter" and _zahl(_v.get("in")) and _zahl(_v.get("out")) and _r["inp"] is not None and _r["out"] is not None:
            _ratio = _x["m"] / _r["m"]
        elif _r["src"] == "openrouter" and _zahl(_v.get("in")) and not _zahl(_v.get("out")) and _r["inp"] is not None:
            _ratio = _v["in"] / _r["inp"]
        else:
            _ratio = _x["m"] / _r["m"]
        if not _ratio > 0 or not math.isfinite(_ratio):
            continue
        REF_ERG[(_x["q"], _x["k"])] = dict(ratio=_ratio, pct=math.floor((1 - _ratio) * 100 + 0.5), auff=_ratio < _grenze, src=_r["src"])

ALT = {}
_meta = D.get("meta") or {}
try:
    _stand = dt.date.fromisoformat(str(_meta.get("erstellt", ""))[:10])
except ValueError:
    _stand = None
for _q, _seit in (_meta.get("veraltet") or {}).items():
    _s = str(_seit or "")[:10]
    try:
        _tage = (_stand - dt.date.fromisoformat(_s)).days if _stand else 0
    except ValueError:
        _tage = 0
    ALT[_q] = dict(seit=_s, tage=_tage, zu_alt=_tage > ALT_TAGE)

for z in ZEILEN:
    e = REF_ERG.get((z["q"], z["kanon"]))
    z["ref"] = e
    z["auff"] = bool(e and e["auff"])
    z["alt"] = ALT.get(z["q"])
    z["ok"] = not z["auff"] and not (z["alt"] and z["alt"]["zu_alt"])
    z["batch"] = z["kanon"].endswith(":batch") or "(batch)" in (z["name"] or "").lower()

def _fmt_ref(n):
    return "$" + (f"{n:.0f}" if n >= 100 else f"{n:.2f}" if n >= 1 else f"{n:.3f}" if n >= 0.01 else f"{n:.4f}")

REF_T = {
    "de": dict(tag="⚠ {p} % unter Referenz",
               titel="Dieser Preis liegt {p} % unter dem Referenzpreis ({ref}). Wir können nicht nachvollziehen, wie er zustande kommt, und nicht prüfen, welches Modell tatsächlich geliefert wird. Vorher Bedingungen, Datenschutz und Zuverlässigkeit prüfen und mit kleinem Guthaben testen.",
               alt_tag="⏱ Stand {d}", alt_titel="Der letzte Abruf bei diesem Anbieter ist fehlgeschlagen – angezeigt werden die Preise vom {d}.",
               batch_titel="Batch-Variante: in der Regel günstiger, Anfragen werden aber gesammelt und verzögert verarbeitet – meist nicht für Chat oder Echtzeit geeignet.",
               ref="Referenzpreis", pro_io="pro 1 Mio. Token (Input / Output)", pro_misch="pro 1 Mio. Token (gemischt 3:1)",
               src_or="OpenRouter", src_or_zu="OpenRouter – bei diesem Modell in der Regel der Listenpreis des Herstellers", src_med="Median aller Anbieter", via="Grundmodell",
               trenner="Weit unter dem Referenzpreis – bitte vorher prüfen", mehr="So vergleichen wir →",
               melden="Preis falsch? Melden", alt_anb="Der letzte Abruf bei {p} ist fehlgeschlagen – angezeigt werden die Preise vom {d}."),
    "en": dict(tag="⚠ {p}% below reference",
               titel="This price is {p}% below the reference price ({ref}). We cannot tell how it is possible or verify which model is actually served. Check terms, privacy and reliability first and test with a small balance.",
               alt_tag="⏱ as of {d}", alt_titel="The last update from this provider failed – prices shown are from {d}.",
               batch_titel="Batch variant: usually cheaper, but requests are collected and processed with a delay – usually not suitable for chat or real-time use.",
               ref="Reference price", pro_io="per 1M tokens (input / output)", pro_misch="per 1M tokens (blended 3:1)",
               src_or="OpenRouter", src_or_zu="OpenRouter – for this model usually the vendor's list price", src_med="median of all providers", via="base model",
               trenner="Far below the reference price – please check first", mehr="How we compare →",
               melden="Wrong price? Report it", alt_anb="The last update from {p} failed – prices shown are from {d}."),
    "zh": dict(tag="⚠ 低于参考价 {p}%",
               titel="此价格比参考价低 {p}%（{ref}）。我们无法确认该价格如何实现，也无法核实实际提供的是哪个模型。使用前请先查看条款、隐私政策和可靠性，并先用少量余额测试。",
               alt_tag="⏱ 数据日期 {d}", alt_titel="该提供商最近一次更新失败——显示的是 {d} 的价格。",
               batch_titel="批处理版本：通常更便宜，但请求会被汇总并延迟处理——一般不适合聊天或实时场景。",
               ref="参考价", pro_io="每百万 Token（输入 / 输出）", pro_misch="每百万 Token（按 3:1 混合）",
               src_or="OpenRouter", src_or_zu="OpenRouter——对该模型通常即厂商官方价格", src_med="所有提供商的中位数", via="基础模型",
               trenner="远低于参考价——使用前请先核实", mehr="我们的比较方法 →",
               melden="价格有误？告诉我们", alt_anb="{p} 最近一次更新失败——显示的是 {d} 的价格。"),
    "ru": dict(tag="⚠ на {p} % ниже эталона",
               titel="Эта цена на {p} % ниже эталонной ({ref}). Мы не можем объяснить, как она возможна, и проверить, какая модель реально используется. Перед использованием проверьте условия, конфиденциальность и надёжность и протестируйте с небольшим балансом.",
               alt_tag="⏱ на {d}", alt_titel="Последнее обновление у этого поставщика не удалось – показаны цены на {d}.",
               batch_titel="Пакетный вариант: обычно дешевле, но запросы собираются и обрабатываются с задержкой – как правило, не подходит для чата и работы в реальном времени.",
               ref="Эталонная цена", pro_io="за 1 млн токенов (вход / выход)", pro_misch="за 1 млн токенов (смешанная 3:1)",
               src_or="OpenRouter", src_or_zu="OpenRouter – для этой модели обычно прайс производителя", src_med="медиана всех поставщиков", via="базовая модель",
               trenner="Намного ниже эталонной цены – проверьте заранее", mehr="Как мы сравниваем →",
               melden="Цена неверна? Сообщите нам", alt_anb="Последнее обновление у {p} не удалось – показаны цены на {d}."),
}

def ref_datum(d, lang):
    m = re.match(r"^(\d{4})-(\d\d)-(\d\d)", d or "")
    if not m:
        return d or ""
    return f"{m[3]}.{m[2]}.{m[1]}" if lang in ("de", "ru") else f"{m[1]}-{m[2]}-{m[3]}"

def ref_text(basis, lang):
    r, t = REF.get(re.sub(r":free$", "", basis)), REF_T[lang]
    if not r:
        return ""
    preis = (f'{_fmt_ref(r["inp"])} / {_fmt_ref(r["out"])} {t["pro_io"]}' if r["inp"] is not None and r["out"] is not None
             else f'{_fmt_ref(r["m"])} {t["pro_misch"]}')
    src = t["src_med"] if r["src"] == "median" else (t["src_or_zu"] if r["geschlossen"] else t["src_or"])
    return f"{preis}, {src}" + (f' ({t["via"]}: {r["via"]})' if r["via"] else "")

def ref_tags(z, lang):
    t, h = REF_T[lang], ""
    if z["auff"]:
        h += (f'<span class="tag warn" title="{esc(t["titel"].format(p=z["ref"]["pct"], ref=ref_text(z["kanon"], lang)))}">'
              f'{esc(t["tag"].format(p=z["ref"]["pct"]))}</span>')
    if z["alt"]:
        d = ref_datum(z["alt"]["seit"], lang)
        h += f'<span class="tag alt" title="{esc(t["alt_titel"].format(d=d))}">{esc(t["alt_tag"].format(d=d))}</span>'
    if z["batch"]:
        h += f'<span class="tag batch" title="{esc(t["batch_titel"])}">Batch</span>'
    return h

def gruppen_info(slug_, liste):
    namen = Counter(name_sauber(z["name"]) for z in liste)
    name = sorted(namen.items(), key=lambda x: (-x[1], -(" " in x[0]), -sum(c.isupper() for c in x[0]), len(x[0])))[0][0]
    entw = Counter(z["entw"] for z in liste if z["entw"]).most_common(1)
    liste = sorted(liste, key=lambda z: (z["preis"], z["quelle"]))
    return dict(slug=slug_, name=name or slug_, entw=entw[0][0] if entw else "", zeilen=liste,
                billig=liste[0], billig_ok=next((z for z in liste if z["ok"]), liste[0]), ctx=max((z["ctx"] for z in liste), default=0),
                media=all(z["media"] for z in liste), anbieter=len({z["q"] for z in liste}),
                gratis=[z for z in liste if z["gratis"]])

INFOS = {s: gruppen_info(s, l) for s, l in GRUPPEN.items()}

def preis_text(z, t):
    if z["gratis"]:
        return t["gratis"]
    if z["ps"] is not None:
        return f'{fmt(z["ps"])}{t["einheit"]["second"]} (≈ {fmt(z["ps"] * 5)} {t["pro5s"]})'
    if z["inp"] is not None:
        return f'{fmt(z["inp"])} / 1M'
    if z["ab"] is not None:
        return f'{t["ab"]} {fmt(z["ab"])} / 1M'
    if z["mp"] is not None:
        return f'{fmt(z["mp"])}{t["einheit"].get(z["einheit"], "")}'
    return "—"

# ------------------------------------------------------------------ Seitengerüst
def pfad(lang, rest):
    return ("" if lang == "en" else lang + "/") + rest

def kopf(lang, rel, titel, desc, rest, alternativen=True):
    t = T[lang]
    alt = ""
    if alternativen:
        alt = "".join(f'<link rel="alternate" hreflang="{T[l]["htmllang"]}" href="{DOMAIN}{pfad(l, rest)}">\n' for l in SPRACHEN)
        alt += f'<link rel="alternate" hreflang="x-default" href="{DOMAIN}{rest}">\n'
    kurz = {"en": "EN", "de": "DE", "zh": "中文", "ru": "RU"}
    sprachlinks = "".join('<a class="btn' + (" active" if l == lang else "") + '" data-setlang="' + l + '" href="' + rel + pfad(l, rest) + '">' + kurz[l] + "</a>" for l in SPRACHEN)
    return f'''<!DOCTYPE html>
<html lang="{t["htmllang"]}">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(titel)}</title>
<meta name="description" content="{esc(desc)}">
<link rel="canonical" href="{DOMAIN}{pfad(lang, rest)}">
{alt}<meta property="og:type" content="website">
<meta property="og:site_name" content="aiapicompare">
<meta property="og:title" content="{esc(titel)}">
<meta property="og:description" content="{esc(desc)}">
<meta property="og:image" content="{DOMAIN}og-image.png">
<meta name="twitter:card" content="summary_large_image">
<link rel="icon" href="{rel}favicon.svg" type="image/svg+xml">
<link rel="apple-touch-icon" href="{rel}apple-touch-icon.png">
<link rel="stylesheet" href="{rel}style.css">
<link rel="alternate" type="application/rss+xml" title="aiapicompare RSS" href="{rel}{pfad(lang, "feed.xml")}">
<script src="{rel}theme.js"></script>
<style>
  .seite{{max-width:1000px}} .bc{{font-size:.8rem;color:var(--dim);margin-bottom:.6rem}} .bc a{{color:var(--muted)}}
  .lead b{{color:var(--fg)}} .zahlen{{display:flex;flex-wrap:wrap;gap:.6rem;margin:1rem 0}}
  .zahl{{border:1px solid var(--border);border-radius:.5rem;padding:.55rem .8rem;background:var(--panel);min-width:150px}}
  .zahl span{{display:block;font-size:.7rem;color:var(--muted);text-transform:uppercase;letter-spacing:.05em}} .zahl b{{font-size:1.05rem}}
  td.num,th.num{{text-align:right}} .price{{font-family:var(--mono);white-space:nowrap}} tr.best td{{background:var(--accent-bg)}}
  .cap{{display:inline-flex;gap:.3rem;align-items:center;font-size:.82rem;padding:.15rem .5rem;border:1px solid var(--border2);border-radius:.4rem;background:var(--panel2);margin:0 .3rem .3rem 0}}
  .caps{{display:flex;flex-wrap:wrap;margin-top:.2rem}} .mini .cap{{font-size:.72rem;padding:.05rem .3rem}}
  .chart{{width:100%;height:auto;border:1px solid var(--border);border-radius:.6rem;background:var(--panel)}}
  pre{{background:var(--codebg);border:1px solid var(--border);border-radius:.45rem;padding:.8rem 1rem;overflow-x:auto}}
  .rel a{{display:inline-block;margin:0 .4rem .4rem 0}} details{{border-bottom:1px solid var(--border);padding:.55rem 0}} summary{{cursor:pointer;font-weight:600}}
  .tag{{font-size:.68rem;padding:.05rem .35rem;border-radius:.3rem;border:1px solid var(--border2);margin-left:.3rem}}
  .tag.g{{color:var(--accent);border-color:var(--accent)}} .idx td{{padding:.35rem .6rem}} .langlinks a{{margin-right:.5rem}}
</style>
</head>
<body>
<div class="topbar">
  <a class="brand" href="{rel}index.html" aria-label="aiapicompare"><img class="logo-d" src="{rel}logo/logo.svg" alt="aiapicompare" width="166" height="30"><img class="logo-l" src="{rel}logo/logo-hell.svg" alt="aiapicompare" width="166" height="30"></a>
  <nav class="nav">
    <a href="{rel}index.html">{t["nav_vergleich"]}</a>
    <a href="{rel}kosten.html">{t["nav_kosten"]}</a>
    <a href="{rel}finder.html">{t["nav_finder"]}</a>
    <a href="{rel}{pfad(lang, "free.html")}">{t["nav_gratis"]}</a>
    <a href="{rel}bestenliste.html">{t["nav_best"]}</a>
    <a href="{rel}news.html">{t["nav_news"]}</a>
    <a href="{rel}anbindung.html">{t["nav_anbindung"]}</a>
  </nav>
  <button class="themebtn" title="Light / dark"><span class="ti-l">☀</span><span class="ti-d">☾</span></button>
  <div class="langbtns langlinks">{sprachlinks}</div>
</div>
<div class="wrap seite">
'''

def fuss(lang, rel):
    t = T[lang]
    return f'''
<div class="legal"><a href="{rel}index.html">{t["nav_vergleich"]}</a><a href="{rel}{pfad(lang, "models/index.html")}">{t["alle_modelle"]}</a><a href="{rel}{pfad(lang, "providers/index.html")}">{t["fuss_anb"]}</a><a href="{rel}preisindex.html">{t["fuss_index"]}</a><a href="{rel}einbetten.html">{t["fuss_widget"]}</a><a href="{rel}methodik.html">{t["fuss_methodik"]}</a><a href="{rel}api/prices.json">{t["api"]}</a><a href="{rel}impressum.html">{t["impressum"]}</a><a href="{rel}datenschutz.html">{t["datenschutz"]}</a></div>
</div>
<script>
(function(){{
  var lang = "{lang}";
  try {{ localStorage.setItem("lang", lang); }} catch(e) {{}}
  document.addEventListener("click", function(e){{ var a = e.target.closest("a[data-setlang]"); if (a) try {{ localStorage.setItem("lang", a.dataset.setlang); }} catch(_) {{}} }});
}})();
</script>
<script src="{rel}config.js"></script>
<script src="{rel}einwilligung.js"></script>
</body>
</html>
'''

def go_link(z, t):
    return (f'<a class="btn" data-anb="{z["q"]}" href="{esc(z["url"] or "#")}" target="_blank" rel="noopener">{t["zum"]}</a>')

def caps_html(z, lang, mini=True):
    teile = []
    for c in z["faeh"]:
        if c in FAEH:
            ico, lab = FAEH[c]
            teile.append(f'<span class="cap" title="{esc(lab[lang])}">{ico}{"" if mini else " " + esc(lab[lang])}</span>')
    if z["dauer"]:
        teile.append(f'<span class="cap">≤{z["dauer"]} s</span>')
    if z["aufl"] and z["aufl"] != "4K":
        teile.append(f'<span class="cap">{esc(z["aufl"])}</span>')
    return f'<span class="caps{" mini" if mini else ""}">{"".join(teile)}</span>' if teile else ""

# ------------------------------------------------------------------ Preisverlauf-Diagramm
def verlauf_svg(info):
    punkte = defaultdict(lambda: float("inf"))
    zeilen = [z for z in info["zeilen"] if not z["auff"]] or info["zeilen"]   # ohne Angebote weit unter Referenzpreis
    serien = [VERLAUF.get(z["q"] + "|" + z["kanon"], {}).get("p") or [] for z in zeilen]
    tage = sorted({d for s in serien for d, _ in s})
    if len(tage) < 2:
        return None
    for tag in tage:          # günstigster Preis je Tag (letzter bekannter Preis je Anbieter)
        for s in serien:
            gueltig = [p for d, p in s if d <= tag]
            if gueltig and gueltig[-1] is not None:
                punkte[tag] = min(punkte[tag], gueltig[-1])
    werte = [(d, punkte[d]) for d in tage if punkte[d] != float("inf")]
    if len(werte) < 2 or len({w for _, w in werte}) < 2:
        return None
    W, H, P = 640, 170, 36
    lo, hi = min(w for _, w in werte), max(w for _, w in werte)
    spanne = (hi - lo) or 1
    xs = lambda i: P + i * (W - 2 * P) / (len(werte) - 1)
    ys = lambda w: H - P + 6 - (w - lo) / spanne * (H - 2 * P)
    pts = " ".join(f"{xs(i):.1f},{ys(w):.1f}" for i, (_, w) in enumerate(werte))
    kreise = "".join(f'<circle cx="{xs(i):.1f}" cy="{ys(w):.1f}" r="3" fill="var(--accent)"/>' for i, (_, w) in enumerate(werte))
    return f'''<svg class="chart" viewBox="0 0 {W} {H}" role="img" aria-label="price history">
<polyline points="{pts}" fill="none" stroke="var(--accent)" stroke-width="2.5" stroke-linejoin="round"/>
{kreise}
<text x="{P}" y="{H - 8}" font-size="11" fill="var(--muted)">{werte[0][0]}</text>
<text x="{W - P}" y="{H - 8}" font-size="11" fill="var(--muted)" text-anchor="end">{werte[-1][0]}</text>
<text x="6" y="{ys(hi) + 4:.1f}" font-size="11" fill="var(--muted)">{fmt(hi)}</text>
<text x="6" y="{ys(lo) + 4:.1f}" font-size="11" fill="var(--muted)">{fmt(lo)}</text>
</svg>'''

# ------------------------------------------------------------------ Modellseite
def modellseite(info, lang):
    t = T[lang]
    rel = "../" if lang == "en" else "../../"
    rest = f'models/{info["slug"]}.html'
    b = info["billig_ok"]          # günstigstes Angebot ohne „weit unter Referenzpreis“ / veraltete Daten
    name, n = info["name"], info["anbieter"]
    if info["media"]:
        desc = t["desc_media"].format(name=name, preis=preis_text(b, t), prov=b["quelle"], n=n)
        lead = t["lead_media"].format(name=esc(name), n=n, prov=esc(b["quelle"]), preis=esc(preis_text(b, t)))
    else:
        desc = t["desc_text"].format(name=name, prov=b["quelle"], inp=fmt(b["inp"] if b["inp"] is not None else b["ab"]), out=fmt(b["out"]), n=n)
        vorlage = t["lead_flat"] if (b["out"] is None and not b["gratis"]) else t["lead_text"]
        lead = vorlage.format(name=esc(name), n=n, prov=esc(b["quelle"]),
                                     inp=esc(t["gratis"] if b["gratis"] else fmt(b["inp"] if b["inp"] is not None else b["ab"])),
                                     out=esc(t["gratis"] if b["gratis"] else fmt(b["out"])))
    extra = []
    if info["ctx"] and not info["media"]:
        extra.append(t["ctx"].format(ctx=f'{info["ctx"]:,}'.replace(",", " ")))
    if info["gratis"]:
        extra.append(t["gratis_bei"].format(prov=", ".join(sorted({z["quelle"] for z in info["gratis"]}))))
    if info["entw"]:
        extra.append(t["entw"].format(e=esc(info["entw"])))

    h = kopf(lang, rel, (t["titel"] if n > 1 else t["titel1"]).format(name=name, n=n), desc, rest)
    h += f'<div class="bc"><a href="{rel}index.html">aiapicompare</a> › <a href="{rel}{pfad(lang, "models/index.html")}">{t["alle_modelle"]}</a> › {esc(name)}</div>\n'
    h += f'<h1>{esc(t["h1"].format(name=name))}</h1>\n<p class="lead">{lead} {" ".join(extra)}</p>\n'

    alle_faeh = []
    for z in info["zeilen"]:
        for c in z["faeh"]:
            if c not in alle_faeh:
                alle_faeh.append(c)
    if alle_faeh:
        h += f'<h2>{t["faeh_titel"]}</h2><div class="caps">' + "".join(
            f'<span class="cap">{FAEH[c][0]} {esc(FAEH[c][1][lang])}</span>' for c in alle_faeh if c in FAEH) + "</div>\n"

    # Platzierungen in der Arena-Bestenliste (CC BY 4.0, mit Quellenangabe)
    plaetze = {}
    for z in info["zeilen"]:
        for bk, pl in ((STAERKEN.get("modelle") or {}).get(re.sub(r":free$", "", z["kanon"])) or {}).items():
            if bk not in plaetze or pl < plaetze[bk]:
                plaetze[bk] = pl
    if plaetze:
        meta = STAERKEN.get("meta") or {}
        chips = "".join(
            f'<a class="cap" style="text-decoration:none" href="{rel}bestenliste.html#{bk}">🏆 {t["platz"].format(p=pl)} · '
            f'{esc((BEREICH_NAMEN.get(bk) or {}).get(lang) or (BEREICH_NAMEN.get(bk) or {}).get("en") or bk)}</a>'
            for bk, pl in sorted(plaetze.items(), key=lambda x: x[1]))
        h += f'<h2>{t["arena_titel"]}</h2><div class="caps">{chips}</div>\n'
        h += (f'<p class="hint" style="font-size:.75rem;color:var(--dim)">'
              f'{t["arena_quelle"].format(stand=esc(meta.get("stand", "")), ds=meta.get("datensatz", ""), lz=meta.get("lizenz_url", ""))}</p>\n')

    # Tabelle
    h += '<div class="tablewrap" style="margin-top:1rem"><table><thead><tr>'
    if info["media"]:
        h += f'<th>{t["th_anbieter"]}</th><th class="num">{t["th_preis"]}</th><th>{t["th_faeh"]}</th><th></th>'
    else:
        h += f'<th>{t["th_anbieter"]}</th><th class="num">{t["th_in"]}</th><th class="num">{t["th_out"]}</th><th class="num">{t["th_ctx"]}</th><th></th>'
    h += "</tr></thead><tbody>"
    bezahlt = [z["preis"] for z in info["zeilen"] if 0 < z["preis"] < float("inf") and z["ok"]]
    min_bez = min(bezahlt) if bezahlt else None
    def aufschlag(z):
        if min_bez and not z["auff"] and 0 < z["preis"] < float("inf") and z["preis"] > min_bez:
            return f' <span class="diff">+{round((z["preis"] / min_bez - 1) * 100)} %</span>'
        return ""
    # erst die regulären Angebote, darunter getrennt die Angebote weit unter dem Referenzpreis
    reihe = [z for z in info["zeilen"] if not z["auff"]] + [z for z in info["zeilen"] if z["auff"]]
    erster_ok = next((z for z in reihe if z["ok"]), None)
    rt = REF_T[lang]
    spalten = 4 if info["media"] else 5
    trenner = False
    for i, z in enumerate(reihe):
        if z["auff"] and not trenner:
            trenner = True
            h += f'<tr class="trenner"><td colspan="{spalten}">⚠ {esc(rt["trenner"])}</td></tr>'
        anb = f'<span class="dot" style="background:{z["farbe"]}"></span><a href="{rel}{pfad(lang, "providers/" + z["q"] + ".html")}">{esc(z["quelle"])}</a>{ref_tags(z, lang)}<br><small style="color:var(--dim);font-family:var(--mono)">{esc(z["roh"])}</small>'
        einr = f' <a class="btn" href="{rel}anbindung.html#anbieter={z["q"]}&amp;modell={esc(z["roh"])}">{t["einrichten"]}</a>' if not z["media"] else ""
        cls = ' class="best"' if z is erster_ok and len(info["zeilen"]) > 1 else ""
        if info["media"]:
            h += f'<tr{cls}><td>{anb}</td><td class="num price">{esc(preis_text(z, t))}{aufschlag(z)}</td><td>{caps_html(z, lang)}</td><td class="num">{go_link(z, t)}</td></tr>'
        else:
            pin = t["gratis"] if z["gratis"] else fmt(z["inp"] if z["inp"] is not None else z["ab"])
            pout = t["gratis"] if z["gratis"] else fmt(z["out"])
            h += f'<tr{cls}><td>{anb}</td><td class="num price">{esc(pin)}{aufschlag(z)}</td><td class="num price">{esc(pout)}</td><td class="num">{fmt_ctx(z["ctx"])}</td><td class="num" style="white-space:nowrap">{go_link(z, t)}{einr}</td></tr>'
    h += f'</tbody></table></div>\n<p class="hint" style="font-size:.78rem;color:var(--dim)">{t["ranking"]} {t["stand"].format(d=esc(STAND))}</p>\n'
    rtext = ref_text(info["zeilen"][0]["kanon"], lang) if not info["media"] else ""
    betreff = urllib.parse.quote(f"Preis / price: {name}")
    h += ('<p class="refzeile">' + (f'{esc(rt["ref"])}: {esc(rtext)} · ' if rtext else "")
          + f'<a href="{rel}methodik.html">{esc(rt["mehr"])}</a> · <a href="mailto:kontakt@aiapicompare.com?subject={betreff}">{esc(rt["melden"])}</a></p>\n')

    # Preisverlauf
    svg = verlauf_svg(info)
    h += f'<h2>{t["verlauf_titel"]}</h2>' + (svg if svg else f'<p style="color:var(--muted)">{t["verlauf_start"]}</p>') + "\n"

    # Schnellstart (Text-Modelle)
    if not info["media"]:
        g = next((z for z in info["zeilen"] if not z["media"] and z["ok"]), None) or next((z for z in info["zeilen"] if not z["media"]), None)
        if g:
            _, _, base, env = ANBIETER[g["q"]]
            h += f'<h2>{esc(t["code_titel"].format(prov=g["quelle"]))}</h2><pre>' + esc(
                f'from openai import OpenAI\nimport os\n\nclient = OpenAI(base_url="{base}", api_key=os.environ["{env}"])\n'
                f'r = client.chat.completions.create(\n    model="{g["roh"]}",\n    messages=[{{"role": "user", "content": "{t["hallo"]}"}}],\n)\nprint(r.choices[0].message.content)') + "</pre>\n"

    # Häufige Fragen
    link = f'{rel}anbindung.html#anbieter={b["q"]}&amp;modell={esc(b["roh"])}'
    h += f'<h2>{t["faq_titel"]}</h2>'
    h += f'<details open><summary>{esc(t["q1"].format(name=name))}</summary><p>{esc(t["a1"].format(prov=b["quelle"], preis=preis_text(b, t)))}</p></details>'
    if not info["media"]:
        h += f'<details><summary>{esc(t["q2"].format(name=name))}</summary><p>{t["a2"].format(link=link)}</p></details>'

    # Direkte Vergleiche mit diesem Modell
    meine = [(x, y) for g, x, y in VS_PAARE if info["slug"] in (x, y)][:12]
    if meine:
        h += f'<h2>{VS[lang]["verfuegbar"]}</h2><div class="rel">' + "".join(
            f'<a class="btn" href="{rel}{pfad(lang, "compare/" + vs_slug(x, y) + ".html")}">{esc(INFOS[x]["name"])} vs. {esc(INFOS[y]["name"])}</a>'
            for x, y in meine) + "</div>"

    # Verwandte Modelle
    if info["entw"]:
        verw = sorted((i for s, i in INFOS.items() if i["entw"] == info["entw"] and s != info["slug"]),
                      key=lambda i: (-i["anbieter"], i["billig"]["preis"]))[:12]
        if verw:
            h += f'<h2>{esc(t["verwandt"].format(e=info["entw"]))}</h2><div class="rel">' + "".join(
                f'<a class="btn" href="{esc(i["slug"])}.html">{esc(i["name"])}</a>' for i in verw) + "</div>"
    h += fuss(lang, rel)
    return h

# ------------------------------------------------------------------ Kostenlose Modelle
def gratisseite(lang):
    t = T[lang]
    rel = "" if lang == "en" else "../"
    liste = sorted((z for z in ZEILEN if z["gratis"]), key=lambda z: (-z["ctx"], z["name"]))
    h = kopf(lang, rel, t["free_titel"].format(n=len(liste)), t["free_desc"].format(n=len(liste)), "free.html")
    h += f'<h1>{t["free_h1"]}</h1><p class="lead">{t["free_lead"]}</p>'
    if not liste:
        h += f'<p>{t["free_leer"]}</p>'
    else:
        h += f'<div class="tablewrap"><table><thead><tr><th>{t["th_modell"]}</th><th>{t["th_anbieter"]}</th><th class="num">{t["th_ctx"]}</th><th></th></tr></thead><tbody>'
        for z in liste:
            h += (f'<tr><td><a href="{rel}{pfad(lang, "models/" + z["slug"] + ".html")}">{esc(name_sauber(z["name"]))}</a>'
                  f'<br><small style="color:var(--dim);font-family:var(--mono)">{esc(z["roh"])}</small></td>'
                  f'<td><span class="dot" style="background:{z["farbe"]}"></span>{esc(z["quelle"])}</td>'
                  f'<td class="num">{fmt_ctx(z["ctx"])}</td><td class="num">{go_link(z, t)}</td></tr>')
        h += "</tbody></table></div>"
    h += f'<p style="font-size:.78rem;color:var(--dim)">{t["stand"].format(d=esc(STAND))}</p>'
    h += fuss(lang, rel)
    return h

# ------------------------------------------------------------------ Verzeichnis A–Z
def verzeichnis(lang):
    t = T[lang]
    rel = "../" if lang == "en" else "../../"
    infos = sorted(INFOS.values(), key=lambda i: i["name"].lower())
    h = kopf(lang, rel, t["idx_titel"], t["idx_desc"].format(n=len(infos), p=len(ANBIETER)), "models/index.html")
    h += f'<h1>{t["idx_h1"]}</h1><p class="lead">{t["idx_lead"].format(n=len(infos), p=len({z["q"] for z in ZEILEN}))}</p>'
    h += f'<div class="tablewrap"><table class="idx"><thead><tr><th>{t["th_modell"]}</th><th class="num">{t["th_anz"]}</th><th class="num">{t["th_ab"]}</th></tr></thead><tbody>'
    for i in infos:
        g = ' <span class="tag g">' + t["gratis"] + "</span>" if i["gratis"] else ""
        h += (f'<tr><td><a href="{esc(i["slug"])}.html">{esc(i["name"])}</a>{g}</td><td class="num">{i["anbieter"]}</td>'
              f'<td class="num price">{esc(preis_text(i["billig"], t))}</td></tr>')
    h += "</tbody></table></div>" + fuss(lang, rel)
    return h

# ------------------------------------------------------------------ Vergleichsseiten "A vs. B"
# Eigene Preisdaten + Platzierungen der Arena-Bestenliste (CC BY 4.0, mit Quellenangabe).
VS = {
"en": dict(titel="{a} vs {b}: API price & performance compared", desc="{a} vs {b}: cheapest API price, context window, providers and Arena leaderboard ranks side by side. Updated daily.",
  h1="{a} vs. {b}", bc="Comparisons", preis_billiger="{x} is {p} % cheaper than {y} at the cheapest provider ({px} vs. {py} per 1M input tokens).",
  preis_billiger_m="{x} is {p} % cheaper than {y} at the cheapest provider ({px} vs. {py}{e}).",
  preis_gleich="Both cost the same at the cheapest provider ({px}).", arena_vor="In the Arena leaderboard, {x} ranks ahead of {y} in {w} of {n} categories.",
  arena_gleich="In the Arena leaderboard, both rank ahead of each other equally often ({w} of {n} categories each).", arena_keine="There are no shared Arena rankings for a performance comparison.",
  t_daten="Prices & key facts", t_arena="Arena leaderboard ranks", t_kosten="Example: monthly cost", kosten_text="10M input + 2M output tokens per month at the cheapest provider:",
  z_preis="Cheapest price", z_out="Output price / 1M", z_ctx="Context window", z_anb="Providers", z_frei="Also free", z_entw="Developer", ja="yes", nein="no",
  bereich="Category", platz="Rank {p}", weitere="More comparisons", alle="All comparisons", modellseite="Model page", im_vergleich="Compare all providers",
  idx_titel="AI model comparisons: price & performance side by side", idx_desc="Head-to-head comparisons of popular AI models: API prices, context windows and Arena leaderboard ranks.",
  idx_h1="AI model comparisons", idx_lead="Popular models side by side – with the cheapest API price from our daily price check and the ranks from the Arena leaderboard.",
  g_text="Text & code", g_bild="Image generation", g_video="Video generation", verfuegbar="Comparisons", fuer="Compare {a} with …"),
"de": dict(titel="{a} vs. {b}: API-Preis & Leistung im Vergleich", desc="{a} vs. {b}: günstigster API-Preis, Kontextfenster, Anbieter und Platzierungen in der Arena-Bestenliste im direkten Vergleich. Täglich aktualisiert.",
  h1="{a} vs. {b}", bc="Vergleiche", preis_billiger="{x} ist beim günstigsten Anbieter {p} % günstiger als {y} ({px} gegenüber {py} pro 1 Mio. Input-Token).",
  preis_billiger_m="{x} ist beim günstigsten Anbieter {p} % günstiger als {y} ({px} gegenüber {py}{e}).",
  preis_gleich="Beide kosten beim günstigsten Anbieter gleich viel ({px}).", arena_vor="In der Arena-Bestenliste liegt {x} in {w} von {n} Bereichen vor {y}.",
  arena_gleich="In der Arena-Bestenliste liegen beide gleich oft vorn (je {w} von {n} Bereichen).", arena_keine="Für einen Leistungsvergleich gibt es keine gemeinsamen Platzierungen in der Arena-Bestenliste.",
  t_daten="Preise & Eckdaten", t_arena="Platzierungen in der Arena-Bestenliste", t_kosten="Beispiel: Kosten pro Monat", kosten_text="10 Mio. Input- + 2 Mio. Output-Token pro Monat beim günstigsten Anbieter:",
  z_preis="Günstigster Preis", z_out="Output-Preis / 1 Mio.", z_ctx="Kontextfenster", z_anb="Anbieter", z_frei="Auch kostenlos", z_entw="Entwickler", ja="ja", nein="nein",
  bereich="Bereich", platz="Platz {p}", weitere="Weitere Vergleiche", alle="Alle Vergleiche", modellseite="Modellseite", im_vergleich="Alle Anbieter vergleichen",
  idx_titel="KI-Modelle im Vergleich: Preis & Leistung direkt gegenübergestellt", idx_desc="Direkte Vergleiche beliebter KI-Modelle: API-Preise, Kontextfenster und Platzierungen in der Arena-Bestenliste.",
  idx_h1="KI-Modelle im direkten Vergleich", idx_lead="Beliebte Modelle nebeneinander – mit dem günstigsten API-Preis aus unserem täglichen Preisvergleich und den Platzierungen der Arena-Bestenliste.",
  g_text="Text & Code", g_bild="Bilder erzeugen", g_video="Videos erzeugen", verfuegbar="Vergleiche", fuer="{a} vergleichen mit …"),
"zh": dict(titel="{a} 对比 {b}：API 价格与性能", desc="{a} 对比 {b}：最低 API 价格、上下文窗口、提供商及 Arena 排行榜名次一览。每日更新。",
  h1="{a} 对比 {b}", bc="对比", preis_billiger="在最便宜的提供商处，{x} 比 {y} 便宜 {p}%（每百万输入 Token {px} 对比 {py}）。",
  preis_billiger_m="在最便宜的提供商处，{x} 比 {y} 便宜 {p}%（{px} 对比 {py}{e}）。",
  preis_gleich="两者在最便宜的提供商处价格相同（{px}）。", arena_vor="在 Arena 排行榜中，{x} 在 {n} 个领域中的 {w} 个领先于 {y}。",
  arena_gleich="在 Arena 排行榜中，两者领先的次数相同（各 {n} 个领域中的 {w} 个）。", arena_keine="Arena 排行榜中没有可用于性能对比的共同排名。",
  t_daten="价格与关键数据", t_arena="Arena 排行榜名次", t_kosten="示例：每月费用", kosten_text="在最便宜的提供商处，每月 1000 万输入 + 200 万输出 Token：",
  z_preis="最低价格", z_out="输出价格 / 百万", z_ctx="上下文窗口", z_anb="提供商数量", z_frei="也有免费版", z_entw="开发者", ja="是", nein="否",
  bereich="领域", platz="第 {p} 名", weitere="更多对比", alle="全部对比", modellseite="模型页面", im_vergleich="比较所有提供商",
  idx_titel="AI 模型对比：价格与性能", idx_desc="热门 AI 模型的直接对比：API 价格、上下文窗口和 Arena 排行榜名次。",
  idx_h1="AI 模型直接对比", idx_lead="热门模型并列对比——附我们每日价格查询中的最低 API 价格以及 Arena 排行榜名次。",
  g_text="文本与代码", g_bild="图像生成", g_video="视频生成", verfuegbar="对比", fuer="将 {a} 与以下模型对比 …"),
"ru": dict(titel="{a} vs {b}: цена API и качество", desc="{a} vs {b}: самая низкая цена API, контекстное окно, поставщики и места в рейтинге Arena рядом. Обновляется ежедневно.",
  h1="{a} vs {b}", bc="Сравнения", preis_billiger="У самого дешёвого поставщика {x} на {p} % дешевле, чем {y} ({px} против {py} за 1 млн входных токенов).",
  preis_billiger_m="У самого дешёвого поставщика {x} на {p} % дешевле, чем {y} ({px} против {py}{e}).",
  preis_gleich="У самого дешёвого поставщика обе модели стоят одинаково ({px}).", arena_vor="В рейтинге Arena {x} опережает {y} в {w} из {n} областей.",
  arena_gleich="В рейтинге Arena обе модели опережают друг друга одинаково часто (по {w} из {n} областей).", arena_keine="Общих мест в рейтинге Arena для сравнения качества нет.",
  t_daten="Цены и основные данные", t_arena="Места в рейтинге Arena", t_kosten="Пример: расходы в месяц", kosten_text="10 млн входных + 2 млн выходных токенов в месяц у самого дешёвого поставщика:",
  z_preis="Самая низкая цена", z_out="Цена вывода / 1 млн", z_ctx="Контекстное окно", z_anb="Поставщиков", z_frei="Есть бесплатно", z_entw="Разработчик", ja="да", nein="нет",
  bereich="Область", platz="Место {p}", weitere="Другие сравнения", alle="Все сравнения", modellseite="Страница модели", im_vergleich="Сравнить всех поставщиков",
  idx_titel="Сравнение AI-моделей: цена и качество", idx_desc="Прямые сравнения популярных AI-моделей: цены API, контекстные окна и места в рейтинге Arena.",
  idx_h1="AI-модели в прямом сравнении", idx_lead="Популярные модели рядом – с самой низкой ценой API из нашей ежедневной проверки и местами в рейтинге Arena.",
  g_text="Текст и код", g_bild="Генерация изображений", g_video="Генерация видео", verfuegbar="Сравнения", fuer="Сравнить {a} с …"),
}
BEREICH_REIHENFOLGE = [k for k in BEREICH_NAMEN]

def plaetze_von(info):
    pl = {}
    for z in info["zeilen"]:
        for bk, p in ((STAERKEN.get("modelle") or {}).get(re.sub(r":free$", "", z["kanon"])) or {}).items():
            if bk not in pl or p < pl[bk]:
                pl[bk] = p
    return pl

def bezahlt_billig(info, alle=False):
    """Günstigstes bezahltes Angebot – ohne Angebote weit unter Referenzpreis und ohne veraltete Daten (> 3 Tage)."""
    l = [z for z in info["zeilen"] if 0 < z["preis"] < float("inf") and (alle or z["ok"])]
    return min(l, key=lambda z: (z["preis"], z["quelle"])) if l else None

def top_slugs(bereiche, n, media):
    out = []
    for bk, anzahl in bereiche:
        genommen = 0
        for x in ((STAERKEN.get("bereiche") or {}).get(bk) or {}).get("liste", []):
            for k in x.get("k") or []:
                s = slug(re.sub(r":free$", "", k))
                if s in INFOS and INFOS[s]["media"] == media and bezahlt_billig(INFOS[s]):
                    if s not in out:
                        out.append(s)
                        genommen += 1
                    break
            if genommen >= anzahl or len(out) >= n:
                break
    return out[:n]

VS_GRUPPEN = []     # (Gruppe, [slugs])
if STAERKEN:
    VS_GRUPPEN = [("text", top_slugs([("allround", 12), ("coding", 6), ("deutsch", 4)], 16, False)),
                  ("bild", top_slugs([("bild", 8)], 8, True)),
                  ("video", top_slugs([("video", 6)], 6, True))]
VS_PAARE = []       # (Gruppe, a, b) – Reihenfolge nach Platzierung
for gruppe, slugs in VS_GRUPPEN:
    for i in range(len(slugs)):
        for j in range(i + 1, len(slugs)):
            VS_PAARE.append((gruppe, slugs[i], slugs[j]))

def vs_slug(a, b):
    return "-vs-".join(sorted([a, b]))

def vs_einheit(z, t):
    if z["ps"] is not None:
        return t["einheit"]["second"]
    return t["einheit"].get(z["einheit"], "")

def vs_preis(z):
    return z["ps"] if z["ps"] is not None else z["preis"]

def vergleichsseite(gruppe, a, b, lang):
    t, v = T[lang], VS[lang]
    rel = "../" if lang == "en" else "../../"
    A, B = INFOS[a], INFOS[b]
    rest = f"compare/{vs_slug(a, b)}.html"
    h = kopf(lang, rel, v["titel"].format(a=A["name"], b=B["name"]) + " | aiapicompare",
             v["desc"].format(a=A["name"], b=B["name"]), rest)
    h += (f'<div class="bc"><a href="{rel}index.html">aiapicompare</a> › '
          f'<a href="{rel}{pfad(lang, "compare/index.html")}">{v["bc"]}</a> › {esc(A["name"])} vs. {esc(B["name"])}</div>\n')
    h += f'<h1>{esc(v["h1"].format(a=A["name"], b=B["name"]))}</h1>\n'
    za, zb = bezahlt_billig(A), bezahlt_billig(B)
    satz = []
    if za and zb:
        pa, pb = vs_preis(za), vs_preis(zb)
        if abs(pa - pb) < 1e-12:
            satz.append(v["preis_gleich"].format(px=fmt(pa)))
        else:
            x, y, px, py = (A, B, pa, pb) if pa < pb else (B, A, pb, pa)
            proz = round((1 - px / py) * 100)          # Ersparnis in % des teureren Preises
            proz = ">99" if proz >= 100 else proz
            vorlage = v["preis_billiger_m"] if A["media"] else v["preis_billiger"]
            satz.append(vorlage.format(x=x["name"], y=y["name"], p=proz, px=fmt(px), py=fmt(py), e=vs_einheit(za, t)))
    pla, plb = plaetze_von(A), plaetze_von(B)
    gemeinsam = [k for k in BEREICH_REIHENFOLGE if k in pla and k in plb]
    if gemeinsam:
        wa = sum(1 for k in gemeinsam if pla[k] < plb[k])
        wb = sum(1 for k in gemeinsam if plb[k] < pla[k])
        if wa == wb:
            satz.append(v["arena_gleich"].format(w=wa, n=len(gemeinsam)))
        else:
            x, y, w = (A, B, wa) if wa > wb else (B, A, wb)
            satz.append(v["arena_vor"].format(x=x["name"], y=y["name"], w=w, n=len(gemeinsam)))
    else:
        satz.append(v["arena_keine"])
    h += f'<p class="lead">{esc(("" if lang == "zh" else " ").join(satz))}</p>\n'

    # Preise & Eckdaten
    def zelle_preis(z):
        if not z:
            return "—"
        return (f'<span class="price">{esc(preis_text(z, t))}</span><br><small style="color:var(--dim)">'
                f'<span class="dot" style="background:{z["farbe"]}"></span>{esc(z["quelle"])}</small>')
    zeilen = [(v["z_preis"], zelle_preis(za), zelle_preis(zb))]
    if not A["media"]:
        zeilen.append((v["z_out"], esc(fmt(za["out"])) if za and za["out"] is not None else "—",
                       esc(fmt(zb["out"])) if zb and zb["out"] is not None else "—"))
        zeilen.append((v["z_ctx"], fmt_ctx(A["ctx"]), fmt_ctx(B["ctx"])))
    zeilen.append((v["z_anb"], str(A["anbieter"]), str(B["anbieter"])))
    zeilen.append((v["z_frei"], v["ja"] if A["gratis"] else v["nein"], v["ja"] if B["gratis"] else v["nein"]))
    if A["entw"] or B["entw"]:
        zeilen.append((v["z_entw"], esc(A["entw"] or "—"), esc(B["entw"] or "—")))
    kopfz = (f'<tr><th></th><th><a href="{rel}{pfad(lang, "models/" + a + ".html")}">{esc(A["name"])}</a></th>'
             f'<th><a href="{rel}{pfad(lang, "models/" + b + ".html")}">{esc(B["name"])}</a></th></tr>')
    h += f'<h2>{v["t_daten"]}</h2><div class="tablewrap"><table><thead>{kopfz}</thead><tbody>'
    h += "".join(f'<tr><td>{esc(l)}</td><td>{x}</td><td>{y}</td></tr>' for l, x, y in zeilen) + "</tbody></table></div>\n"

    # Arena-Platzierungen
    bereiche = [k for k in BEREICH_REIHENFOLGE if k in pla or k in plb]
    if bereiche:
        h += f'<h2>{v["t_arena"]}</h2><div class="tablewrap"><table><thead><tr><th>{v["bereich"]}</th><th>{esc(A["name"])}</th><th>{esc(B["name"])}</th></tr></thead><tbody>'
        for k in bereiche:
            nm = BEREICH_NAMEN.get(k) or {}
            ra, rb = pla.get(k), plb.get(k)
            fa = ra is not None and (rb is None or ra < rb)
            fb = rb is not None and (ra is None or rb < ra)
            ca = (("<b>" if fa else "") + v["platz"].format(p=ra) + ("</b>" if fa else "")) if ra else "—"
            cb = (("<b>" if fb else "") + v["platz"].format(p=rb) + ("</b>" if fb else "")) if rb else "—"
            h += (f'<tr><td><a href="{rel}bestenliste.html#{k}">{nm.get("ico", "")} {esc(nm.get(lang) or nm.get("en") or k)}</a></td>'
                  f'<td>{ca}</td><td>{cb}</td></tr>')
        meta = STAERKEN.get("meta") or {}
        h += ('</tbody></table></div>\n<p class="hint" style="font-size:.75rem;color:var(--dim)">'
              f'{t["arena_quelle"].format(stand=esc(meta.get("stand", "")), ds=meta.get("datensatz", ""), lz=meta.get("lizenz_url", ""))}</p>\n')

    # Kostenbeispiel (nur Text)
    if not A["media"] and za and zb:
        def kosten(z):
            pin = z["inp"] if z["inp"] is not None else z["ab"]
            pout = z["out"] if z["out"] is not None else pin
            return 10 * pin + 2 * pout
        h += (f'<h2>{v["t_kosten"]}</h2><p>{v["kosten_text"]}</p><div class="zahlen">'
              f'<div class="zahl"><span>{esc(A["name"])}</span><b>{esc(fmt(kosten(za)))}</b></div>'
              f'<div class="zahl"><span>{esc(B["name"])}</span><b>{esc(fmt(kosten(zb)))}</b></div></div>\n')

    such = lambda i: rel + "index.html#q=" + urllib.parse.quote(i["name"])
    h += (f'<div class="rel" style="margin-top:1rem">'
          f'<a class="btn" href="{rel}{pfad(lang, "models/" + a + ".html")}">{v["modellseite"]}: {esc(A["name"])}</a>'
          f'<a class="btn" href="{rel}{pfad(lang, "models/" + b + ".html")}">{v["modellseite"]}: {esc(B["name"])}</a>'
          f'<a class="btn" href="{such(A)}">{v["im_vergleich"]} ↗</a><a class="btn" href="{rel}kosten.html">{t["nav_kosten"]}</a></div>\n')
    # Weitere Vergleiche
    weitere = [(g, x, y) for g, x, y in VS_PAARE if (x in (a, b) or y in (a, b)) and {x, y} != {a, b}][:12]
    if weitere:
        h += f'<h2>{v["weitere"]}</h2><div class="rel">' + "".join(
            f'<a class="btn" href="{vs_slug(x, y)}.html">{esc(INFOS[x]["name"])} vs. {esc(INFOS[y]["name"])}</a>' for _, x, y in weitere) + "</div>\n"
    h += f'<p style="font-size:.78rem;color:var(--dim)">{t["stand"].format(d=esc(STAND))} {t["ranking"]}</p>'
    h += fuss(lang, rel)
    return h

def vergleichsindex(lang):
    t, v = T[lang], VS[lang]
    rel = "../" if lang == "en" else "../../"
    h = kopf(lang, rel, v["idx_titel"] + " | aiapicompare", v["idx_desc"], "compare/index.html")
    h += f'<h1>{v["idx_h1"]}</h1><p class="lead">{v["idx_lead"]}</p>'
    for gruppe, slugs in VS_GRUPPEN:
        paare = [(x, y) for g, x, y in VS_PAARE if g == gruppe]
        if not paare:
            continue
        h += f'<h2>{v["g_" + gruppe]}</h2>'
        for s in slugs:
            mit = [(x, y) for x, y in paare if s in (x, y)]
            h += (f'<p style="margin:.8rem 0 .3rem;font-weight:600">{esc(v["fuer"].format(a=INFOS[s]["name"]))}</p><div class="rel">' +
                  "".join(f'<a class="btn" href="{vs_slug(x, y)}.html">{esc(INFOS[y if x == s else x]["name"])}</a>' for x, y in mit) + "</div>")
    meta = STAERKEN.get("meta") or {}
    if meta:
        h += (f'<p class="hint" style="font-size:.75rem;color:var(--dim);margin-top:1.2rem">'
              f'{t["arena_quelle"].format(stand=esc(meta.get("stand", "")), ds=meta.get("datensatz", ""), lz=meta.get("lizenz_url", ""))}</p>')
    h += fuss(lang, rel)
    return h

# ------------------------------------------------------------------ RSS-Feed & llms.txt
NEWS = {}
if (BASIS / "out" / "news.js").exists():
    try:
        NEWS = lade_js(BASIS / "out" / "news.js")
    except Exception:
        NEWS = {}

FEED = {
"en": dict(titel="aiapicompare – AI API price changes & new models", desc="Price cuts, price increases and new AI models across API providers – generated daily from our own price checks.",
  runter="{name} at {prov}: price cut {p} % ({alt} → {neu}{e})", hoch="{name} at {prov}: price increase +{p} % ({alt} → {neu}{e})",
  neu="New at {prov}: {name}{preis}", text="/ 1M input tokens", gratis="free"),
"de": dict(titel="aiapicompare – Preisänderungen & neue KI-Modelle", desc="Preissenkungen, Preiserhöhungen und neue KI-Modelle bei API-Anbietern – täglich aus unseren eigenen Preisabfragen erzeugt.",
  runter="{name} bei {prov}: Preissenkung {p} % ({alt} → {neu}{e})", hoch="{name} bei {prov}: Preiserhöhung +{p} % ({alt} → {neu}{e})",
  neu="Neu bei {prov}: {name}{preis}", text="/ 1 Mio. Input-Token", gratis="kostenlos"),
"zh": dict(titel="aiapicompare – AI API 价格变化与新模型", desc="各 API 提供商的降价、涨价与新模型——根据我们每日的价格查询自动生成。",
  runter="{prov} 的 {name}：降价 {p}%（{alt} → {neu}{e}）", hoch="{prov} 的 {name}：涨价 +{p}%（{alt} → {neu}{e}）",
  neu="{prov} 新上线：{name}{preis}", text="/ 百万输入 Token", gratis="免费"),
"ru": dict(titel="aiapicompare – изменения цен AI API и новые модели", desc="Снижения и повышения цен, новые AI-модели у поставщиков API – ежедневно по нашим собственным проверкам цен.",
  runter="{name} у {prov}: снижение цены {p} % ({alt} → {neu}{e})", hoch="{name} у {prov}: повышение цены +{p} % ({alt} → {neu}{e})",
  neu="Новое у {prov}: {name}{preis}", text="/ 1 млн входных токенов", gratis="бесплатно"),
}

def rss_datum(d):
    import email.utils, datetime
    try:
        return email.utils.format_datetime(datetime.datetime.strptime(d[:10], "%Y-%m-%d").replace(tzinfo=datetime.timezone.utc))
    except Exception:
        return email.utils.format_datetime(datetime.datetime.now(datetime.timezone.utc))

def feed(lang):
    t, f = T[lang], FEED[lang]
    def einheit(e):
        return t["einheit"].get(e, "") if e else " " + f["text"]
    def link(k):
        s = slug(k)
        return DOMAIN + pfad(lang, f"models/{s}.html") if s in INFOS else DOMAIN + "news.html"
    items = []
    for x in NEWS.get("preis", []):
        runter = x["neu"] < x["alt"]
        titel = (f["runter"] if runter else f["hoch"]).format(name=name_sauber(x["n"]), prov=ANBIETER.get(x["q"], (x["q"],))[0],
                 p=abs(x["pz"] or 0), alt=fmt(x["alt"]), neu=fmt(x["neu"]), e=einheit(x.get("e")))
        items.append((x["d"], titel, link(x["k"]), f'preis|{x["q"]}|{x["k"]}|{x["d"]}|{x["neu"]}'))
    for x in NEWS.get("neu", []):
        if x.get("g"):
            preis = f' ({f["gratis"]})'
        elif isinstance(x.get("in"), (int, float)):
            preis = f' ({fmt(x["in"])} {f["text"]})'
        elif isinstance(x.get("ab"), (int, float)):
            preis = f' ({fmt(x["ab"])} {f["text"]})'
        elif isinstance(x.get("mp"), (int, float)):
            preis = f' ({fmt(x["mp"])}{t["einheit"].get(x.get("e") or "", "")})'
        else:
            preis = ""
        titel = f["neu"].format(prov=ANBIETER.get(x["q"], (x["q"],))[0], name=name_sauber(x["n"]), preis=preis)
        items.append((x["d"], titel, link(x["k"]), f'neu|{x["q"]}|{x["k"]}|{x["d"]}'))
    items.sort(key=lambda i: i[0], reverse=True)
    selbst = DOMAIN + pfad(lang, "feed.xml")
    x = ['<?xml version="1.0" encoding="UTF-8"?>',
         '<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom"><channel>',
         f'<title>{esc(f["titel"])}</title><link>{DOMAIN}news.html</link><description>{esc(f["desc"])}</description>',
         f'<language>{T[lang]["htmllang"]}</language><lastBuildDate>{rss_datum(STAND)}</lastBuildDate>',
         f'<atom:link href="{selbst}" rel="self" type="application/rss+xml"/>']
    for d, titel, url, guid in items[:60]:
        x.append(f'<item><title>{esc(titel)}</title><link>{esc(url)}</link><guid isPermaLink="false">{esc(guid)}</guid><pubDate>{rss_datum(d)}</pubDate></item>')
    x.append("</channel></rss>")
    return "\n".join(x)

def llms_txt():
    namen = ", ".join(v[0] for v in ANBIETER.values())
    zeilen = [
        "# aiapicompare",
        "",
        f"> Independent price comparison for AI model APIs: input/output token prices, image and video prices, context windows and free models for {len(INFOS)} models across {len(ANBIETER)} providers ({namen}). Updated daily. Includes Arena leaderboard ranks per use case and head-to-head model comparisons.",
        "",
        "All prices are list prices in USD, collected automatically every night from the providers' public model lists and price pages. There are no paid placements; listings are sorted by price or by the Arena score.",
        "",
        "## Main pages",
        f"- [Price comparison]({DOMAIN}): all models and providers, sortable by price, provider and context window",
        f"- [Leaderboard – which AI model is best for what]({DOMAIN}bestenliste.html): Arena ranks per use case (coding, math, writing, German, images, video …) with the cheapest API price",
        f"- [Model comparisons (A vs B)]({DOMAIN}compare/index.html): price and performance of popular models side by side",
        f"- [All models A–Z]({DOMAIN}models/index.html): one page per model with all providers, price history and FAQ",
        f"- [Free AI models via API]({DOMAIN}free.html)",
        f"- [News: new models and price changes]({DOMAIN}news.html)",
        f"- [Cost calculator]({DOMAIN}kosten.html): monthly cost for tokens, images or video seconds",
        f"- [Setup guides]({DOMAIN}anbindung.html): base URLs and configuration for VS Code, Cline, Cursor, Hermes and more",
        f"- [How we compare]({DOMAIN}methodik.html): data sources, reference prices and why some offers are flagged as far below the reference price",
        "",
        "## Data",
        f"- [prices.json]({DOMAIN}api/prices.json): all current prices as JSON",
        f"- [RSS feed]({DOMAIN}feed.xml): price changes and new models (also /de/feed.xml, /zh/feed.xml, /ru/feed.xml)",
        "",
        "## Sources and licenses",
        "- Prices: own daily collection from the providers' public data.",
        "- Leaderboard ranks: Arena (arena.ai, formerly LMArena), dataset lmarena-ai/leaderboard-dataset, licensed under CC BY 4.0.",
        "",
        "## Languages",
        "English (site root), German (/de/), Chinese (/zh/), Russian (/ru/).",
        "",
        f"Last data update: {STAND}",
    ]
    return "\n".join(zeilen) + "\n"

# ------------------------------------------------------------------ Anbieter-Seiten, Widget, 404
STARTSEITE = {"openrouter": "https://openrouter.ai", "uplinkswitch": "https://uplinkswitch.ai", "anymodel": "https://anymodel.org",
              "nanogpt": "https://nano-gpt.com", "chutes": "https://chutes.ai", "deepinfra": "https://deepinfra.com",
              "novita": "https://novita.ai", "cometapi": "https://www.cometapi.com", "kyma": "https://kymaapi.com"}
PV = {
"en": dict(titel="{p} API prices: {n} AI models compared | aiapicompare", desc="{p}: prices for {n} AI models via API, cheapest models, free models, Arena top models and setup (base URL). Updated daily.",
  h1="{p}: API prices & models", lead="{p} offers {n} models in our daily price check{arten}. Below: the cheapest models, the best-rated models in the Arena leaderboard and how to connect {p}.",
  arten=" ({t})", text="text", bild="image", video="video", gratis_n="{n} free",
  k_modelle="Models", k_gratis="Free models", k_ab="Cheapest text model", k_base="Base URL",
  h_billig="Cheapest text models at {p}", h_top="Best-rated models available at {p}", h_einr="Connect {p}",
  einr_text="OpenAI-compatible: use the base URL below with your {p} API key. Step-by-step guides for VS Code, Cline, Cursor, Hermes and more:",
  zum_anb="Go to {p} ↗", anleitung="Setup guide", alternativen="Other providers with the same models", gemeinsam="{n} shared models",
  th_modell="Model", th_preis="Input / output per 1M", th_platz="Arena (overall)", alle="All providers",
  idx_titel="AI API providers compared | aiapicompare", idx_desc="All AI API providers in our daily price check: number of models, cheapest prices and free models.",
  idx_h1="AI API providers", idx_lead="All providers in our daily price check – with number of models, free models and the cheapest text model.",
  th_anb="Provider", th_anz="Models", th_frei="Free", th_ab="Cheapest text model",
  hinweis="Facts from our own daily price check. Prices without guarantee – the provider’s website is authoritative.",
  auff_anb="{n} offers from {p} are far below the reference price (e.g. far below the vendor's list price). We cannot verify which model is actually served – check terms and privacy first and test with a small balance.", w_warn="⚠ Far below reference price – check first", w_ab="from", w_bei="at", w_anb="{n} providers", w_quelle="Prices: aiapicompare.com",
  nf_titel="Page not found", nf_text="This page does not exist (anymore). Maybe one of these helps:", nf_suche="Search for a model …"),
"de": dict(titel="{p} API-Preise: {n} KI-Modelle im Vergleich | aiapicompare", desc="{p}: Preise für {n} KI-Modelle per API, günstigste Modelle, kostenlose Modelle, Top-Modelle der Arena und Einrichtung (Base-URL). Täglich aktualisiert.",
  h1="{p}: API-Preise & Modelle", lead="{p} bietet in unserem täglichen Preisvergleich {n} Modelle{arten}. Unten: die günstigsten Modelle, die am besten bewerteten Modelle der Arena-Bestenliste und die Anbindung von {p}.",
  arten=" ({t})", text="Text", bild="Bild", video="Video", gratis_n="{n} kostenlos",
  k_modelle="Modelle", k_gratis="Kostenlose Modelle", k_ab="Günstigstes Textmodell", k_base="Base-URL",
  h_billig="Günstigste Textmodelle bei {p}", h_top="Am besten bewertete Modelle bei {p}", h_einr="{p} anbinden",
  einr_text="OpenAI-kompatibel: Base-URL unten mit deinem {p}-API-Schlüssel verwenden. Schritt-für-Schritt-Anleitungen für VS Code, Cline, Cursor, Hermes und mehr:",
  zum_anb="Zu {p} ↗", anleitung="Anleitung", alternativen="Andere Anbieter mit denselben Modellen", gemeinsam="{n} gemeinsame Modelle",
  th_modell="Modell", th_preis="Input / Output pro 1 Mio.", th_platz="Arena (Allround)", alle="Alle Anbieter",
  idx_titel="KI-API-Anbieter im Vergleich | aiapicompare", idx_desc="Alle KI-API-Anbieter in unserem täglichen Preisvergleich: Anzahl Modelle, günstigste Preise und kostenlose Modelle.",
  idx_h1="KI-API-Anbieter", idx_lead="Alle Anbieter in unserem täglichen Preisvergleich – mit Anzahl der Modelle, kostenlosen Modellen und dem günstigsten Textmodell.",
  th_anb="Anbieter", th_anz="Modelle", th_frei="Kostenlos", th_ab="Günstigstes Textmodell",
  hinweis="Fakten aus unserem eigenen täglichen Preisvergleich. Preise ohne Gewähr – maßgeblich ist die Seite des Anbieters.",
  auff_anb="{n} Angebote von {p} liegen weit unter dem Referenzpreis (z. B. weit unter dem Listenpreis des Herstellers). Wir können nicht prüfen, welches Modell tatsächlich geliefert wird – vorher Bedingungen und Datenschutz prüfen und mit kleinem Guthaben testen.", w_warn="⚠ Weit unter Referenzpreis – vorher prüfen", w_ab="ab", w_bei="bei", w_anb="{n} Anbieter", w_quelle="Preise: aiapicompare.com",
  nf_titel="Seite nicht gefunden", nf_text="Diese Seite gibt es nicht (mehr). Vielleicht hilft eine dieser Seiten weiter:", nf_suche="Modell suchen …"),
"zh": dict(titel="{p} API 价格：{n} 个 AI 模型对比 | aiapicompare", desc="{p}：{n} 个 AI 模型的 API 价格、最便宜的模型、免费模型、Arena 高分模型及接入方式（Base URL）。每日更新。",
  h1="{p}：API 价格与模型", lead="在我们的每日价格查询中，{p} 提供 {n} 个模型{arten}。下方列出最便宜的模型、Arena 排行榜评分最高的模型以及 {p} 的接入方式。",
  arten="（{t}）", text="文本", bild="图像", video="视频", gratis_n="{n} 个免费",
  k_modelle="模型", k_gratis="免费模型", k_ab="最便宜的文本模型", k_base="Base URL",
  h_billig="{p} 最便宜的文本模型", h_top="{p} 上评分最高的模型", h_einr="接入 {p}",
  einr_text="兼容 OpenAI：使用下方 Base URL 和你的 {p} API 密钥。VS Code、Cline、Cursor、Hermes 等的详细步骤：",
  zum_anb="前往 {p} ↗", anleitung="配置指南", alternativen="提供相同模型的其他提供商", gemeinsam="{n} 个相同模型",
  th_modell="模型", th_preis="每百万输入 / 输出", th_platz="Arena（综合）", alle="全部提供商",
  idx_titel="AI API 提供商对比 | aiapicompare", idx_desc="我们每日价格查询中的全部 AI API 提供商：模型数量、最低价格和免费模型。",
  idx_h1="AI API 提供商", idx_lead="我们每日价格查询中的全部提供商——含模型数量、免费模型和最便宜的文本模型。",
  th_anb="提供商", th_anz="模型数", th_frei="免费", th_ab="最便宜的文本模型",
  hinweis="数据来自我们自己的每日价格查询。价格仅供参考，以提供商网站为准。",
  auff_anb="{p} 有 {n} 个报价远低于参考价（例如远低于厂商官方价格）。我们无法核实实际提供的是哪个模型——使用前请查看条款和隐私政策，并先用少量余额测试。", w_warn="⚠ 远低于参考价——请先核实", w_ab="起", w_bei="于", w_anb="{n} 家提供商", w_quelle="价格：aiapicompare.com",
  nf_titel="页面不存在", nf_text="此页面不存在（或已删除）。以下页面或许有帮助：", nf_suche="搜索模型 …"),
"ru": dict(titel="{p}: цены API на {n} AI-моделей | aiapicompare", desc="{p}: цены на {n} AI-моделей через API, самые дешёвые и бесплатные модели, лучшие модели Arena и подключение (Base URL). Обновляется ежедневно.",
  h1="{p}: цены API и модели", lead="В нашей ежедневной проверке у {p} {n} моделей{arten}. Ниже: самые дешёвые модели, лучшие по рейтингу Arena и подключение {p}.",
  arten=" ({t})", text="текст", bild="изображения", video="видео", gratis_n="{n} бесплатно",
  k_modelle="Модели", k_gratis="Бесплатные модели", k_ab="Самая дешёвая текстовая модель", k_base="Base URL",
  h_billig="Самые дешёвые текстовые модели у {p}", h_top="Лучшие по рейтингу модели у {p}", h_einr="Подключение {p}",
  einr_text="Совместимо с OpenAI: используйте Base URL ниже и ваш API-ключ {p}. Пошаговые инструкции для VS Code, Cline, Cursor, Hermes и др.:",
  zum_anb="К {p} ↗", anleitung="Инструкция", alternativen="Другие поставщики с теми же моделями", gemeinsam="{n} общих моделей",
  th_modell="Модель", th_preis="Вход / выход за 1 млн", th_platz="Arena (в целом)", alle="Все поставщики",
  idx_titel="Поставщики AI API в сравнении | aiapicompare", idx_desc="Все поставщики AI API в нашей ежедневной проверке: число моделей, самые низкие цены и бесплатные модели.",
  idx_h1="Поставщики AI API", idx_lead="Все поставщики в нашей ежедневной проверке цен – число моделей, бесплатные модели и самая дешёвая текстовая модель.",
  th_anb="Поставщик", th_anz="Моделей", th_frei="Бесплатно", th_ab="Самая дешёвая текстовая модель",
  hinweis="Факты из нашей собственной ежедневной проверки цен. Цены без гарантии – действует информация на сайте поставщика.",
  auff_anb="{n} предложений {p} намного ниже эталонной цены (например, намного ниже прайса производителя). Мы не можем проверить, какая модель реально используется – заранее проверьте условия и конфиденциальность и протестируйте с небольшим балансом.", w_warn="⚠ Намного ниже эталонной цены – проверьте заранее", w_ab="от", w_bei="у", w_anb="{n} поставщ.", w_quelle="Цены: aiapicompare.com",
  nf_titel="Страница не найдена", nf_text="Такой страницы нет (больше нет). Возможно, поможет одна из этих:", nf_suche="Найти модель …"),
}

def anbieter_info(q):
    zeilen = [z for z in ZEILEN if z["q"] == q]
    slugs = sorted({z["slug"] for z in zeilen})
    arten = Counter("video" if "video" in z["typ"] else "bild" if ("bild" in z["typ"] or z["media"]) else "text" for z in zeilen)
    text = [z for z in zeilen if not z["media"] and 0 < z["preis"] < float("inf")]
    billig = sorted(text, key=lambda z: (z["preis"], z["name"]))
    return dict(q=q, zeilen=zeilen, slugs=slugs, arten=arten, billig=billig,
                gratis=[z for z in zeilen if z["gratis"]])

ANBIETER_INFOS = {q: anbieter_info(q) for q in ANBIETER if any(z["q"] == q for z in ZEILEN)}

def allround_platz(z):
    return ((STAERKEN.get("modelle") or {}).get(re.sub(r":free$", "", z["kanon"])) or {}).get("allround")

def anbieterseite(q, lang):
    t, v = T[lang], PV[lang]
    rel = "../" if lang == "en" else "../../"
    name, farbe, base, env = ANBIETER[q]
    info = ANBIETER_INFOS[q]
    n = len(info["slugs"])
    arten = ", ".join(f'{info["arten"][a]} {v[a]}' for a in ("text", "bild", "video") if info["arten"].get(a))
    h = kopf(lang, rel, v["titel"].format(p=name, n=n), v["desc"].format(p=name, n=n), f"providers/{q}.html")
    h += (f'<div class="bc"><a href="{rel}index.html">aiapicompare</a> › '
          f'<a href="{rel}{pfad(lang, "providers/index.html")}">{v["alle"]}</a> › {esc(name)}</div>\n')
    h += f'<h1><span class="dot" style="background:{farbe}"></span>{esc(v["h1"].format(p=name))}</h1>\n'
    h += f'<p class="lead">{esc(v["lead"].format(p=name, n=n, arten=v["arten"].format(t=arten) if arten else ""))}</p>\n'
    if ALT.get(q):
        h += f'<div class="hinweisbox">⏱ {esc(REF_T[lang]["alt_anb"].format(p=name, d=ref_datum(ALT[q]["seit"], lang)))}</div>\n'
    n_auff = sum(1 for z in info["zeilen"] if z["auff"])
    if n_auff:
        h += (f'<div class="hinweisbox">⚠ {esc(PV[lang]["auff_anb"].format(n=n_auff, p=name))} '
              f'<a href="{rel}methodik.html" style="color:inherit">{esc(REF_T[lang]["mehr"])}</a></div>\n')
    ab = info["billig"][0] if info["billig"] else None
    h += ('<div class="zahlen">'
          f'<div class="zahl"><span>{v["k_modelle"]}</span><b>{n}</b></div>'
          f'<div class="zahl"><span>{v["k_gratis"]}</span><b>{len(info["gratis"])}</b></div>'
          + (f'<div class="zahl"><span>{v["k_ab"]}</span><b>{esc(preis_text(ab, t))}</b></div>' if ab else "")
          + f'<div class="zahl"><span>{v["k_base"]}</span><b style="font-family:var(--mono);font-size:.85rem">{esc(base)}</b></div></div>\n')
    h += (f'<div class="rel"><a class="btn" data-anb="{q}" data-start="1" href="{STARTSEITE.get(q, "#")}" target="_blank" rel="noopener">'
          f'{esc(v["zum_anb"].format(p=name))}</a><a class="btn" href="{rel}anbindung.html#anbieter={q}">{v["anleitung"]}</a>'
          f'<a class="btn" href="{rel}index.html#anb={q}">{t["nav_vergleich"]}</a></div>\n')
    h += fakten_box(q, lang, rel)

    def tabelle(liste, mit_platz=False):
        x = (f'<div class="tablewrap" style="margin-top:.6rem"><table><thead><tr><th>{v["th_modell"]}</th><th class="num">{v["th_preis"]}</th>'
             + (f'<th class="num">{v["th_platz"]}</th>' if mit_platz else "") + '<th></th></tr></thead><tbody>')
        for z in liste:
            pin = t["gratis"] if z["gratis"] else fmt(z["inp"] if z["inp"] is not None else z["ab"])
            pout = t["gratis"] if z["gratis"] else fmt(z["out"]) if z["out"] is not None else "—"
            x += (f'<tr><td><a href="{rel}{pfad(lang, "models/" + z["slug"] + ".html")}">{esc(name_sauber(z["name"]))}</a>{ref_tags(dict(z, alt=None), lang)}'
                  f'<br><small style="color:var(--dim);font-family:var(--mono)">{esc(z["roh"])}</small></td>'
                  f'<td class="num price">{esc(pin) if z["gratis"] else esc(pin) + " / " + esc(pout)}</td>'
                  + (f'<td class="num">#{allround_platz(z)}</td>' if mit_platz else "")
                  + f'<td class="num">{go_link(z, t)}</td></tr>')
        return x + "</tbody></table></div>\n"

    if info["billig"]:
        h += f'<h2>{esc(v["h_billig"].format(p=name))}</h2>' + tabelle(info["billig"][:15])
    top = sorted((z for z in info["zeilen"] if allround_platz(z) and not z["media"]), key=lambda z: (allround_platz(z), z["preis"]))
    gesehen, top_eindeutig = set(), []
    for z in top:
        if z["slug"] not in gesehen:
            gesehen.add(z["slug"]); top_eindeutig.append(z)
    if top_eindeutig:
        meta = STAERKEN.get("meta") or {}
        h += f'<h2>{esc(v["h_top"].format(p=name))}</h2>' + tabelle(top_eindeutig[:15], mit_platz=True)
        h += (f'<p class="hint" style="font-size:.75rem;color:var(--dim)">'
              f'{t["arena_quelle"].format(stand=esc(meta.get("stand", "")), ds=meta.get("datensatz", ""), lz=meta.get("lizenz_url", ""))}</p>\n')
    h += f'<h2>{esc(v["h_einr"].format(p=name))}</h2><p>{esc(v["einr_text"].format(p=name))} <a href="{rel}anbindung.html#anbieter={q}">{v["anleitung"]} →</a></p>'
    h += "<pre>" + esc(f'from openai import OpenAI\nimport os\n\nclient = OpenAI(base_url="{base}", api_key=os.environ["{env}"])') + "</pre>\n"
    # Alternativen: andere Anbieter mit denselben Modellen
    meine = set(info["slugs"])
    alt = sorted(((o, len(meine & set(i["slugs"]))) for o, i in ANBIETER_INFOS.items() if o != q), key=lambda x: -x[1])
    alt = [(o, m) for o, m in alt if m > 0]
    if alt:
        h += f'<h2>{v["alternativen"]}</h2><div class="rel">' + "".join(
            f'<a class="btn" href="{o}.html"><span class="dot" style="background:{ANBIETER[o][1]}"></span>{esc(ANBIETER[o][0])} · {v["gemeinsam"].format(n=m)}</a>'
            for o, m in alt) + "</div>\n"
    h += f'<p style="font-size:.78rem;color:var(--dim)">{v["hinweis"]} {t["stand"].format(d=esc(STAND))}</p>'
    h += fuss(lang, rel)
    return h

# ------------------------------------------------------------------ Anbieter-Fakten (von Hand gepflegt: anbieter_info.json)
try:
    ANB_FAKTEN = json.loads((BASIS / "anbieter_info.json").read_text(encoding="utf-8"))
except (OSError, ValueError):
    ANB_FAKTEN = {}

FAKT_T = {
    "de": dict(h="Auf einen Blick", firma="Unternehmen und Sitz", zahlung="Zahlungsarten", minimum="Mindestaufladung", gebuehr="Gebühren",
               speichert="Speichert Prompts", training="Training mit deinen Daten", daten="Datenschutz", quellen="Quellen",
               hinweis="Laut Angaben des Anbieters, geprüft am {d} – ohne Gewähr. Bedingungen können sich ändern; maßgeblich sind die Seiten des Anbieters.",
               h_vergl="Bedingungen im Vergleich", sitz="Sitz", melden="Fehler melden",
               z=dict(karte="Karte", alipay="Alipay", krypto="Krypto", sbp="SBP (Russland)", bank="Überweisung", tao="TAO (Bittensor)", rechnung="Rechnung"),
               s=dict(nein="Nein (laut Anbieter)", optin="Nur wenn eingeschaltet", ja="Ja", unklar="Keine klare Angabe"),
               tr=dict(nein="Nein (laut Anbieter)", nein_ausnahmen="Nein (mit Ausnahmen)", unklar="Keine Angabe")),
    "en": dict(h="At a glance", firma="Company and location", zahlung="Payment methods", minimum="Minimum top-up", gebuehr="Fees",
               speichert="Stores prompts", training="Training on your data", daten="Data handling", quellen="Sources",
               hinweis="Based on the provider’s own information, checked on {d} – without guarantee. Terms may change; the provider’s pages prevail.",
               h_vergl="Terms compared", sitz="Location", melden="Report an error",
               z=dict(karte="Card", alipay="Alipay", krypto="Crypto", sbp="SBP (Russia)", bank="Bank transfer", tao="TAO (Bittensor)", rechnung="Invoice"),
               s=dict(nein="No (per provider)", optin="Only if you opt in", ja="Yes", unklar="Not clearly stated"),
               tr=dict(nein="No (per provider)", nein_ausnahmen="No (with exceptions)", unklar="Not stated")),
    "zh": dict(h="概览", firma="公司与所在地", zahlung="支付方式", minimum="最低充值", gebuehr="手续费",
               speichert="是否保存提示词", training="用你的数据训练", daten="数据处理", quellen="来源",
               hinweis="依据提供商自身信息，核查日期 {d}——不作保证。条款可能变化，以提供商页面为准。",
               h_vergl="条款对比", sitz="所在地", melden="报告错误",
               z=dict(karte="银行卡", alipay="支付宝", krypto="加密货币", sbp="SBP（俄罗斯）", bank="银行转账", tao="TAO（Bittensor）", rechnung="发票结算"),
               s=dict(nein="否（据提供商）", optin="仅在你开启时", ja="是", unklar="未明确说明"),
               tr=dict(nein="否（据提供商）", nein_ausnahmen="否（有例外）", unklar="未说明")),
    "ru": dict(h="Коротко", firma="Компания и местонахождение", zahlung="Способы оплаты", minimum="Минимальное пополнение", gebuehr="Комиссии",
               speichert="Хранит промпты", training="Обучение на ваших данных", daten="Обработка данных", quellen="Источники",
               hinweis="По данным поставщика, проверено {d} – без гарантии. Условия могут меняться; действуют страницы поставщика.",
               h_vergl="Сравнение условий", sitz="Местонахождение", melden="Сообщить об ошибке",
               z=dict(karte="Карта", alipay="Alipay", krypto="Криптовалюта", sbp="СБП", bank="Банковский перевод", tao="TAO (Bittensor)", rechnung="Счёт"),
               s=dict(nein="Нет (по данным поставщика)", optin="Только при включении", ja="Да", unklar="Нет чёткой информации"),
               tr=dict(nein="Нет (по данным поставщика)", nein_ausnahmen="Нет (с исключениями)", unklar="Не указано")),
}

def _fakt(q):
    return (ANB_FAKTEN.get("anbieter") or {}).get(q)

def _zahlung_text(f, lang):
    ft = FAKT_T[lang]
    teile = [ft["z"].get(z, z) for z in f.get("zahlung") or []]
    hinweis = (f.get("zahlung_hinweis") or {}).get(lang)
    return hinweis or ", ".join(teile) or "—"      # ein Hinweis ist vollständig formuliert und ersetzt die Liste

def _quelle_kurz(u):
    x = urllib.parse.urlsplit(u)
    return (x.netloc.replace("www.", "") + x.path).rstrip("/")

def fakten_box(q, lang, rel):
    f = _fakt(q)
    if not f:
        return ""
    ft = FAKT_T[lang]
    firma = (esc(f["firma"]) + " · " if f.get("firma") else "") + esc(f["sitz"][lang])
    zeilen = [(ft["firma"], firma), (ft["zahlung"], esc(_zahlung_text(f, lang))), (ft["minimum"], esc(f["minimum"][lang])),
              (ft["gebuehr"], esc(f["gebuehr"][lang])), (ft["speichert"], esc(ft["s"].get(f["speichert"], "—"))),
              (ft["training"], esc(ft["tr"].get(f["training"], "—"))), (ft["daten"], esc(f["daten"][lang])),
              (ft["quellen"], " · ".join(f'<a href="{esc(u)}" target="_blank" rel="nofollow noopener">{esc(_quelle_kurz(u))}</a>' for u in f.get("quellen", [])))]
    betreff = urllib.parse.quote(f"Anbieter-Angaben / provider info: {ANBIETER[q][0]}")
    return (f'<h2>{ft["h"]}</h2><div class="tablewrap"><table class="fakten"><tbody>'
            + "".join(f'<tr><th>{k}</th><td>{v}</td></tr>' for k, v in zeilen)
            + f'</tbody></table></div><p class="refzeile">{esc(ft["hinweis"].format(d=ref_datum(ANB_FAKTEN.get("stand", ""), lang)))} '
            f'<a href="mailto:kontakt@aiapicompare.com?subject={betreff}">{esc(ft["melden"])}</a></p>\n')

def fakten_vergleich(lang):
    if not ANB_FAKTEN.get("anbieter"):
        return ""
    ft = FAKT_T[lang]
    h = (f'<h2>{ft["h_vergl"]}</h2><div class="tablewrap"><table><thead><tr><th></th><th>{ft["sitz"]}</th><th>{ft["zahlung"]}</th>'
         f'<th>{ft["minimum"]}</th><th>{ft["speichert"]}</th><th>{ft["training"]}</th></tr></thead><tbody>')
    for q in ANBIETER:
        f = _fakt(q)
        if not f:
            continue
        name_html = f'<span class="dot" style="background:{ANBIETER[q][1]}"></span>{esc(ANBIETER[q][0])}'
        if q in ANBIETER_INFOS:          # Anbieter-Seite gibt es nur, wenn der Anbieter Daten geliefert hat
            name_html = f'<a href="{q}.html">{name_html}</a>'
        h += (f'<tr><td style="white-space:nowrap">{name_html}</td>'
              f'<td>{esc(f["sitz"][lang])}</td><td>{esc(_zahlung_text(f, lang))}</td><td>{esc(f["minimum"][lang])}</td>'
              f'<td>{esc(ft["s"].get(f["speichert"], "—"))}</td><td>{esc(ft["tr"].get(f["training"], "—"))}</td></tr>')
    return h + (f'</tbody></table></div><p class="refzeile">{esc(ft["hinweis"].format(d=ref_datum(ANB_FAKTEN.get("stand", ""), lang)))} '
                f'<a href="../{"" if lang == "en" else "../"}methodik.html">{esc(REF_T[lang]["mehr"])}</a></p>\n')

def anbieterindex(lang):
    t, v = T[lang], PV[lang]
    rel = "../" if lang == "en" else "../../"
    h = kopf(lang, rel, v["idx_titel"], v["idx_desc"], "providers/index.html")
    h += f'<h1>{v["idx_h1"]}</h1><p class="lead">{v["idx_lead"]}</p>'
    h += (f'<div class="tablewrap"><table><thead><tr><th>{v["th_anb"]}</th><th class="num">{v["th_anz"]}</th>'
          f'<th class="num">{v["th_frei"]}</th><th>{v["th_ab"]}</th></tr></thead><tbody>')
    for q, info in sorted(ANBIETER_INFOS.items(), key=lambda x: -len(x[1]["slugs"])):
        ab = info["billig"][0] if info["billig"] else None
        alt_tag = ""
        if ALT.get(q):
            d = ref_datum(ALT[q]["seit"], lang)
            alt_tag = f'<span class="tag alt" title="{esc(REF_T[lang]["alt_titel"].format(d=d))}">{esc(REF_T[lang]["alt_tag"].format(d=d))}</span>'
        h += (f'<tr><td><a href="{q}.html"><span class="dot" style="background:{ANBIETER[q][1]}"></span>{esc(ANBIETER[q][0])}</a>{alt_tag}</td>'
              f'<td class="num">{len(info["slugs"])}</td><td class="num">{len(info["gratis"])}</td>'
              f'<td>{(esc(name_sauber(ab["name"])) + " · <span class=price>" + esc(preis_text(ab, t)) + "</span>" + ref_tags(dict(ab, alt=None), lang)) if ab else "—"}</td></tr>')
    h += f'</tbody></table></div><p style="font-size:.78rem;color:var(--dim)">{v["hinweis"]} {t["stand"].format(d=esc(STAND))}</p>'
    h += fakten_vergleich(lang)
    h += fuss(lang, rel)
    return h

def widgetseite(info):
    """Kleine, einbettbare Preisbox (iframe). Sprache über ?lang=de|en|zh|ru, Standard Englisch."""
    b = bezahlt_billig(info) or info["billig_ok"]
    warn = bool(b["auff"])
    def vor(l):
        pt = preis_text(b, T[l])
        return "" if b["gratis"] or pt.startswith(T[l]["ab"] + " ") else PV[l]["w_ab"] + " "
    texte = {l: dict(ab=vor(l), bei=PV[l]["w_bei"], anb=PV[l]["w_anb"].format(n=info["anbieter"]), quelle=PV[l]["w_quelle"],
                     warn=PV[l]["w_warn"] if warn else "",
                     preis=preis_text(b, T[l]), gratis=T[l]["gratis"]) for l in SPRACHEN}
    return f'''<!DOCTYPE html>
<html lang="en"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="robots" content="noindex"><link rel="icon" href="data:,"><title>{esc(info["name"])} – aiapicompare</title>
<style>
  html,body{{margin:0;background:transparent;font-family:system-ui,-apple-system,"Segoe UI",Roboto,sans-serif}}
  a.box{{display:block;box-sizing:border-box;max-width:340px;padding:12px 14px;border:1px solid #d8dde3;border-radius:10px;background:#fff;color:#0f172a;text-decoration:none}}
  a.box:hover{{border-color:#16a34a}}
  .n{{font-weight:700;font-size:15px}} .p{{font-size:20px;font-weight:800;color:#16a34a;margin:4px 0;font-family:ui-monospace,Consolas,monospace}}
  .m{{font-size:12px;color:#64748b}} .q{{font-size:11px;color:#94a3b8;margin-top:6px}}
  @media (prefers-color-scheme:dark){{a.box{{background:#121418;color:#e8e9eb;border-color:#2e323a}} .p{{color:#4ade80}}}}
  body.hell a.box{{background:#fff;color:#0f172a;border-color:#d8dde3}} body.hell .p{{color:#16a34a}}
  body.dunkel a.box{{background:#121418;color:#e8e9eb;border-color:#2e323a}} body.dunkel .p{{color:#4ade80}}
</style></head>
<body><a class="box" id="box" target="_blank" rel="noopener" href="{DOMAIN}models/{info["slug"]}.html">
<div class="n">{esc(info["name"])}</div><div class="p" id="p"></div><div class="m" id="m"></div><div class="q" id="q"></div></a>
<script>
(function(){{
  var T = {json.dumps(texte, ensure_ascii=False)};
  var s = new URLSearchParams(location.search), l = s.get("lang"); if (!T[l]) l = "en";
  var t = T[l]; document.documentElement.lang = l;
  document.getElementById("p").textContent = t.ab + t.preis;
  document.getElementById("m").textContent = t.bei + " {esc(b["quelle"])} · " + t.anb;
  document.getElementById("q").textContent = t.warn ? t.warn + " · " + t.quelle : t.quelle;
  if (l !== "en") document.getElementById("box").href = "{DOMAIN}" + l + "/models/{info["slug"]}.html";
  if (s.get("theme") === "light") document.body.className = "hell"; else if (s.get("theme") === "dark") document.body.className = "dunkel";
}})();
</script></body></html>
'''

def seite_404():
    """Eigene Fehlerseite; GitHub Pages liefert sie für jede unbekannte Adresse aus (daher absolute Pfade)."""
    texte = {l: dict(titel=PV[l]["nf_titel"], text=PV[l]["nf_text"], suche=PV[l]["nf_suche"], v=T[l]["nav_vergleich"],
                     k=T[l]["nav_kosten"], g=T[l]["nav_gratis"], b=T[l]["nav_best"], n=T[l]["nav_news"], a=T[l]["alle_modelle"],
                     c=VS[l]["alle"], p=PV[l]["alle"], f=T[l]["nav_finder"], pf=("" if l == "en" else l + "/"),
                     im=T[l]["impressum"], ds=T[l]["datenschutz"]) for l in SPRACHEN}
    return f'''<!DOCTYPE html>
<html lang="en"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="robots" content="noindex"><title>404 – aiapicompare</title>
<link rel="icon" href="/favicon.svg" type="image/svg+xml"><link rel="stylesheet" href="/style.css"><script src="/theme.js"></script>
<style>.nf{{max-width:720px;margin:3rem auto;padding:0 1.25rem;text-align:center}} .nf .gross{{font-size:4rem;font-weight:800;color:var(--accent);line-height:1}}
.nf form{{display:flex;gap:.5rem;margin:1.5rem auto;max-width:460px}} .nf input{{flex:1;padding:.6rem .8rem;border:1px solid var(--border2);border-radius:.5rem;background:var(--input);color:var(--fg);font-size:1rem}}
.nf .rel{{display:flex;flex-wrap:wrap;gap:.45rem;justify-content:center}}</style></head>
<body><div class="topbar"><a class="brand" href="/" aria-label="aiapicompare"><img class="logo-d" src="/logo/logo.svg" alt="aiapicompare" width="166" height="30"><img class="logo-l" src="/logo/logo-hell.svg" alt="aiapicompare" width="166" height="30"></a>
<button class="themebtn" title="Light / dark"><span class="ti-l">☀</span><span class="ti-d">☾</span></button></div>
<div class="nf"><div class="gross">404</div><h1 id="t"></h1><p id="x" style="color:var(--muted)"></p>
<form action="/index.html" id="f"><input id="q" type="search" autocomplete="off"><button class="btn" type="submit">→</button></form>
<div class="rel" id="links"></div>
<div class="legal" style="justify-content:center;margin-top:2.5rem"><a href="/impressum.html" id="li"></a><a href="/datenschutz.html" id="ld"></a></div></div>
<script>
(function(){{
  var T = {json.dumps(texte, ensure_ascii=False)};
  var l = (location.pathname.match(/^\\/(de|zh|ru)\\//) || [])[1];
  try {{ l = l || localStorage.getItem("lang"); }} catch(e) {{}}
  l = l || (navigator.language || "en").slice(0, 2); if (!T[l]) l = "en";
  var t = T[l]; document.documentElement.lang = l;
  document.getElementById("t").textContent = t.titel; document.getElementById("x").textContent = t.text;
  document.getElementById("q").placeholder = t.suche;
  document.getElementById("f").addEventListener("submit", function(e){{ e.preventDefault(); location.href = "/index.html#q=" + encodeURIComponent(document.getElementById("q").value); }});
  var L = [["/", t.v], ["/kosten.html", t.k], ["/finder.html", t.f], ["/bestenliste.html", t.b], ["/news.html", t.n],
           ["/" + t.pf + "free.html", t.g], ["/" + t.pf + "models/index.html", t.a], ["/" + t.pf + "compare/index.html", t.c], ["/" + t.pf + "providers/index.html", t.p]];
  document.getElementById("links").innerHTML = L.map(function(x){{ return '<a class="btn" href="' + x[0] + '">' + x[1] + '</a>'; }}).join("");
  document.getElementById("li").textContent = t.im; document.getElementById("ld").textContent = t.ds;
}})();
</script>
<script src="/config.js"></script>
<script src="/einwilligung.js"></script>
</body></html>
'''

# ------------------------------------------------------------------ Ausgabe
def schreibe(rel_pfad, inhalt):
    p = ZIEL / rel_pfad
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(inhalt, encoding="utf-8")

def main():
    ZIEL.mkdir(parents=True, exist_ok=True)
    for f in STATISCH:
        if (BASIS / f).exists():
            shutil.copy2(BASIS / f, ZIEL / f)
    if (BASIS / "logo").exists():
        shutil.copytree(BASIS / "logo", ZIEL / "logo", dirs_exist_ok=True)
        (ZIEL / "logo" / "logo-uebersicht.png").unlink(missing_ok=True)
    (ZIEL / "out").mkdir(exist_ok=True)
    shutil.copy2(BASIS / "out" / "data.js", ZIEL / "out" / "data.js")
    with open(ZIEL / "out" / "data.js", "a", encoding="utf-8") as f:   # Kennzeichen: Modellseiten existieren
        f.write("window.MODELLSEITEN = true;\n")
    for f in ("staerken.js", "news.js", "preisindex.js"):
        if (BASIS / "out" / f).exists():
            shutil.copy2(BASIS / "out" / f, ZIEL / "out" / f)
    (ZIEL / "api").mkdir(exist_ok=True)
    if (BASIS / "out" / "prices.json").exists():
        shutil.copy2(BASIS / "out" / "prices.json", ZIEL / "api" / "prices.json")
    else:
        (ZIEL / "api" / "prices.json").write_text(json.dumps(D, ensure_ascii=False), encoding="utf-8")

    for lang in SPRACHEN:
        for q in ANBIETER_INFOS:
            schreibe(pfad(lang, f"providers/{q}.html"), anbieterseite(q, lang))
        schreibe(pfad(lang, "providers/index.html"), anbieterindex(lang))
    for s_, info in INFOS.items():
        schreibe(f"widget/{s_}.html", widgetseite(info))
    schreibe("404.html", seite_404())
    for lang in SPRACHEN:
        schreibe(pfad(lang, "feed.xml"), feed(lang))
    schreibe("llms.txt", llms_txt())
    for f in BASIS.glob("*.txt"):                       # IndexNow-Schlüsseldatei (32 Hex-Zeichen)
        if re.fullmatch(r"[0-9a-f]{32}\.txt", f.name):
            shutil.copy2(f, ZIEL / f.name)

    urls = []   # (Pfad ohne Sprache, Sprachen, Häufigkeit, Priorität)
    for lang in SPRACHEN:
        for s, info in INFOS.items():
            schreibe(pfad(lang, f"models/{s}.html"), modellseite(info, lang))
        schreibe(pfad(lang, "free.html"), gratisseite(lang))
        schreibe(pfad(lang, "models/index.html"), verzeichnis(lang))
        if VS_PAARE:
            for g, a, b in VS_PAARE:
                schreibe(pfad(lang, f"compare/{vs_slug(a, b)}.html"), vergleichsseite(g, a, b, lang))
            schreibe(pfad(lang, "compare/index.html"), vergleichsindex(lang))
    urls += [(f"models/{s}.html", True, "daily", "0.7") for s in INFOS]
    urls += [("free.html", True, "daily", "0.9"), ("models/index.html", True, "daily", "0.8")]
    urls += [(f"providers/{q}.html", True, "daily", "0.8") for q in ANBIETER_INFOS] + [("providers/index.html", True, "daily", "0.8")]
    if VS_PAARE:
        urls += [(f"compare/{vs_slug(a, b)}.html", True, "daily", "0.7") for g, a, b in VS_PAARE]
        urls += [("compare/index.html", True, "daily", "0.8")]

    # Sitemap mit Sprachvarianten
    x = ['<?xml version="1.0" encoding="UTF-8"?>',
         '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" xmlns:xhtml="http://www.w3.org/1999/xhtml">']
    for loc, prio in [("", "1.0"), ("kosten.html", "0.9"), ("finder.html", "0.9"), ("bestenliste.html", "0.9"), ("news.html", "0.8"),
                      ("preisindex.html", "0.8"), ("einbetten.html", "0.5"), ("methodik.html", "0.6"), ("anbindung.html", "0.8")]:
        x.append(f"  <url><loc>{DOMAIN}{loc}</loc><changefreq>daily</changefreq><priority>{prio}</priority></url>")
    for rest, mehrsprachig, freq, prio in urls:
        alts = "".join(f'<xhtml:link rel="alternate" hreflang="{T[l]["htmllang"]}" href="{DOMAIN}{pfad(l, rest)}"/>' for l in SPRACHEN)
        for l in SPRACHEN:
            x.append(f"  <url><loc>{DOMAIN}{pfad(l, rest)}</loc>{alts}<changefreq>{freq}</changefreq><priority>{prio}</priority></url>")
    x.append("</urlset>")
    (ZIEL / "sitemap.xml").write_text("\n".join(x), encoding="utf-8")
    print(f"Vergleichsseiten: {len(VS_PAARE)} Paare × {len(SPRACHEN)} Sprachen")
    print(f"Website in {ZIEL}: {len(INFOS)} Modelle × {len(SPRACHEN)} Sprachen, "
          f"{sum(1 for z in ZEILEN if z['gratis'])} kostenlose Modelle, Sitemap mit {len(x) - 3} Adressen")

if __name__ == "__main__":
    main()
