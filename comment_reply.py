"""FB + Insta कांदा Auto Reply — Green Source (पूर्वी n8n मध्ये होते).

दर 15 मिनिटांनी GitHub Actions हा script चालवतो:
FB posts + FB reels + Insta media मधल्या नवीन कमेंट्स पाहतो, शब्द/राज्य ओळखतो आणि योग्य पोस्टकडे पाठवणारा रिप्लाय देतो.
कोणत्या कमेंटला रिप्लाय गेला ती यादी state/replied.json मध्ये राहते (n8n च्या static data ऐवजी).

लक्षात ठेवा: repo public आहे, म्हणून logs मध्ये कमेंट करणाऱ्याचं नाव किंवा कमेंट छापत नाही.
"""
import json
import random
import re
import time
import unicodedata
from datetime import datetime, timedelta, timezone
from pathlib import Path

import requests

from fb_token import page_token, DRY_RUN

# ================= इथे बदल करू शकता =================

# गट १: मराठी शब्द → MSMB चा मराठी रेट + मराठी मेसेज
MR_WORDS = ['कांदा', 'कांदे', 'महाराष्ट्र', 'महाराष्ट्रा']

# गट २: हिंदी शब्द → AG Market महाराष्ट्र रेट + हिंदी मेसेज
HI_WORDS = ['प्याज', 'pyaz', 'pyaj', 'pyaaz', 'pyaaj']

# गट ३: इंग्रजी / हिंग्लिश शब्द → AG Market महाराष्ट्र रेट + मराठी मेसेज
EN_WORDS = ['onion', 'kanda', 'kande', 'kaanda', 'knda']

# इंग्रजीत "Maharashtra" लिहिलं तर AG Market महाराष्ट्र रेटसोबत मेसेजची भाषा: 'mr' / 'hi' / 'en'
MH_LANG = 'mr'

# या राज्यांना इंग्रजीत मेसेज जाईल. महाराष्ट्राला MH_LANG नुसार. बाकी सर्व राज्यांना हिंदीत.
SOUTH_STATES = ['Karnataka', 'Andhra Pradesh', 'Telangana', 'Tamil Nadu', 'Kerala', 'Puducherry', 'Goa']

