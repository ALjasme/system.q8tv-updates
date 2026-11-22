#!/usr/bin/env python3
"""Adds new Kuwait photos for the system.q8tv home screen, a few each month.

Takes the next photos of photos/queue.json: Wikimedia Commons photographs of Kuwait reviewed by eye (no people)
and freely licensed (CC0, public domain, CC BY, CC BY-SA), at least 3840 px wide; the licence is checked again
before each is published. candidates() lists new ones to review when the queue runs low. Each is
cropped to 16:9 and scaled to 3840x2160 (BY-SA works stay under BY-SA), published as an asset of the month's
GitHub release, and listed with its author, licence and source in photos/photos.json, which the TVs read.

Run by .github/workflows/monthly-photos.yml on the 1st of each month; also by hand: tools/monthly_photos.py OUT_DIR
"""
import hashlib, io, json, os, re, sys, time, urllib.parse, urllib.request
from PIL import Image

PER_MONTH = 6
# when the reviewed queue is used up: only these photographers' views of buildings and places (their Kuwait sets are
# architecture without crowds), so the library keeps growing every month
TRUSTED = {'Zairon', 'Diego Delso'}
PLACES = re.compile(r'(mosque|tower|skyline|harbou?r|beach|park|palace|museum|souq|bridge|marina|island|desert|corniche|fort|gate|sunset|night)', re.I)
API = 'https://commons.wikimedia.org/w/api.php'
UA = 'system.q8tv-photos/1.0 (https://github.com/ALjasme/system.q8tv-updates)'
SEARCHES = [
    'incategory:"Quality_images_of_Kuwait" filemime:image/jpeg',
    'deepcategory:"Kuwait City" filew:>3800 filemime:image/jpeg',
    'deepcategory:"Mosques in Kuwait" filew:>3800 filemime:image/jpeg',
    'deepcategory:"Kuwait Towers" filew:>3800 filemime:image/jpeg',
    'deepcategory:"Failaka Island" filew:>3800 filemime:image/jpeg',
]
LICENCES = re.compile(r'^(CC0|Public domain|PD|CC BY(-SA)? [0-9.]+)', re.I)
PEOPLE = re.compile(r'\b(girl|boy|man|men|woman|women|people|person|portrait|selfie|child|children|kid|family|crowd|'
                    r'football|f[uú]tbol|player|wedding|bride|ni[nñ]o|ni[nñ]a|hombre|mujer|personas|gente|retrato|'
                    r'reading the quran|worshipp?ers?|prayer|praying|funeral|protest|soldier|police|lizard|monitor|agama|'
                    r'mercado|market|interior of a shop)\b', re.I)

def get(params):
    q = urllib.parse.urlencode({**params, 'format': 'json', 'formatversion': 2})
    req = urllib.request.Request(API + '?' + q, headers={'User-Agent': UA})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.load(r)

def candidates():
    seen = {}
    for s in SEARCHES:
        d = get({'action': 'query', 'generator': 'search', 'gsrsearch': s, 'gsrnamespace': 6, 'gsrlimit': 200,
                 'prop': 'imageinfo|categories', 'cllimit': 'max', 'iiprop': 'url|size|extmetadata', 'iiurlwidth': 3840})
        for p in d.get('query', {}).get('pages', []):
            seen.setdefault(p['title'], (p, 'Quality_images' in s))
        time.sleep(1)
    return seen.values()

def plain(html):
    return re.sub(r'\s+', ' ', re.sub(r'<[^>]+>', '', html or '')).strip()

def suitable(p, skip):
    title = p['title'][5:]
    if title in skip: return None
    ii = (p.get('imageinfo') or [None])[0]
    if not ii: return None
    w, h = ii['width'], ii['height']
    if w < 3840 or not (1.3 <= w / h <= 1.78): return None   # 3840 wide must still give 2160 high after the 16:9 crop
    meta = ii.get('extmetadata', {})
    lic = plain(meta.get('LicenseShortName', {}).get('value'))
    if not LICENCES.match(lic) or 'NC' in lic or 'ND' in lic: return None
    cats = ' '.join(c['title'] for c in p.get('categories', []))
    text = title + ' ' + cats + ' ' + plain(meta.get('ImageDescription', {}).get('value'))
    if PEOPLE.search(text): return None
    author = plain(meta.get('Artist', {}).get('value')) or 'Wikimedia Commons'
    return {'title': re.sub(r'\.jpe?g$', '', title, flags=re.I), 'author': author[:80], 'license': lic,
            'source': ii['descriptionurl'], 'thumb': ii.get('thumburl') or ii['url'], 'pixels': w * h}

