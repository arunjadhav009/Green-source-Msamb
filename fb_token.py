"""Facebook token सुरक्षितपणे मिळवणे.

- token कधीही code मध्ये लिहायचा नाही. तो GitHub → Settings → Secrets → FB_TOKEN मधून येतो.
- System User token वरून Page token काढला जातो. तो पण GitHub logs मध्ये लपवला (***) जातो.
"""
import os
import sys

import requests

PAGE_ID = "609269705592123"
DRY_RUN = os.environ.get("DRY_RUN", "false").strip().lower() == "true"


def mask(value):
    """GitHub Actions ला सांगणे: ही value logs मध्ये कुठेही आली तर *** दाखव."""
    if value and os.environ.get("GITHUB_ACTIONS") == "true":
        print(f"::add-mask::{value}", flush=True)


def page_token():
    token = os.environ.get("FB_TOKEN", "").strip()
    if not token:
        print("❌ FB_TOKEN secret सापडला नाही. Repo → Settings → Secrets and variables → Actions मध्ये FB_TOKEN टाका.")
        sys.exit(1)
    mask(token)
    try:
        res = requests.get(
            f"https://graph.facebook.com/{PAGE_ID}",
            params={"fields": "access_token"},
            headers={"Authorization": f"Bearer {token}"},
            timeout=30,
        ).json()
        page = res.get("access_token")
        if page:
            mask(page)
            return page
        if "error" in res:
            print("⚠️ Page token मिळाला नाही:", res["error"].get("message", ""))
    except Exception as e:
        print("⚠️ Page token मिळवताना अडचण:", type(e).__name__)
    return token