# [पोस्टमधलं इंग्रजी नाव(नावे)], [कमेंटमधले शब्द], 'हिंदी/मराठी मेसेजमधलं नाव'
STATE_WORDS = [
    [['Maharashtra'], ['maharashtra'], 'महाराष्ट्र'],
    [['Madhya Pradesh'], ['madhya pradesh', 'मध्य प्रदेश', 'मध्यप्रदेश', 'एमपी'], 'मध्य प्रदेश'],
    [['Rajasthan'], ['rajasthan', 'राजस्थान'], 'राजस्थान'],
    [['Uttar Pradesh'], ['uttar pradesh', 'उत्तर प्रदेश', 'उत्तरप्रदेश', 'यूपी'], 'उत्तर प्रदेश'],
    [['Bihar'], ['bihar', 'बिहार'], 'बिहार'],
    [['Gujarat'], ['gujarat', 'गुजरात', 'ગુજરાત'], 'गुजरात'],
    [['Karnataka'], ['karnataka', 'कर्नाटक', 'ಕರ್ನಾಟಕ'], 'कर्नाटक'],
    [['Andhra Pradesh'], ['andhra', 'आंध्र', 'ఆంధ్ర'], 'आंध्र प्रदेश'],
    [['Telangana'], ['telangana', 'तेलंगाना', 'तेलंगणा', 'తెలంగాణ'], 'तेलंगाना'],
    [['Tamil Nadu'], ['tamil nadu', 'tamilnadu', 'तमिलनाडु', 'तमिळनाडू', 'தமிழ்நாடு', 'தமிழ்'], 'तमिलनाडु'],
    [['Kerala', 'Keralam'], ['kerala', 'keralam', 'केरल', 'केरळ', 'കേരളം', 'കേരള'], 'केरल'],
    [['West Bengal'], ['west bengal', 'bengal', 'बंगाल', 'পশ্চিমবঙ্গ', 'বাংলা'], 'पश्चिम बंगाल'],
    [['Odisha', 'Orissa'], ['odisha', 'orissa', 'ओडिशा', 'ओडिसा', 'ଓଡ଼ିଶା'], 'ओडिशा'],
    [['Punjab'], ['punjab', 'पंजाब', 'ਪੰਜਾਬ'], 'पंजाब'],
    [['Haryana'], ['haryana', 'हरियाणा', 'हरयाणा'], 'हरियाणा'],
    [['Himachal Pradesh'], ['himachal', 'हिमाचल'], 'हिमाचल प्रदेश'],
    [['Uttarakhand'], ['uttarakhand', 'उत्तराखंड', 'उत्तराखण्ड'], 'उत्तराखंड'],
    [['Jammu and Kashmir', 'Jammu & Kashmir'], ['jammu', 'kashmir', 'जम्मू', 'कश्मीर', 'काश्मीर'], 'जम्मू-कश्मीर'],
    [['Chhattisgarh'], ['chhattisgarh', 'chattisgarh', 'छत्तीसगढ़', 'छत्तीसगड'], 'छत्तीसगढ़'],
    [['Jharkhand'], ['jharkhand', 'झारखंड', 'झारखण्ड'], 'झारखंड'],
    [['Assam'], ['assam', 'असम', 'आसाम', 'অসম'], 'असम'],
    [['Goa'], ['goa', 'गोवा', 'गोंय'], 'गोवा'],
    [['Delhi', 'NCT of Delhi'], ['delhi', 'दिल्ली'], 'दिल्ली'],
    [['Tripura'], ['tripura', 'त्रिपुरा', 'ত্রিপুরা'], 'त्रिपुरा'],
    [['Meghalaya'], ['meghalaya', 'मेघालय'], 'मेघालय'],
    [['Manipur'], ['manipur', 'मणिपुर'], 'मणिपुर'],
    [['Nagaland'], ['nagaland', 'नागालैंड'], 'नागालैंड'],
    [['Mizoram'], ['mizoram', 'मिजोरम'], 'मिजोरम'],
    [['Sikkim'], ['sikkim', 'सिक्किम'], 'सिक्किम'],
    [['Arunachal Pradesh'], ['arunachal', 'अरुणाचल'], 'अरुणाचल प्रदेश'],
    [['Chandigarh'], ['chandigarh', 'चंडीगढ़'], 'चंडीगढ़'],
    [['Puducherry', 'Pondicherry'], ['puducherry', 'pondicherry', 'पुडुचेरी', 'புதுச்சேரி'], 'पुडुचेरी'],
]

