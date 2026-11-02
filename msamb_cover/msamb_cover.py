"""MSAMB महाराष्ट्र कांदा बाजारभाव — पहिली (Top 5) इमेज, नवीन डिझाइन. 1080 x 1350 PNG.

generate_msamb_cover(post_date, markets, output_path)
  post_date : '22/10/2026', '22-10-2026', '2026-10-22' ... (न जुळल्यास आजची IST तारीख)
  markets   : [{"name": "सोलापूर", "price": 7100, "variety": "लाल", "modal": 3000}, ...]   (MSAMB मध्ये जिल्हा नसतो, फक्त बाजाराचे नाव)
              कितीही नोंदी द्या; सर्वाधिक भावाच्या 5 आपोआप निवडल्या जातात.

build_cover_html(pages_data) : generate_and_post.py मधून थेट वापरण्यासाठी (MSAMB PageData: APMC, Hrate, Variety, Modal).
"""
import base64
import datetime as dt
import html
import json
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
WEEKDAYS = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
ROW_TOPS = [444, 548, 645, 743, 840]
EMOJI_RE = re.compile("[\U0001F000-\U0001FAFF☀-➿️‍]+")

CSS = """
@font-face{font-family:Noto;src:url('data:font/ttf;base64,__FONT__');font-weight:100 900;font-display:block}
*{box-sizing:border-box}html,body{margin:0;width:1080px;height:1350px;overflow:hidden;background:#2a0d24}
#poster{position:relative;width:1080px;height:1350px;font-family:Noto,sans-serif;color:#fff}
#static{position:absolute;inset:0;width:1080px;height:1350px}
.text{position:absolute;display:flex;align-items:center;line-height:1.2;font-weight:800;white-space:nowrap}
.text span{display:block;max-width:100%}.c{justify-content:center;text-align:center}.r{justify-content:flex-end;text-align:right}
.wrap{white-space:normal;text-wrap:balance}
"""

FIT = """<script>
window.__fit=async()=>{await document.fonts.ready;const problems=[];
for(const el of document.querySelectorAll('.text')){const sp=el.firstElementChild;
let s=parseFloat(getComputedStyle(el).fontSize);const min=Number(el.dataset.min||18);
const ok=()=>sp.scrollWidth<=el.clientWidth+1&&sp.getBoundingClientRect().height<=el.clientHeight+1;
while(!ok()&&s>min){s--;el.style.fontSize=s+'px'}if(!ok())problems.push(el.id)}
return {problems,fontLoaded:document.fonts.check('30px Noto')}};
</script>"""


def parse_post_date(value):
    s = str(value or "").strip()[:10]
    for fmt in ("%d/%m/%Y", "%d-%m-%Y", "%Y-%m-%d", "%d.%m.%Y", "%Y/%m/%d"):
        try:
            return dt.datetime.strptime(s, fmt).date()
        except ValueError:
            pass
    return (dt.datetime.utcnow() + dt.timedelta(hours=5, minutes=30)).date()


