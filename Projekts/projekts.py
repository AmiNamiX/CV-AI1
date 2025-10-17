import os
import json
import urllib.request

API_KEY = "AIzaSyAVM1pt3LV0y6AC3CNfpuyWEcx-3Xyjl7s"
MODEL_NAME = "models/gemini-2.5-flash"
GEMINI_URL = f"https://generativelanguage.googleapis.com/v1/{MODEL_NAME}:generateContent?key={API_KEY}"

INPUT_DIR = "sample_inputs"
OUTPUT_DIR = "outputs"

json_files = [] 

def read_text(path):
    with open(path, "r", encoding="utf-8") as f:
        return f.read().strip()

def make_prompt(jd_text, cv_text):
    return f"""
### Darba apraksts

{jd_text}

---

### Kandidāta CV

{cv_text}

---

Pamatojoties uz šo darba aprakstu un kandidāta CV, novērtē kandidāta atbilstību šim darba aprakstam. Lūdzu, sniedz atbildi šādā JSON formātā (latviešu valodā):

{{
  "match_score": 0-100,
  "summary": "Īss apraksts, cik labi CV atbilst JD.",
  "strengths": [
    "Galvenās prasmes/pieredze no CV, kas atbilst JD"
  ],
  "missing_requirements": [
    "Svarīgas JD prasības, kas CV nav redzamas"
  ],
  "verdict": "strong match | possible match | not a match"
}}
"""

def call_gemini(prompt):
    payload = {
        "contents": [
            {
                "role": "user",
                "parts": [{"text": prompt}]
            }
        ],
        "generationConfig": {
            "temperature": 0.3,
            "topP": 1,
            "topK": 1
        }
    }
    headers = {
        'Content-Type': 'application/json'
    }
    data = json.dumps(payload).encode('utf-8')
    req = urllib.request.Request(GEMINI_URL, data=data, headers=headers, method='POST')
    try:
        with urllib.request.urlopen(req) as resp:
            resp_data = resp.read().decode('utf-8')
            return json.loads(resp_data)
    except Exception as e:
        print("Kļūda, izsaucot Gemini API:", e)
        return None

def extract_json(response):
    try:
        text = response["candidates"][0]["content"]["parts"][0]["text"]
        start = text.find("{")
        end = text.rfind("}")
        json_str = text[start:end+1]
        return json.loads(json_str)
    except Exception as e:
        print("Kļūda parsējot Gemini atbildi:", e)
        print("Atbilde:", response)
        return None

def make_report(json_data):
    md = f"""# Kandidāta atbilstības pārskats

**Atbilstības indekss:** {json_data['match_score']}/100  
**Secinājums:** {json_data['verdict']}

## Īss apraksts
{json_data['summary']}

## Stiprās puses
"""
    for s in json_data['strengths']:
        md += f"- {s}\n"
    md += "\n## Trūkstošās prasības\n"
    for m in json_data['missing_requirements']:
        md += f"- {m}\n"
    return md

def main():
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)
    jd_text = read_text(os.path.join(INPUT_DIR, "jd.txt"))

    for i in range(1, 4):
        cv_file = f"cv{i}.txt"
        cv_path = os.path.join(INPUT_DIR, cv_file)
        if not os.path.exists(cv_path):
            print(f"CV fails {cv_file} nav atrasts!")
            continue

        cv_text = read_text(cv_path)
        print(f"CV {cv_file} saturs:\n{cv_text}\n{'-'*40}")
        if not cv_text:
            print(f"CV fails {cv_file} ir tukšs!")
            continue

        prompt = make_prompt(jd_text, cv_text)

        with open(os.path.join(OUTPUT_DIR, f"prompt_{i}.md"), "w", encoding="utf-8") as f:
            f.write(prompt)

        print(f"Sūtu pieprasījumu Gemini par {cv_file} ...")
        response = call_gemini(prompt)

        # Saglabā API atbildi debugam
        api_response_path = os.path.join(OUTPUT_DIR, f"cv{i}_api_response.json")
        with open(api_response_path, "w", encoding="utf-8") as f:
            json.dump(response, f, ensure_ascii=False, indent=2)

        json_data = extract_json(response)

        if not json_data:
            print(f"Kļūda ar kandidātu {i}")
            continue

        json_path = os.path.join(OUTPUT_DIR, f"cv{i}.json")
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(json_data, f, ensure_ascii=False, indent=2)

        report = make_report(json_data)
        report_path = os.path.join(OUTPUT_DIR, f"cv{i}_report.md")
        with open(report_path, "w", encoding="utf-8") as f:
            f.write(report)

        print(f"Izveidots: {json_path} un {report_path}")
        import glob
    for jf in json_files:
        if os.path.exists(jf):
            os.remove(jf)
            print(f"Automātiski dzēsts: {jf}")

if __name__ == "__main__":
    main()