# राज्य पोस्टचे रिप्लाय. {date} = पोस्टची तारीख, {state} = राज्य
STATE_TPL = {
    'facebook': {
        'hi': [
            'नमस्कार 🙏 दिनांक {date} के {state} प्याज मंडी भाव साथ में हैं। पूरी लिस्ट के लिए Green Source पेज पर {date} की {state} पोस्ट देखें। सभी राज्यों के प्याज भाव हमारे पेज पर उपलब्ध हैं।',
            'धन्यवाद 🙏 {state} के दिनांक {date} के प्याज भाव साथ में हैं। {state} की सभी मंडियों के भाव Green Source पेज की {date} की पोस्ट में हैं। सभी राज्यों के भाव भी हमारे पेज पर उपलब्ध हैं।',
        ],
        'en': [
            'Namaste 🙏 {state} onion mandi rates for {date} are attached. For the full list, see the {date} {state} post on the Green Source page. Onion rates of all states are available on our page.',
            'Thank you 🙏 Here are the {state} onion rates for {date}. All mandi rates are in the {date} {state} post on the Green Source page. Rates for every state are also available on our page.',
        ],
        'mr': [
            'नमस्कार 🙏 दिनांक {date} चे {state} कांदा बाजारभाव सोबत दिले आहेत. सर्व बाजार समित्यांचे भाव Green Source पेजवरील {date} तारखेच्या {state} पोस्टमध्ये आहेत. सर्व राज्यांचे कांदा भाव आमच्या पेजवर उपलब्ध आहेत.',
            'धन्यवाद 🙏 हे दिनांक {date} चे {state} कांदा भाव आहेत. पूर्ण यादीसाठी Green Source पेजवरील {date} तारखेची {state} पोस्ट पहा. सर्व राज्यांचे भावही आमच्या पेजवर मिळतील.',
        ],
    },
    'instagram': {
        'hi': [
            'नमस्कार 🙏 दिनांक {date} के {state} प्याज मंडी भाव @greensourceonion प्रोफाइल पर {date} की {state} पोस्ट में देखें। सभी राज्यों के भाव हमारे प्रोफाइल पर उपलब्ध हैं।',
            'धन्यवाद 🙏 {state} के प्याज भाव (दिनांक {date}) @greensourceonion प्रोफाइल की {date} की पोस्ट में हैं। सभी राज्यों के भाव भी वहीं उपलब्ध हैं।',
        ],
        'en': [
            'Namaste 🙏 {state} onion mandi rates for {date} are in the {date} {state} post on @greensourceonion. Onion rates of all states are available on our profile.',
            'Thank you 🙏 See the {date} {state} post on @greensourceonion for all mandi rates. Rates for every state are also on our profile.',
        ],
        'mr': [
            'नमस्कार 🙏 दिनांक {date} चे {state} कांदा बाजारभाव @greensourceonion प्रोफाइलवरील {date} तारखेच्या {state} पोस्टमध्ये पहा. सर्व राज्यांचे भाव आमच्या प्रोफाइलवर उपलब्ध आहेत.',
            'धन्यवाद 🙏 {state} चे दिनांक {date} चे कांदा भाव @greensourceonion प्रोफाइलवरील पोस्टमध्ये आहेत. सर्व राज्यांचे भावही तिथे मिळतील.',
        ],
    },
}

# MSMB (मराठी) पोस्टचे रिप्लाय
MSMB_TPL = {
    'facebook': [
        'नमस्कार 🙏 दिनांक {date} चे कांदा बाजारभाव. पूर्ण यादीसाठी वरील Green Source नावावर क्लिक करून पेजवरील {date} तारखेची पोस्ट पहा. सर्व राज्यांचे कांदा भाव आमच्या पेजवर उपलब्ध आहेत.',
        'धन्यवाद 🙏 हे दिनांक {date} चे कांदा बाजारभाव आहेत. सर्व बाजार समित्यांचे भाव पाहण्यासाठी वरील Green Source नावावर क्लिक करा आणि {date} तारखेची पोस्ट पहा. सर्व राज्यांचे भावही आमच्या पेजवर मिळतील.',
        'राम राम 🙏 दिनांक {date} चे कांदा भाव सोबत दिले आहेत. पूर्ण यादी Green Source पेजवरील {date} तारखेच्या पोस्टमध्ये आहे. सर्व राज्यांचे कांदा भाव आमच्या पेजवर उपलब्ध आहेत.',
    ],
    'instagram': [
        'नमस्कार 🙏 दिनांक {date} चे संपूर्ण कांदा बाजारभाव @greensourceonion प्रोफाइलवरील {date} तारखेची पोस्ट पहा. सर्व राज्यांचे भाव आमच्या प्रोफाइलवर उपलब्ध आहेत.',
        'धन्यवाद 🙏 दिनांक {date} चे सर्व बाजार समित्यांचे कांदा भाव @greensourceonion प्रोफाइलवरील {date} तारखेच्या पोस्टमध्ये पहा. सर्व राज्यांचे भावही तिथे मिळतील.',
        'राम राम 🙏 कांदा बाजारभावासाठी @greensourceonion प्रोफाइलवरील दिनांक {date} ची पोस्ट पहा. सर्व राज्यांचे कांदा भाव आमच्या प्रोफाइलवर उपलब्ध आहेत.',
    ],
}

# प्रत्येक प्लॅटफॉर्मसाठी एका वेळी जास्तीत जास्त किती रिप्लाय
MAX_PER_RUN = 10

# किती तासांपेक्षा जुन्या कमेंटला रिप्लाय नको
MAX_AGE_HOURS = 24

