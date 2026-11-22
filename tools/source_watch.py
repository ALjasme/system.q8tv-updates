"""Checks every outside source system.q8tv depends on; prints a report and exits 1 when any is broken.
Run daily by .github/workflows/source-watch.yml, which keeps one GitHub issue open while something is broken."""
import datetime, json, re, sys, urllib.request, xml.etree.ElementTree as ET

UA = {"User-Agent": "Mozilla/5.0 (system.q8tv source watch)"}
LAT, LON = 29.3759, 47.9774

def get(url, data=None, headers=None, limit=2_000_000):
    req = urllib.request.Request(url, data=data, headers={**UA, **(headers or {})})
    with urllib.request.urlopen(req, timeout=25) as r:
        return r.read(limit)

def j(url, **kw): return json.loads(get(url, **kw))

tomorrow = (datetime.datetime.utcnow() + datetime.timedelta(hours=27)).date().isoformat()
CHECKS = {
    "تقويم العجيري (مواقيت الصلاة)": lambda: len(re.findall(r'data-time="\d\d:\d\d', json.loads(get(
        f"https://www.alojeiri.com/ar/ojeiri-calendar?country_id=1&date={tomorrow}", headers={"X-Requested-With": "XMLHttpRequest"}))["html"])) == 6,
    "وزارة الأوقاف (خطبة الجمعة)": lambda: "خطبة-الجمعة" in get("https://www.awqaf.gov.kw/").decode("utf-8", "ignore"),
    "الطقس Open-Meteo": lambda: len(j(f"https://api.open-meteo.com/v1/forecast?latitude={LAT}&longitude={LON}&hourly=apparent_temperature&minutely_15=precipitation&forecast_days=1")["minutely_15"]["time"]) > 10,
    "الغبار Open-Meteo": lambda: "dust" in j(f"https://air-quality-api.open-meteo.com/v1/air-quality?latitude={LAT}&longitude={LON}&current=dust")["current"],
    "البحر Open-Meteo": lambda: "wave_height" in j(f"https://marine-api.open-meteo.com/v1/marine?latitude={LAT}&longitude={LON}&current=wave_height")["current"],
    "الأرصاد الكويتية (النشرة)": lambda: "الكويت" in get("https://www.met.gov.kw/Forecasts/kuwait.php?lang=ara").decode("utf-8", "ignore"),
    "الأرصاد الكويتية (التحذيرات)": lambda: ET.fromstring(get("https://www.met.gov.kw/XML/cap.xml")) is not None,
    "الزلازل USGS": lambda: "features" in j("https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/2.5_day.geojson"),
    "الأسهم (TradingView)": lambda: j("https://scanner.tradingview.com/kuwait/scan", data=json.dumps({"columns": ["close"], "range": [0, 1]}).encode(),
                                    headers={"Content-Type": "application/json"})["totalCount"] > 0,
    "الرسوم البيانية (Yahoo)": lambda: j("https://query1.finance.yahoo.com/v8/finance/chart/%5EGSPC?range=5d&interval=1d")["chart"]["result"] is not None,
    "المباريات ESPN": lambda: "events" in j("https://site.api.espn.com/apis/site/v2/sports/soccer/eng.1/scoreboard"),
    "الفرق TheSportsDB": lambda: "teams" in j("https://www.thesportsdb.com/api/v1/json/123/searchteams.php?t=Arsenal"),
    "القرّاء mp3quran": lambda: len(j("https://www.mp3quran.net/api/v3/reciters?language=ar")["reciters"]) > 50,
    "تلاوات mp3quran": lambda: len(get("https://cdn.mp3quran.net/audio/mishary-alafasy/r1/001.mp3", limit=2048)) == 2048,
    "آيات everyayah (الرقية)": lambda: len(get("https://everyayah.com/data/Alafasy_128kbps/001001.mp3", limit=2048)) == 2048,
    "الإذاعات qurango": lambda: len(get("https://backup.qurango.net/radio/mix", limit=4096)) == 4096,
    "التفسير alquran.cloud": lambda: j("https://api.alquran.cloud/v1/ayah/2:255/ar.muyassar")["code"] == 200,
    "الطائرات adsb.lol": lambda: "ac" in j(f"https://api.adsb.lol/v2/point/{LAT}/{LON}/50"),
    "الأخبار (BBC)": lambda: b"<rss" in get("https://feeds.bbci.co.uk/arabic/rss.xml"),
    "الأخبار (الراي)": lambda: b"<rss" in get("https://www.alraimedia.com/rssFeed/0"),
    "الأخبار (سكاي نيوز)": lambda: b"<rss" in get("https://www.skynewsarabia.com/rss"),
    "محطة الفضاء (iss.json)": lambda: (datetime.datetime.now(datetime.timezone.utc) - datetime.datetime.strptime(
        j("https://raw.githubusercontent.com/ALjasme/system.q8tv-updates/main/iss.json")["updated"], "%Y-%m-%dT%H:%MZ").replace(tzinfo=datetime.timezone.utc)).days < 2,
    "نفط برنت (السوق صباحًا)": lambda: j("https://scanner.tradingview.com/futures/scan", data=json.dumps({"symbols": {"tickers": ["ICEEUR:BRN1!"]}, "columns": ["close", "change"]}).encode(),
                                    headers={"Content-Type": "application/json"})["totalCount"] == 1,
    "الذهب والدولار (الغرام بالدينار)": lambda: j("https://scanner.tradingview.com/forex/scan", data=json.dumps({"symbols": {"tickers": ["FX_IDC:USDKWD"]}, "columns": ["close"]}).encode(),
                                    headers={"Content-Type": "application/json"})["totalCount"] == 1,
    "ألوان التجويد (مؤسسة القرآن)": lambda: "<rule class=" in json.dumps(j("https://api.quran.com/api/v4/verses/by_page/2?words=true&word_fields=text_uthmani_tajweed&per_page=3"), ensure_ascii=False),
    "توقيت الكلمات (مؤسسة القرآن)": lambda: len(j("https://api.quran.com/api/v4/chapter_recitations/7/1?segments=true")["audio_file"]["timestamps"]) == 7,
    "رزنامة وزارة التربية": lambda: "امتحان نهاية الفصل الدراسي" in __import__("html").unescape(get("https://www.moe.edu.kw/pages/calendar").decode("utf-8", "ignore")),
    "قنوات IPTV": lambda: get("https://raw.githubusercontent.com/ALjasme/klight-iptv/main/playlist.m3u", limit=64).startswith(b"#EXTM3U"),
}

broken = []
import time
for name, check in CHECKS.items():
    for attempt in (1, 2):   # a passing hiccup is not a broken source
        try:
            ok = bool(check())
            why = "" if ok else "رد غير متوقع"
        except Exception as e:
            ok, why = False, type(e).__name__ + ": " + str(e)[:120]
        if ok: break
        time.sleep(8)
    print(("✅ " if ok else "❌ ") + name + ("" if ok else " — " + why))
    if not ok: broken.append(f"- **{name}**: {why}")
with open("source_report.md", "w") as f:
    f.write("\n".join(broken))
sys.exit(1 if broken else 0)