def fetch(url):
    req = urllib.request.Request(url, headers={'User-Agent': UA})
    with urllib.request.urlopen(req, timeout=120) as r:
        return r.read()

def to_uhd(data):
    im = Image.open(io.BytesIO(data)).convert('RGB')
    w, h = im.size
    if w / h > 16 / 9: nw = round(h * 16 / 9); im = im.crop(((w - nw) // 2, 0, (w - nw) // 2 + nw, h))
    else: nh = round(w * 9 / 16); im = im.crop((0, (h - nh) // 2, w, (h - nh) // 2 + nh))
    if im.size[1] < 2000: return None
    im = im.resize((3840, 2160), Image.LANCZOS)
    out = io.BytesIO()
    im.save(out, 'WEBP', quality=82, method=6)   # the TVs read WebP since v2611; a third the size of JPEG
    return out.getvalue()

WORDS = [('Grand Mosque', 'المسجد الكبير'), ('Mosque', 'مسجد'), ('Kuwait Towers', 'أبراج الكويت'), ('Liberation Tower', 'برج التحرير'),
         ('Skyline', 'أفق المدينة'), ('Harbour', 'الميناء'), ('Beach', 'الشاطئ'), ('Park', 'حديقة'), ('Palace', 'قصر'), ('Museum', 'متحف'),
         ('Souq', 'السوق'), ('Night', 'ليلًا'), ('Sunset', 'الغروب'), ('Island', 'جزيرة'), ('Kuwait City', 'مدينة الكويت')]

def title_ar(title):
    """A short Arabic caption from the file's English title (only for photos added without a reviewed one)."""
    hits = [ar for en, ar in WORDS if en.lower() in title.lower()]
    seen = []
    for h in hits:
        if not any(h in x for x in seen): seen.append(h)
    return ' · '.join(seen[:3]) or 'من الكويت'

def info(title):
    d = get({'action': 'query', 'titles': 'File:' + title, 'prop': 'imageinfo|categories', 'cllimit': 'max',
             'iiprop': 'url|size|extmetadata', 'iiurlwidth': 3840})
    return d['query']['pages'][0]

def main(out_dir, repo_dir):
    """Publishes the next approved photos of photos/queue.json; with the queue used up it adds nothing."""
    os.makedirs(out_dir, exist_ok=True)
    listing_path = os.path.join(repo_dir, 'photos', 'photos.json')
    listing = json.load(open(listing_path)) if os.path.exists(listing_path) else {'photos': []}
    queue = json.load(open(os.path.join(repo_dir, 'photos', 'queue.json')))['queue']
    done = {p['commons'] for p in listing['photos']}
    month = time.strftime('%Y-%m')
    if any(p['month'] == month for p in listing['photos']):
        print('already added this month'); return []
    picks = []
    skip = set()
    try: skip = {l.strip()[5:] for l in open(os.path.join(repo_dir, 'photos', 'skip.txt')) if l.startswith('File:')}
    except OSError: pass
    if len([q for q in queue if q['commons'] not in done]) < PER_MONTH:   # queue running out: trusted photographers' places
        for p, quality in candidates():
            c = suitable(p, skip)
            t = p['title'][5:]
            if c and c['author'] in TRUSTED and PLACES.search(t) and t not in done and all(q['commons'] != t for q in queue):
                queue.append({'commons': t})
    for q in queue:
        if len(picks) == PER_MONTH: break
        if q['commons'] in done: continue
        c = suitable(info(q['commons']), set())
        if not c: print('no longer suitable:', q['commons']); continue
        jpg = to_uhd(fetch(c['thumb']))
        if not jpg: continue
        name = 'kw_%s_%d.webp' % (month.replace('-', ''), len(picks) + 1)
        open(os.path.join(out_dir, name), 'wb').write(jpg)
        picks.append({'file': name, 'sha256': hashlib.sha256(jpg).hexdigest(), 'month': month, 'commons': q['commons'],
                      'title': q.get('title_ar') or title_ar(c['title']), 'author': c['author'], 'license': c['license'], 'source': c['source'],
                      'url': 'https://github.com/ALjasme/system.q8tv-updates/releases/download/photos-%s/%s' % (month, name)})
        time.sleep(1)
    if not picks: print('QUEUE EMPTY: add reviewed photos to photos/queue.json')
    listing['photos'].extend(picks)
    json.dump(listing, open(listing_path, 'w'), ensure_ascii=False, indent=1)
    for p in picks: print(p['file'], '|', p['title'], '|', p['author'], '|', p['license'])
    return picks

if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