# MSMB रेट पोस्टच्या टायटलमधले ठरलेले शब्द
TITLE_WORDS = ['कांदा बाजारभाव']

# ================= याखाली बदल करू नका =================

PAGE_ID = '609269705592123'
IG_USER_ID = '17841412056274162'
IG_USERNAME = 'greensourceonion'
MARKER = '#GreenSourceMandiBhav'
GRAPH = 'https://graph.facebook.com'
STATE_FILE = Path(__file__).resolve().parent / 'state' / 'replied.json'
IST = timezone(timedelta(hours=5, minutes=30))

TOKEN = ''


def graph(method, path, params=None, data=None):
    """Token URL मध्ये नाही, header मध्ये जातो — त्यामुळे कुठल्याही error मध्ये token छापला जात नाही."""
    try:
        r = requests.request(method, f'{GRAPH}/{path}', params=params, data=data,
                             headers={'Authorization': f'Bearer {TOKEN}'}, timeout=60)
        j = r.json()
    except Exception as e:
        print(f'⚠️ {path.split("/")[-1]}: {type(e).__name__}')
        return {}
    if isinstance(j, dict) and 'error' in j:
        print(f'⚠️ {path.split("/")[-1]}: {j["error"].get("message", "")}')
        return {}
    return j


def norm(t):
    return unicodedata.normalize('NFC', str(t or '')).lower()


def has_any(words, t):
    return any(norm(k) in t for k in words)


def pick(lst, n):
    return lst[n % len(lst)]


def ckey(cid):
    # एकच कमेंट feed आणि reels मध्ये वेगळ्या ID ने येऊ शकते: '123_456' आणि '789_456'
    return str(cid or '').split('_')[-1]


def to_ist(s):
    s = str(s or '')
    try:
        d = datetime.strptime(s, '%Y-%m-%dT%H:%M:%S%z')
    except ValueError:
        d = datetime.fromisoformat(s.replace('Z', '+00:00'))
    return d.astimezone(IST)


def age_hours(s, now):
    try:
        return (now - to_ist(s)).total_seconds() / 3600
    except Exception:
        return 1e9


def ddmmyyyy(s):
    return to_ist(s).strftime('%d-%m-%Y')


def _letters_only(t):
    return ''.join(ch if unicodedata.category(ch)[0] in 'LMN' else ' ' for ch in norm(t))


def state_of(t):
    x = ' ' + re.sub(r' +', ' ', _letters_only(t)) + ' '
    for entry in STATE_WORDS:
        for k in entry[1]:
            kk = norm(k)
            if (re.fullmatch(r'[a-z ]+', kk) and f' {kk} ' in x) or (not re.fullmatch(r'[a-z ]+', kk) and kk in x):
                return entry
    return None


MH_ENTRY = next(e for e in STATE_WORDS if e[0][0] == 'Maharashtra')


def lang_for(key):
    return MH_LANG if key == 'Maharashtra' else ('en' if key in SOUTH_STATES else 'hi')


def is_rate_title(t):
    s = unicodedata.normalize('NFC', str(t or ''))
    return any(w in s for w in TITLE_WORDS) and MARKER not in s


def is_state_post(msg, names):
    m = str(msg or '')
    return (MARKER in m or re.search(r'Onion Mandi Rates|प्याज मंडी भाव|कांदा बाजार भाव', m)) and any(n in m for n in names)


def our_reply(s):
    m = str(s or '')
    return bool(re.search(r'\d{2}-\d{2}-\d{4}', m) and re.search(r'Green Source|greensourceonion', m, re.I))


def pick_target(text, find_state_post, msmb):
    t = norm(text)
    st = state_of(text)                       # १. राज्याचं नाव
    if st:
        p = find_state_post(st)
        if p:
            return {'post': p, 'entry': st, 'lang': lang_for(st[0][0])}
    if has_any(MR_WORDS, t):                  # २. मराठी शब्द → MSMB + मराठी
        return {'post': msmb, 'msmb': True, 'lang': 'mr'} if msmb else None
    lang = 'hi' if has_any(HI_WORDS, t) else ('mr' if has_any(EN_WORDS, t) else None)
    if not lang:
        return None
    mh = find_state_post(MH_ENTRY)            # ३/४. AG Market महाराष्ट्र
    if mh:
        return {'post': mh, 'entry': MH_ENTRY, 'lang': lang}
    return {'post': msmb, 'msmb': True, 'lang': lang} if msmb else None


