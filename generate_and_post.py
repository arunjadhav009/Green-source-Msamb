import os
import sys
import time
import json
import html
import requests
from playwright.sync_api import sync_playwright

# नवीन पहिले (टॉप 5) कव्हर — msamb_cover फोल्डरमधून. सर्व इमेजेस 1080 x 1350 (4:5).
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "msamb_cover"))

PAGE_ID = "609269705592123"
IG_USER_ID = "17841412056274162"

from fb_token import page_token, DRY_RUN

# token कधीही code मध्ये लिहायचा नाही — तो GitHub Secrets मधून (FB_TOKEN) येतो
FB_TOKEN = "" if DRY_RUN else page_token()

POST_CAPTION = (
    "महाराष्ट्र राज्य कांदा बाजारभाव\n\n"
    "दररोजच्या ताज्या बाजारभावासाठी पेजला नक्की फॉलो करा!\n"
    "#कांदा #बाजारभाव #महाराष्ट्र #OnionRates #Maharashtra #greensourceonion"
)

def generate_html_page(data):
    rows = data.get("PageData", [])
    post_date = data.get("PostDate", "आजचे भाव")
    state_name = data.get("StateName", "महाराष्ट्र")
    current_page = data.get("CurrentPage", 1)
    total_pages = data.get("TotalPages", 1)

    table_rows = ""
    for idx, r in enumerate(rows):
        is_even = (idx % 2 == 1)
        bg = "#f8fafc" if is_even else "#ffffff"
        apmc = r.get("APMC", r.get("Market", "-"))
        variety = r.get("Variety", "-")
        qty = r.get("Quantity", "0")
        lrate = r.get("Lrate", r.get("Min_Price", "0"))
        hrate = r.get("Hrate", r.get("Max_Price", "0"))
        modal = r.get("Modal", r.get("Modal_Price", "0"))

        table_rows += f"""
        <tr style="background: {bg}; border-bottom: 1.5px solid #e2e8f0; height: 72px;">
          <td style="text-align: left; padding: 0 14px; font-weight: 700; font-size: 21px; color: #0f172a; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">{apmc}</td>
          <td style="text-align: center; padding: 0 8px; font-size: 19px; color: #475569; font-weight: 600;">{variety}</td>
          <td style="text-align: center; padding: 0 8px; font-size: 20px; font-weight: 700; color: #0f172a;">{qty}</td>
          <td style="text-align: center; padding: 0 8px; font-size: 20px; font-weight: 700; color: #dc2626;">₹{lrate}</td>
          <td style="text-align: center; padding: 0 8px; font-size: 20px; font-weight: 700; color: #16a34a;">₹{hrate}</td>
          <td style="text-align: center; padding: 0 8px; font-size: 22px; font-weight: 800; color: #881337; background: rgba(225, 29, 72, 0.08);">₹{modal}</td>
        </tr>
        """

    html = f"""<!DOCTYPE html>
<html lang="mr">
<head>
<meta charset="UTF-8">
<style>
  * {{
    box-sizing: border-box;
    margin: 0;
    padding: 0;
    -webkit-font-smoothing: antialiased;
    -moz-osx-font-smoothing: grayscale;
  }}
  body {{
    width: 1080px;
    height: 1350px;
    background: #f1f5f9;
    font-family: 'Noto Sans Devanagari', 'Lohit Devanagari', sans-serif;
    padding: 18px 20px;
    display: flex;
    flex-direction: column;
    justify-content: space-between;
    overflow: hidden;
  }}
  .header-card {{
    background: linear-gradient(135deg, #881337 0%, #be123c 60%, #e11d48 100%);
    border-radius: 16px;
    padding: 14px 22px;
    color: #ffffff;
    box-shadow: 0 6px 18px rgba(136, 19, 55, 0.28);
    border: 1px solid rgba(255, 255, 255, 0.15);
  }}
  .header-card h1 {{
    font-size: 32px;
    font-weight: 800;
    text-align: center;
    letter-spacing: 0.5px;
    margin-bottom: 8px;
  }}
  .meta-chips {{
    display: flex;
    justify-content: space-between;
    align-items: center;
  }}
  .chip {{
    background: rgba(255, 255, 255, 0.22);
    padding: 4px 16px;
    border-radius: 20px;
    font-size: 18px;
    font-weight: 700;
  }}
  .table-wrapper {{
    background: #ffffff;
    border-radius: 16px;
    overflow: hidden;
    box-shadow: 0 4px 16px rgba(0, 0, 0, 0.06);
    border: 1px solid #cbd5e1;
    margin: 8px 0;
    flex-grow: 1;
    display: flex;
    flex-direction: column;
    justify-content: flex-start;
  }}
  table {{
    width: 100%;
    border-collapse: collapse;
    table-layout: fixed;
  }}
  thead th {{
    background: #1e293b;
    color: #ffffff;
    font-size: 20px;
    font-weight: 700;
    padding: 12px 8px;
    text-align: center;
    border-bottom: 2px solid #0f172a;
    height: 52px;
  }}
  tbody tr {{
    vertical-align: middle;
  }}
  .footer-bar {{
    background: #0f172a;
    color: #f8fafc;
    border-radius: 12px;
    padding: 12px 22px;
    display: flex;
    justify-content: space-between;
    align-items: center;
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
  }}
  .footer-bar .left {{
    font-size: 19px;
    font-weight: 700;
    color: #fbbf24;
  }}
  .footer-bar .right {{
    font-size: 18px;
    font-weight: 600;
    color: #cbd5e1;
  }}
</style>
</head>
<body>
  <div class="header-card">
    <h1>🧅 महाराष्ट्र राज्य - आजचे कांदा बाजार भाव 🧅</h1>
    <div class="meta-chips">
      <div class="chip">तारीख: {post_date}</div>
      <div class="chip">राज्य: {state_name}</div>
      <div class="chip">पेज: {current_page} / {total_pages}</div>
    </div>
  </div>

  <div class="table-wrapper">
    <table>
      <thead>
        <tr>
          <th style="text-align: left; padding-left: 14px; width: 27%;">बाजार समिती</th>
          <th style="width: 15%;">जात/प्रकार</th>
          <th style="width: 14%;">आवक (क्विं.)</th>
          <th style="width: 14%;">कमी भाव</th>
          <th style="width: 14%;">जास्त भाव</th>
          <th style="width: 16%;">सरासरी भाव</th>
        </tr>
      </thead>
      <tbody>
        {table_rows}
      </tbody>
    </table>
  </div>

  <div class="footer-bar">
    <div class="left">⚖️ दर प्रति क्विंटल (₹)</div>
    <div class="right">दररोजच्या ताज्या बाजारभावासाठी फॉलो करा</div>
  </div>
</body>
</html>"""
    return html

