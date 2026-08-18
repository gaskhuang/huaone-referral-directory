#!/usr/bin/env python3
"""把 members.json 加上自動產業分類，輸出網站用的 site/data/members.js"""
import json, re, os, datetime

# 自動產業分類：先用「專業別」比對，再退回公司名／我的專業。
# 這是為了做篩選而推導出來的欄位，不是分會官方分組。
CATEGORIES = [
    # 寵物相關一律歸生活零售：寵物食品／保健品不是人的餐飲或醫療，
    # 放前面才不會被「食品」「保健」先吃掉
    ("生活零售", r"寵物|毛小孩|貓舍|犬舍"),
    ("金融保險", r"保險|金融|理財|投資|債券|票據|基金|貸款|房貸|財務|會計|記帳|報稅|節稅|信託|資產管理|壽險"),
    ("醫療健康", r"醫療|醫師|中醫|西醫|牙科|牙醫|健康|保健|養生|長照|銀髮|樂齡|藥局|藥師|診所|復健|營養|酵素|身心|舒壓|療癒|檢測"),
    ("美容美業", r"美容|美業|美甲|美學|彩妝|美髮|髮型|皮膚|醫美|造型|保養|香氛|SPA"),
    ("食品餐飲", r"食品|餐飲|餐廳|烘焙|甜點|西點|咖啡|素食|蔬食|無肉|植物肉|天貝|乳酪|橄欖油|紫蘇|醬料|湯底|水產|海鮮|生鮮|水果|蔬果|燕麥|冰淇淋|美食|外燴|餐車|製麵|農場|農|腰果|柚|茶|酒|飲品|零食|即食|廚"),
    ("行銷傳媒", r"行銷|影音|短影音|攝影|影像|拍攝|媒體|直播|網紅|KOL|KOC|私域|廣告|公關|社群|文案|SEO|電商|導演|主持|剪輯|策展|活動企劃|活動統籌|活動執行|印刷|輸出|設計|品牌行銷|品牌策略|品牌顧問|品牌影像|品牌整合|品牌設計|品牌企劃|品牌導演|個人品牌"),
    ("科技數位", r"AI|人工智慧|科技|資訊|系統|軟體|雲端|資安|網路|網站|數位|自動化|智慧製造|工程師|IT|SaaS|投影|通訊|機器人|軟體開發|程式"),
    ("建築居家", r"建築|裝潢|裝修|室內|房地產|不動產|仲介|建商|鍍膜|寢具|家居|家具|清潔|水電|驗屋|居家|空間|營造|工程"),
    ("教育顧問", r"顧問|教育|培訓|講師|教練|課程|教學|職涯|親子|命理|塔羅|生肖|姓名學|能量|學習|補習|訓練"),
    ("生活零售", r"飾品|髮圈|髮飾|服飾|鞋|家用|禮品|禮贈品|選物|文具|寵物|團購|通路|零售|電器|3C|手機|iPhone|筆電|平板|生活用品"),
    ("專業服務", r"律師|法律|會計師|地政|人資|勞資|智慧財產|專利|商標|旅遊|旅行|翻譯|保全|徵信|媒合|經紀|保母|整理|婚禮"),
    ("貿易製造", r"貿易|製造|工廠|代工|OEM|ODM|批發|供應商|經銷|進口|外銷|出口|物流|運通|機械|能源|環保|節能|回收|材料|包裝|五金|化工|市場拓展"),
]



def categorize(m):
    for hay in (m.get("trade", ""),
                m.get("company", ""),
                " ".join(m.get("expertise", [])[:2])):
        if not hay.strip():
            continue
        for name, pat in CATEGORIES:
            if re.search(pat, hay, re.I):
                return name
    return "其他"


def load_lights():
    """scripts/lights.py 產生的燈號，沒跑過就當作沒有資料"""
    try:
        return json.load(open("data/lights.json", encoding="utf-8"))
    except FileNotFoundError:
        return {"lights": {}, "period": "", "source": "", "matched": 0}


def main():
    members = json.load(open("data/members.json", encoding="utf-8"))
    lights = load_lights()
    LT = lights.get("lights", {})
    out = []
    for m in members:
        t = m["tiers"]
        lt = LT.get(m["no"] + "-" + m["name"])
        out.append({
            "no": m["no"],
            "name": m["name"],
            "nickname": m["nickname"],
            "trade": m["trade"],
            "company": m["company"],
            "category": categorize(m),
            "basic": t["basic"],
            "ideal": t["ideal"],
            "dream": t["dream"],
            "have": m["have"],
            "want": m["want"],
            "expertise": m["expertise"],
            "slideUrl": m["slideUrl"],
            "complete": bool(t["basic"] or t["ideal"] or t["dream"]),
            # 只帶顏色。來源報告載明僅供領導團隊參考，分數與排名不對外輸出。
            "light": (lt or {}).get("light"),
        })
    out.sort(key=lambda m: (m["no"], m["name"]))

    os.makedirs("docs/data", exist_ok=True)
    meta = {
        "updated": datetime.date.today().isoformat(),
        "total": len(out),
        "complete": sum(1 for m in out if m["complete"]),
        "categories": sorted({m["category"] for m in out},
                             key=lambda c: -sum(1 for m in out if m["category"] == c)),
        "driveUrl": "https://drive.google.com/drive/folders/1iytHoLg1dH42tUC3GkN1b7mHhG6lgJXE",
        "lightSource": lights.get("source", ""),
        "lightPeriod": lights.get("period", ""),
        "lightMatched": sum(1 for m in out if m["light"]),
    }
    with open("docs/data/members.js", "w", encoding="utf-8") as f:
        f.write("window.HUAONE_META = ")
        json.dump(meta, f, ensure_ascii=False, indent=1)
        f.write(";\nwindow.HUAONE_MEMBERS = ")
        json.dump(out, f, ensure_ascii=False, indent=1)
        f.write(";\n")

    counts = {}
    for m in out:
        counts[m["category"]] = counts.get(m["category"], 0) + 1
    print(f"built docs/data/members.js — {len(out)} 位成員"
          f"（含燈號 {meta['lightMatched']} 位）")
    for c, n in sorted(counts.items(), key=lambda kv: -kv[1]):
        print(f"  {c}: {n}")


if __name__ == "__main__":
    main()
