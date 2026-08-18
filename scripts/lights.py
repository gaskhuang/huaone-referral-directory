#!/usr/bin/env python3
"""抓 BNI 新北市西B區紅綠燈報告，比對出華One成員的燈號 → data/lights.json

來源頁把全區 1279 位的資料以 `var D=[...]` 內嵌在 HTML 裡，燈號門檻寫在同一支
script：GT=70 綠、YT=50 黃、RT=30 紅、其餘黑。這裡照抄同一套規則，不自行加工。
榜上的姓名是「中文名+英文名」黏在一起（黃俊凱Gask huang），所以用前綴比對。
"""
import json, re, sys, urllib.request

SRC = "https://bninwb.autolab.cloud/202607/me.html"
CHAPTER = "華one"
GT, YT, RT = 70, 50, 30


def light(score):
    if score >= GT:
        return "green"
    if score >= YT:
        return "yellow"
    if score >= RT:
        return "red"
    return "black"


def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read().decode("utf-8", "replace")


def parse(html):
    m = re.search(r"var D=(\[.*?\]);", html, re.S)
    if not m:
        sys.exit("找不到 var D=[...]，來源頁格式可能改了")
    return json.loads(m.group(1))


def period(html):
    m = re.search(r"統計期間\s*([0-9]{4}-[0-9]{2}-[0-9]{2}\s*-\s*[0-9]{4}-[0-9]{2}-[0-9]{2}[^<]*)", html)
    return m.group(1).strip() if m else ""


def norm(s):
    return re.sub(r"\s+", "", s or "")


def main():
    html = fetch(SRC)
    D = parse(html)
    rows = [x for x in D if x["c"] == CHAPTER]
    members = json.load(open("data/members.json", encoding="utf-8"))

    # 榜上姓名 → 取開頭的中文字當比對鍵
    index = {}
    for x in rows:
        cjk = re.match(r"[一-鿿]+", norm(x["n"]))
        if cjk:
            index.setdefault(cjk.group(0), []).append(x)

    out, unmatched, ambiguous = {}, [], []
    for m in members:
        name = norm(m["name"])
        # 先精準比對中文姓名，再退回「榜上姓名以此開頭」
        hits = index.get(name) or [x for x in rows if norm(x["n"]).startswith(name)]
        if not hits:
            # 名冊姓名被解析成暱稱（例：矽谷阿雅）時，改用檔名比對
            title = norm(re.sub(r"^\s*\d{1,3}\s*", "", m["sourceTitle"]))
            hits = [x for x in rows if title and norm(x["n"]).startswith(title[:3])]
        if not hits:
            unmatched.append(m["no"] + m["name"])
            continue
        if len(hits) > 1:
            ambiguous.append(m["no"] + m["name"] + " → " + str([h["n"] for h in hits]))
        x = hits[0]
        out[m["no"] + "-" + m["name"]] = {
            "light": light(x["s"]),
            "score": x["s"],
            "prev": x.get("p"),
            "prevLight": None if x.get("p") is None else light(x["p"]),
            "rank": x.get("r"),
            "isNew": bool(x.get("nw")),
            "listedName": x["n"],
        }

    payload = {
        "source": SRC,
        "period": period(html),
        "total": len(D),
        "chapterCount": len(rows),
        "matched": len(out),
        "thresholds": {"green": GT, "yellow": YT, "red": RT},
        "lights": out,
    }
    json.dump(payload, open("data/lights.json", "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)

    from collections import Counter
    print(f"來源 {SRC}")
    print(f"統計期間 {payload['period']}")
    print(f"全區 {len(D)} 位，{CHAPTER} {len(rows)} 位，比對到 {len(out)} 位")
    print("燈號分佈:", Counter(v["light"] for v in out.values()).most_common())
    if ambiguous:
        print(f"\n同名多筆 {len(ambiguous)}:")
        for a in ambiguous:
            print("  " + a)
    if unmatched:
        print(f"\n比對不到 {len(unmatched)}:")
        print("  " + "、".join(unmatched))


if __name__ == "__main__":
    main()