def make_reply(platform, tgt, n):
    date = tgt['post']['date']
    if tgt.get('msmb') and tgt['lang'] == 'mr':
        return pick(MSMB_TPL[platform], n).replace('{date}', date)
    entry = tgt.get('entry') or MH_ENTRY
    name = entry[0][0] if tgt['lang'] == 'en' else entry[2]
    return pick(STATE_TPL[platform][tgt['lang']], n).replace('{date}', date).replace('{state}', name)


def first_image(p):
    a = ((p.get('attachments') or {}).get('data') or [{}])[0] or {}
    subs = (a.get('subattachments') or {}).get('data') or []
    sub = subs[0] if subs else None
    if sub and ((sub.get('media') or {}).get('image') or {}).get('src'):
        return sub['media']['image']['src']
    return ((a.get('media') or {}).get('image') or {}).get('src', '')


def fb_kind(p):
    return ','.join(str(a.get('media_type') or a.get('type') or '').lower()
                    for a in ((p.get('attachments') or {}).get('data') or []))


def fb_is_photo(p):
    k = fb_kind(p)
    return bool(p.get('permalink_url')) and bool(re.search('photo|album', k)) and 'video' not in k


def ig_is_photo(m):
    return bool(m.get('permalink')) and m.get('media_product_type') == 'FEED' and m.get('media_type') != 'VIDEO'


def load_store():
    try:
        return json.loads(STATE_FILE.read_text(encoding='utf-8'))
    except Exception:
        return {}


def save_store(store):
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(store, ensure_ascii=False, indent=1), encoding='utf-8')


