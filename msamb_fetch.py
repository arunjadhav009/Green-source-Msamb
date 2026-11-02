"""MSAMB वेबसाइटवरून कांद्याचे बाजारभाव घेणे (पूर्वी n8n चे 'MSAMB Daily Data Extract' + 'Filter & Create Chunks').

fetch_rows()   -> MSAMB मधील सर्व ओळी (Date, APMC, Variety, Unit, Quantity, Lrate, Hrate, Modal)
build_pages()  -> आजची (नसेल तर शेवटची) तारीख, आवकनुसार मोठ्याकडून लहान, 14-14 ओळींची पाने
save_csv()     -> data/msamb/YYYY-MM-DD.csv मध्ये रोजचा रेकॉर्ड
"""
import csv
import json
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import requests

MSAMB_URL = "https://www.msamb.com/ApmcDetail/DataGridBind"
COMMODITY_CODE = "08035"     # कांदा
RECORDS_PER_PAGE = 14
IST = timezone(timedelta(hours=5, minutes=30))
FIELDS = ["Date", "APMC", "Variety", "Unit", "Quantity", "Lrate", "Hrate", "Modal"]


def _clean(cell):
    return re.sub(r"<[^>]+>", "", cell).strip()


def fetch_rows():
    last_err = None
    for attempt in range(1, 4):
        try:
            r = requests.get(
                MSAMB_URL,
                params={"commodityCode": COMMODITY_CODE, "apmcCode": "null"},
                headers={
                    "X-Requested-With": "XMLHttpRequest",
                    "Referer": "https://www.msamb.com/ApmcDetail/APMCPriceInformation",
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                                  "(KHTML, like Gecko) Chrome/130.0 Safari/537.36",
                },
                timeout=60,
            )
            r.raise_for_status()
            body = r.text
            try:  # कधी कधी HTML JSON string मध्ये येतो
                parsed = json.loads(body)
                if isinstance(parsed, str):
                    body = parsed
            except ValueError:
                pass
            rows = _parse(body)
            if rows:
                print(f"MSAMB: {len(rows)} ओळी मिळाल्या")
                return rows
            last_err = "रिकामा डेटा"
        except Exception as e:
            last_err = f"{type(e).__name__}: {e}"
        print(f"⚠️ MSAMB प्रयत्न {attempt}/3 अयशस्वी: {last_err}")
    print("❌ MSAMB वेबसाइटवरून डेटा मिळाला नाही.")
    sys.exit(1)


def _parse(html):
    rows, current_date = [], ""
    for tr in re.findall(r"<tr>[\s\S]*?</tr>", html):
        cells = [_clean(c) for c in re.findall(r"<td[^>]*>([\s\S]*?)</td>", tr)]
        if len(cells) == 1:          # colspan=7 असलेली तारखेची ओळ
            current_date = cells[0]
        elif len(cells) == 7:        # APMC, Variety, Unit, Qty, Lrate, Hrate, Modal
            rows.append(dict(zip(FIELDS, [current_date] + cells)))
    return rows


def _date_num(s):
    p = re.split(r"[/\-]", s)
    try:
        return int(p[2] + p[1].zfill(2) + p[0].zfill(2))
    except (IndexError, ValueError):
        return 0


def _qty(r):
    try:
        return float(re.sub(r"[^0-9.\-]+", "", str(r.get("Quantity") or "0")) or 0)
    except ValueError:
        return 0.0


def build_pages(rows):
    today = datetime.now(IST)
    targets = {today.strftime("%d/%m/%Y"), today.strftime("%d-%m-%Y")}
    selected = [r for r in rows if r["Date"].strip() in targets]
    post_date = today.strftime("%d/%m/%Y")

    if not selected:  # आजचा डेटा नसेल तर सर्वात शेवटची तारीख
        dated = [r["Date"].strip() for r in rows if r["Date"].strip()]
        if not dated:
            print("❌ MSAMB डेटामध्ये तारीख सापडली नाही.")
            sys.exit(1)
        post_date = max(dated, key=_date_num)
        selected = [r for r in rows if r["Date"].strip() == post_date]
        print(f"⚠️ आजचा डेटा अजून नाही, शेवटची तारीख वापरत आहे: {post_date}")

    selected.sort(key=_qty, reverse=True)
    total = -(-len(selected) // RECORDS_PER_PAGE)
    pages = []
    for i in range(0, len(selected), RECORDS_PER_PAGE):
        pages.append({"json": {
            "StateName": "महाराष्ट्र",
            "PostDate": post_date,
            "CurrentPage": i // RECORDS_PER_PAGE + 1,
            "TotalPages": total,
            "TotalRecords": len(selected),
            "PageData": selected[i:i + RECORDS_PER_PAGE],
        }})
    return pages


def save_csv(rows):
    day = datetime.now(IST).strftime("%Y-%m-%d")
    out = Path(__file__).resolve().parent / "data" / "msamb" / f"{day}.csv"
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        w.writerows(rows)
    print(f"डेटा सेव्ह: data/msamb/{day}.csv")


if __name__ == "__main__":
    pages = build_pages(fetch_rows())
    print(json.dumps([p["json"] for p in pages], ensure_ascii=False, indent=1)[:3000])