def pick_cta(date):
    c = json.loads((HERE / "content.json").read_text(encoding="utf-8"))
    extra = c.get("rotating_cta") or []
    o = date.toordinal()
    if c.get("rotation_enabled") and extra and o % 2 == 1:
        q = extra[(o // 2) % len(extra)]
    else:
        q = c["primary_cta"][WEEKDAYS[date.weekday()]]
    return EMOJI_RE.sub("", q).strip()


def _num(v):
    try:
        return float(str(v).replace(",", "").replace("₹", "").strip())
    except (TypeError, ValueError):
        return 0.0


def _price(v):
    return "₹" + format(int(round(_num(v))), ",")


def _name(v):
    # MSAMB नावातले "नामपूर- करंजाड" / "पुणे -पिंपरी" असे डॅश व्यवस्थित करणे
    return re.sub(r"\s*-\s*", " - ", str(v or "").strip())


def _sub(r):
    # दुसरी ओळ: जात · सरासरी भाव (जुन्या इमेजसारखी)
    v = str(r.get("variety") or "").strip()
    v = "" if v.strip("- ") == "" else v
    m = _num(r.get("modal"))
    parts = [v] + (["सरासरी " + _price(m)] if m > 0 else [])
    return " · ".join(x for x in parts if x)


def _t(id_, box, text, size, cls="", minsize=18, style=""):
    x, y, w, h = box
    return (f'<div id="{id_}" class="text {cls}" data-min="{minsize}" '
            f'style="left:{x}px;top:{y}px;width:{w}px;height:{h}px;font-size:{size}px;{style}">'
            f'<span>{html.escape(str(text))}</span></div>')


def build_html(post_date, markets):
    date = parse_post_date(post_date)
    top = sorted(markets, key=lambda r: _num(r.get("price")), reverse=True)[:5]
    L = [_t("date", [139, 119, 285, 54], date.strftime("%d-%m-%Y"), 46, "c", 34,
            "color:#090900;transform:rotate(-2deg)")]
    if top:
        b = top[0]
        L += [
            _t("hp", [549, 225, 312, 98], _price(b.get("price")), 92, "c", 52, "color:#fffdeb;font-weight:900"),
            _t("hm", [557, 330, 292, 72], _name(b.get("name")), 32, "c wrap", 18, "color:#151402;line-height:1.1"),
        ]
    for i, r in enumerate(top):
        y = ROW_TOPS[i]
        col = "#151100" if i == 0 else "#ffffff"
        L += [
            _t(f"m{i}", [235, y + 5, 450, 45], _name(r.get("name")), 36, "", 21, f"color:{col}"),
            _t(f"s{i}", [236, y + 50, 448, 33], _sub(r), 25, "", 16, f"color:{col};font-weight:500"),
            _t(f"p{i}", [707, y + 1, 265, 56], _price(r.get("price")), 49, "r", 32,
               "color:" + ("#280517" if i == 0 else "#ffeb32") + ";font-weight:900"),
            _t(f"u{i}", [781, y + 57, 190, 28], "प्रति क्विंटल", 22, "r", 17, f"color:{col};font-weight:600"),
        ]
    cta = pick_cta(date)
    L.append(_t("cta", [401, 1040, 468, 96], cta, 39, "c wrap", 24, "color:#640c2c;font-weight:900;line-height:1.22"))
    css = CSS.replace("__FONT__", base64.b64encode((HERE / "fonts/NotoSansDevanagari.ttf").read_bytes()).decode())
    bg = base64.b64encode((HERE / "static_background.png").read_bytes()).decode()
    page = (f'<!doctype html><html lang="mr"><meta charset="utf-8"><style>{css}</style><div id="poster">'
            f'<img id="static" src="data:image/png;base64,{bg}">' + "\n".join(L) + "</div>" + FIT + "</html>")
    return page, {"date": str(date), "cta": cta, "rows": len(top)}


def generate_msamb_cover(post_date, markets, output_path, browser=None):
    page_html, info = build_html(post_date, markets)

    def shoot(b):
        pg = b.new_page(viewport={"width": 1080, "height": 1350}, device_scale_factor=1)
        pg.set_content(page_html, wait_until="load")
        rep = pg.evaluate("window.__fit()")
        pg.screenshot(path=str(output_path), full_page=False)
        pg.close()
        return rep

    if browser is not None:
        rep = shoot(browser)
    else:
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            b = p.chromium.launch()
            try:
                rep = shoot(b)
            finally:
                b.close()
    if rep.get("problems"):
        print("⚠️ MSAMB कव्हर: काही मजकूर जागेत पूर्ण बसला नाही:", rep["problems"])
    print(f"✅ MSAMB नवीन कव्हर: {info['date']} | प्रश्न: {info['cta']}")
    return rep


def build_cover_html(pages_data):
    """generate_and_post.py साठी: MSAMB पेजेस (PageData मध्ये APMC, Hrate, Variety, Modal) वरून कव्हरचा HTML."""
    post_date, markets = "", []
    for item in pages_data:
        info = item.get("json", item)
        post_date = post_date or str(info.get("PostDate", ""))
        for r in info.get("PageData", []):
            markets.append({"name": r.get("APMC", r.get("Market", "")),
                            "price": r.get("Hrate", r.get("Max_Price", 0)),
                            "variety": r.get("Variety", ""),
                            "modal": r.get("Modal", r.get("Modal_Price", ""))})
    page, info = build_html(post_date, markets)
    print(f"✅ MSAMB नवीन कव्हर: {info['date']} | प्रश्न: {info['cta']}")
    return page


if __name__ == "__main__":
    import sys
    data = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8-sig"))
    generate_msamb_cover(data["date"], data["markets"], sys.argv[2] if len(sys.argv) > 2 else "msamb_cover.png")
