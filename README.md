# Green Source — MSAMB कांदा बाजारभाव automation

n8n शिवाय, पूर्णपणे GitHub Actions वर चालणारे Green Source चे काम.

| Workflow | काय करतो | कधी |
|---|---|---|
| `MSAMB Daily Post (FB + Insta)` | MSAMB वेबसाइटवरून कांदा भाव → Top 5 कव्हर + सर्व भावांच्या images → Facebook + Instagram पोस्ट | रोज 7:00 PM (IST) |
| `FB + Insta कांदा Auto Reply` | "कांदा / प्याज / onion / राज्याचं नाव" कमेंटला योग्य पोस्टकडे पाठवणारा रिप्लाय | दर 15 मिनिटांनी |

## सुरक्षितता
- Facebook token **कधीही code मध्ये लिहायचा नाही.** तो फक्त `Settings → Secrets and variables → Actions → Secrets → FB_TOKEN` मध्ये असतो.
- Logs मध्ये token आपोआप `***` दिसतो. कमेंट करणाऱ्यांची नावं logs मध्ये छापली जात नाहीत.

## चालू / बंद
- `Settings → Secrets and variables → Actions → Variables → LIVE`
  - `true` = रोजचं schedule चालू
  - `false` (किंवा variable नाही) = schedule बंद; फक्त हाताने "Run workflow" करता येतो
- हाताने चालवताना `no` निवडलं तर **test mode**: images बनतात / रिप्लाय दाखवले जातात, पण काहीही पोस्ट होत नाही.

## फाइल्स
- `generate_and_post.py` — images बनवणे आणि FB/Insta पोस्ट
- `msamb_fetch.py` — MSAMB वरून डेटा, तारीख फिल्टर, आवकनुसार sort, 14-14 ओळींची पाने
- `msamb_cover/` — Top 5 कव्हर डिझाइन (`content.json` मध्ये रोजचे प्रश्न बदलता येतात)
- `comment_reply.py` — auto reply (वर "इथे बदल करू शकता" भागात शब्द, राज्यं, मेसेज बदलता येतात)
- `state/replied.json` — कोणत्या कमेंटला रिप्लाय गेला त्याची यादी
- `data/msamb/` — रोजचा MSAMB डेटा (CSV)