def generate_cover_html(pages_data):
    """MSMB पोस्टसाठी पहिलं (फ्रंट) पान: आजचे सर्वाधिक 5 भाव, पूर्ण मराठीत"""
    records = []
    post_date = ""
    for item in pages_data:
        info = item.get("json", item)
        post_date = post_date or str(info.get("PostDate", ""))
        records.extend(info.get("PageData", []))

    def high(r):
        try:
            return float(str(r.get("Hrate", r.get("Max_Price", 0)) or 0).replace(",", ""))
        except ValueError:
            return 0.0

    top5 = sorted(records, key=high, reverse=True)[:5]
    date_text = html.escape(post_date.replace("/", "-"))

    rows = ""
    for i, r in enumerate(top5):
        apmc = html.escape(str(r.get("APMC", r.get("Market", "-"))))
        variety = html.escape(str(r.get("Variety", "") or ""))
        variety = "" if variety.strip("- ") == "" else variety
        modal = r.get("Modal", r.get("Modal_Price", ""))
        sub = " · ".join(x for x in [variety, f"सरासरी ₹{int(float(str(modal).replace(',', ''))):,}" if str(modal).replace(",", "").replace(".", "").isdigit() else ""] if x)
        cls = "row best" if i == 0 else "row"
        rows += f"""
        <div class="{cls}">
          <div class="num">{i + 1}</div>
          <div class="mid"><div class="apmc">{apmc}</div><div class="sub">{sub}</div></div>
          <div class="rate"><span>कमाल</span>₹{int(high(r)):,}</div>
        </div>"""

    return f"""<!DOCTYPE html>
<html lang="mr"><head><meta charset="UTF-8"><style>
* {{ margin: 0; padding: 0; box-sizing: border-box; }}
body {{ width: 1080px; height: 1350px; background: #fbf5e9; font-family: 'Noto Sans Devanagari', 'Lohit Devanagari', sans-serif;
  color: #1f2a1f; display: flex; flex-direction: column; overflow: hidden; }}
.band {{ background: #14532d; color: #fff; padding: 26px 60px 30px; position: relative; }}
.band .top {{ display: flex; justify-content: space-between; align-items: center; font-size: 26px; font-weight: 700; }}
.band .brand {{ letter-spacing: 1px; color: #bbf7d0; }}
.band .date {{ background: #fde68a; color: #14532d; padding: 6px 22px; border-radius: 30px; font-size: 28px; font-weight: 800; }}
.band h1 {{ margin-top: 14px; font-size: 76px; font-weight: 800; line-height: 1.15; }}
.band .lead {{ font-size: 30px; font-weight: 600; color: #dcfce7; margin-top: 4px; }}
.list {{ padding: 26px 60px 0; display: flex; flex-direction: column; gap: 12px; }}
.row {{ display: flex; align-items: center; gap: 22px; background: #fff; border: 2px solid #ecdcc0;
  border-radius: 18px; height: 98px; padding: 0 26px; }}
.row.best {{ background: #b91c1c; border-color: #b91c1c; color: #fff; }}
.num {{ width: 58px; height: 58px; border-radius: 50%; background: #14532d; color: #fff; font-size: 32px; font-weight: 800;
  display: flex; align-items: center; justify-content: center; flex-shrink: 0; }}
.row.best .num {{ background: #fff; color: #b91c1c; }}
.mid {{ flex: 1; min-width: 0; }}
.apmc {{ font-size: 36px; font-weight: 800; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; line-height: 1.2; }}
.sub {{ font-size: 22px; font-weight: 600; opacity: .75; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }}
.rate {{ font-size: 50px; font-weight: 800; color: #b91c1c; white-space: nowrap; text-align: right; line-height: 1; }}
.rate span {{ display: block; font-size: 20px; font-weight: 700; color: #6b7a6b; margin-bottom: 4px; }}
.row.best .rate, .row.best .rate span {{ color: #fff; }}
.ask {{ margin: 18px 60px 0; border: 3px dashed #14532d; border-radius: 18px; padding: 12px 20px; text-align: center; }}
.ask b {{ display: block; font-size: 30px; color: #14532d; }}
.ask i {{ font-style: normal; font-size: 22px; font-weight: 600; color: #4b5b4b; }}
.foot {{ margin-top: auto; background: #14532d; color: #fff; display: flex; justify-content: space-between; align-items: center;
  padding: 16px 60px; font-size: 24px; font-weight: 700; }}
.foot .next {{ color: #fde68a; }}
</style></head><body>
  <div class="band">
    <div class="top"><div class="brand">GREEN SOURCE · ग्रीन सोर्स</div><div class="date">{date_text}</div></div>
    <h1>महाराष्ट्र कांदा बाजारभाव</h1>
    <div class="lead">आजचे सर्वाधिक 5 भाव (₹ प्रति क्विंटल)</div>
  </div>
  <div class="list">{rows}
  </div>
  <div class="ask"><b>तुमच्या बाजार समितीचं नाव आणि आजचा भाव कमेंट करा</b>
    <i>रोज संध्याकाळी ताजे कांदा भाव इथे मिळतील · पेज फॉलो करा</i></div>
  <div class="foot"><div>सर्व बाजार समित्यांचे भाव</div><div class="next">पुढील फोटोमध्ये ➜</div></div>
</body></html>"""