def main():
    global TOKEN
    TOKEN = page_token()
    store = load_store()
    store['replied'] = store.get('replied') or []
    replied_keys = {ckey(x) for x in store['replied']}
    now = datetime.now(IST)
    start = random.randint(0, 2)
    out, seen = [], set()

    # ---------- डेटा आणणे ----------
    fb_posts = graph('GET', f'{PAGE_ID}/feed', {
        'fields': 'id,created_time,permalink_url,message,attachments{media_type,type,media{image{src}},'
                  'subattachments.limit(1){media{image{src}}}},comments.order(reverse_chronological).limit(50)'
                  '{id,message,created_time,from,comments.limit(25){id,from,message}}',
        'limit': 60}).get('data', [])
    fb_reels = graph('GET', f'{PAGE_ID}/video_reels', {
        'fields': 'id,created_time,comments.order(reverse_chronological).limit(50)'
                  '{id,message,created_time,from,comments.limit(25){id,from,message}}',
        'limit': 30}).get('data', [])

    ig_media, ig_ids, after = [], set(), ''
    for _ in range(3):
        params = {'fields': 'id,media_type,media_product_type,permalink,timestamp,caption,'
                            'comments.limit(50){id,text,timestamp,username,replies{id,username}}',
                  'limit': 100}
        if after:
            params['after'] = after
        res = graph('GET', f'{IG_USER_ID}/media', params)
        for m in res.get('data', []):
            if m['id'] not in ig_ids:
                ig_ids.add(m['id'])
                ig_media.append(m)
        after = ((res.get('paging') or {}).get('cursors') or {}).get('after', '')
        if not after or not (res.get('paging') or {}).get('next'):
            break
    print(f'FB posts: {len(fb_posts)} | FB reels: {len(fb_reels)} | IG media: {len(ig_media)}')

    # ---------- FACEBOOK ----------
    fb_rate = next((p for p in fb_posts if fb_is_photo(p) and is_rate_title(p.get('message'))), None)
    if fb_rate:
        store['fbPost'] = {'link': fb_rate['permalink_url'], 'date': ddmmyyyy(fb_rate['created_time']),
                           'image': first_image(fb_rate)}
    fb_cache = {}

    def fb_state_post(entry):
        key = entry[0][0]
        if key not in fb_cache:
            q = next((p for p in fb_posts if fb_is_photo(p) and is_state_post(p.get('message'), entry[0])), None)
            fb_cache[key] = {'link': q['permalink_url'], 'date': ddmmyyyy(q['created_time']),
                             'image': first_image(q)} if q else None
        return fb_cache[key]

    fb_sources = ([p for p in fb_posts if 'video' not in fb_kind(p)] + fb_reels) if fb_reels else fb_posts
    for p in fb_sources:
        for c in ((p.get('comments') or {}).get('data') or []):
            if len(out) >= MAX_PER_RUN:
                break
            if (c.get('from') or {}).get('id') == PAGE_ID:
                continue
            k = ckey(c.get('id'))
            if k in replied_keys or k in seen:
                continue
            if age_hours(c.get('created_time'), now) > MAX_AGE_HOURS:
                continue
            subs = (c.get('comments') or {}).get('data') or []
            if any((r.get('from') or {}).get('id') == PAGE_ID or our_reply(r.get('message')) for r in subs):
                continue
            tgt = pick_target(c.get('message'), fb_state_post, store.get('fbPost'))
            if not tgt:
                continue
            seen.add(k)
            text = make_reply('facebook', tgt, start + len(out))
            image = tgt['post'].get('image') or (store.get('fbPost') or {}).get('image') or ''
            body = {'message': text}
            if image:
                body['attachment_url'] = image
            out.append({'platform': 'facebook', 'commentId': c['id'], 'text': text, 'body': body})

    # ---------- INSTAGRAM ----------
    ig_rate = next((m for m in ig_media if ig_is_photo(m) and is_rate_title(m.get('caption'))), None)
    if ig_rate:
        store['igPost'] = {'link': ig_rate['permalink'], 'date': ddmmyyyy(ig_rate['timestamp'])}
    ig_cache = {}

    def ig_state_post(entry):
        key = entry[0][0]
        if key not in ig_cache:
            q = next((m for m in ig_media if ig_is_photo(m) and is_state_post(m.get('caption'), entry[0])), None)
            ig_cache[key] = {'link': q['permalink'], 'date': ddmmyyyy(q['timestamp'])} if q else None
        return ig_cache[key]

    fb_count = len(out)
    for m in ig_media:
        for c in ((m.get('comments') or {}).get('data') or []):
            if len(out) - fb_count >= MAX_PER_RUN:
                break
            if c.get('username') == IG_USERNAME:
                continue
            k = ckey(c.get('id'))
            if k in replied_keys or k in seen:
                continue
            if age_hours(c.get('timestamp'), now) > MAX_AGE_HOURS:
                continue
            if any(r.get('username') == IG_USERNAME for r in ((c.get('replies') or {}).get('data') or [])):
                continue
            tgt = pick_target(c.get('text'), ig_state_post, store.get('igPost'))
            if not tgt:
                continue
            seen.add(k)
            text = make_reply('instagram', tgt, start + len(out))
            out.append({'platform': 'instagram', 'commentId': c['id'], 'text': text, 'body': {'message': text}})

    print(f'रिप्लाय द्यायच्या कमेंट्स: FB {fb_count} | Insta {len(out) - fb_count}')

    # ---------- रिप्लाय पाठवणे ----------
    sent = 0
    for i, item in enumerate(out):
        if DRY_RUN:
            print(f'[TEST] {item["platform"]}: {item["text"][:90]}…')
            continue
        if i:
            time.sleep(3)
        edge = 'comments' if item['platform'] == 'facebook' else 'replies'
        res = graph('POST', f'{item["commentId"]}/{edge}', data=item['body'])
        if res.get('id'):
            sent += 1
            if item['commentId'] not in store['replied']:
                store['replied'].append(item['commentId'])
    store['replied'] = store['replied'][-3000:]

    if DRY_RUN:
        print('✅ TEST MODE: कोणालाही रिप्लाय पाठवला नाही.')
    else:
        save_store(store)
        print(f'✅ {sent}/{len(out)} रिप्लाय पाठवले.')


if __name__ == '__main__':
    main()