def main():
    # डेटा थेट MSAMB वेबसाइटवरून (Google Sheet / n8n ची गरज नाही)
    # आजचा डेटा आला तरच पोस्ट: नसेल तर 5-5 मिनिटांनी 45 मिनिटांपर्यंत वाट पाहणे
    from msamb_fetch import fetch_rows, fetch_today_rows, build_pages, save_csv
    if DRY_RUN:
        rows = fetch_rows()
    else:
        rows = fetch_today_rows(wait_minutes=45, every_minutes=5)
        if rows is None:
            print("❌ 45 मिनिटं थांबूनही MSAMB वर आजचा डेटा आला नाही. जुना डेटा पोस्ट करणार नाही — आज पोस्ट नाही.")
            sys.exit(1)
    pages_data = build_pages(rows, allow_old=DRY_RUN)
    if not DRY_RUN:
        save_csv(rows)
    print(f"Total pages: {len(pages_data)} | Date: {pages_data[0]['json']['PostDate']}"
          + ("  [TEST MODE — पोस्ट होणार नाही]" if DRY_RUN else ""))

    fb_photo_ids = []
    ig_image_urls = []

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=[
                "--no-sandbox",
                "--disable-setuid-sandbox",
                "--font-render-hinting=none"
            ]
        )
        context = browser.new_context(
            viewport={"width": 1080, "height": 1350},
            device_scale_factor=2
        )
        page = context.new_page()

        # पहिलं फ्रंट पान (टॉप 5), नंतर सर्व भावांची पानं
        try:
            from msamb_cover import build_cover_html
            cover_html = build_cover_html(pages_data)
        except Exception as e:
            print(f"⚠️ नवीन कव्हर तयार झाले नाही, जुने कव्हर वापरत आहे: {e}")
            cover_html = generate_cover_html(pages_data)
        slides = [cover_html] + [generate_html_page(item.get("json", item)) for item in pages_data]
        for index, html_content in enumerate(slides):
            image_name = f"mandi_page_{index + 1}.png"

            print(f"Generating Ultra-HD Image {index + 1}/{len(slides)}: {image_name}...")
            page.set_content(html_content, wait_until="load")
            page.evaluate("window.__fit ? window.__fit() : null")
            page.screenshot(path=image_name, full_page=False)
            if DRY_RUN:
                continue

            # १. Facebook वर Unpublished फोटो अपलोड
            upload_url = f"https://graph.facebook.com/v19.0/{PAGE_ID}/photos"
            with open(image_name, "rb") as img_file:
                files = {"source": img_file}
                data = {"published": "false", "access_token": FB_TOKEN}
                res = requests.post(upload_url, files=files, data=data)
                result = res.json()

            if "id" in result:
                photo_id = result["id"]
                fb_photo_ids.append(photo_id)
                print(f"Page {index + 1} uploaded to FB. Photo ID: {photo_id}")

                # २. Instagram साठी Facebook कडून फोटोची Public URL मिळवणे
                pic_req = requests.get(
                    f"https://graph.facebook.com/v19.0/{photo_id}?fields=images&access_token={FB_TOKEN}"
                ).json()
                if "images" in pic_req and len(pic_req["images"]) > 0:
                    public_url = pic_req["images"][0]["source"]
                    ig_image_urls.append(public_url)
            else:
                print(f"Error uploading page {index + 1}: {result}")

        browser.close()

    if DRY_RUN:
        print(f"\n✅ TEST MODE: {len(slides)} images बनल्या. Run पानावर 'Artifacts' मध्ये डाउनलोड करून पहा. FB/Insta वर काहीही पोस्ट केले नाही.")
        return

    if not fb_photo_ids:
        print("No photos uploaded. Exiting.")
        sys.exit(1)

    # Facebook वर Multi-Photo Post करणे
    print("\n--- 1. Publishing to Facebook ---")
    feed_url = f"https://graph.facebook.com/v19.0/{PAGE_ID}/feed"
    attached_media = [{"media_fbid": pid} for pid in fb_photo_ids]
    post_payload = {
        "message": POST_CAPTION,
        "attached_media": json.dumps(attached_media),
        "access_token": FB_TOKEN
    }
    fb_resp = requests.post(feed_url, data=post_payload)
    print("Facebook Post Response:", fb_resp.text)

    # Instagram वर पोस्ट करणे (Single Image किंवा Carousel)
    if ig_image_urls:
        print(f"\n--- 2. Publishing to Instagram (@greensourceonion) --- [Total Images: {len(ig_image_urls)}]")
        
        creation_id = None

        # जर फक्त १ च इमेज असेल (Single Image Post)
        if len(ig_image_urls) == 1:
            print("Detected 1 image. Creating Single Image Container for Instagram...")
            create_url = f"https://graph.facebook.com/v19.0/{IG_USER_ID}/media"
            payload = {
                "image_url": ig_image_urls[0],
                "caption": POST_CAPTION,
                "access_token": FB_TOKEN
            }
            res = requests.post(create_url, data=payload).json()
            if "id" in res:
                creation_id = res["id"]
                print(f"Single Image Container ID: {creation_id}")
            else:
                print("Error creating Single Image container:", res)

        # जर २ किंवा जास्त इमेजेस असतील (Carousel Post)
        else:
            print(f"Detected {len(ig_image_urls)} images. Creating Carousel Container for Instagram...")
            ig_container_ids = []
            for idx, img_url in enumerate(ig_image_urls):
                create_item_url = f"https://graph.facebook.com/v19.0/{IG_USER_ID}/media"
                item_payload = {
                    "image_url": img_url,
                    "is_carousel_item": "true",
                    "access_token": FB_TOKEN
                }
                c_res = requests.post(create_item_url, data=item_payload).json()
                if "id" in c_res:
                    ig_container_ids.append(c_res["id"])
                    print(f"IG Carousel item {idx + 1} container created: {c_res['id']}")
                else:
                    print(f"Error creating IG item {idx + 1}: {c_res}")

            if ig_container_ids:
                print("Waiting 8 seconds for item containers to process...")
                time.sleep(8)

                main_carousel_url = f"https://graph.facebook.com/v19.0/{IG_USER_ID}/media"
                main_payload = {
                    "media_type": "CAROUSEL",
                    "children": json.dumps(ig_container_ids),
                    "caption": POST_CAPTION,
                    "access_token": FB_TOKEN
                }
                main_res = requests.post(main_carousel_url, data=main_payload).json()
                if "id" in main_res:
                    creation_id = main_res["id"]
                    print(f"Main IG Carousel Container ID: {creation_id}")
                else:
                    print("Error creating main IG carousel:", main_res)

        # पब्लिश करणे (Status Polling सह)
        if creation_id:
            status_url = f"https://graph.facebook.com/v19.0/{creation_id}?fields=status_code&access_token={FB_TOKEN}"
            is_ready = False
            for attempt in range(1, 10):
                print(f"Checking media readiness (Attempt {attempt}/9)...")
                s_res = requests.get(status_url).json()
                status = s_res.get("status_code", "")
                print(f"Current Status: {status}")

                if status == "FINISHED":
                    is_ready = True
                    break
                elif status == "ERROR":
                    print("Meta reported an error processing this container.")
                    break
                time.sleep(5)

            if is_ready:
                publish_url = f"https://graph.facebook.com/v19.0/{IG_USER_ID}/media_publish"
                pub_res = requests.post(publish_url, data={"creation_id": creation_id, "access_token": FB_TOKEN}).json()
                print("Instagram Final Publish Response:", pub_res)
            else:
                print("Could not publish: Media container was not ready in time.")

if __name__ == "__main__":
    main()
