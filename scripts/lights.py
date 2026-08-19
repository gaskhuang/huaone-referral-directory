#!/usr/bin/env python3
"""抓 BNI 新北市西B區紅綠燈報告，比對出華One成員的燈號 → data/lights.json

來源頁把全區 1279 位的資料以 `var D=[...]` 內嵌在 HTML 裡，燈號門檻寫在同一支
script：GT=70 綠、YT=50 黃、RT=30 紅、其餘黑。這裡照抄同一套規則，不自行加工。
榜上的姓名是「中文名+英文名」黏在一起（黃俊凱Gask huang），所以用前綴比對。
"""
import datetime, json, re, sys, urllib.error, urllib.request

BASE = "https://bninwb.autolab.cloud/{ym}/me.html"
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


def latest_report(back=8):
    """報告網址是 /YYYYMM/me.html，從本月往前找第一份存在的，避免月份寫死。"""
    d = datetime.date.today().replace(day=1)
    for _ in range(back):
        url = BASE.format(ym=d.strftime("%Y%m"))
        try:
            return url, fetch(url)
        except urllib.error.HTTPError as e:
            if e.code != 404:
                raise
        d = (d - datetime.timedelta(days=1)).replace(day=1)
    sys.exit(f"往前找 {back} 個月都沒有紅綠燈報告，來源可能搬家了")


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
    SRC, html = latest_report()
    print(f"使用報告 {SRC}")
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
    # 安全閘：來源頁改格式或分會名稱改字（華one → 華One）時，比對數會崩掉。
    # 這時候寧可整批失敗，也不要讓 build.py 拿空燈號把 112 位的燈號全洗掉。
    floor = int(len(members) * 0.6)
    if len(out) < floor:
        sys.exit(f"只比對到 {len(out)} 位，低於安全下限 {floor}，"
                 f"來源頁可能改格式或分會名稱變了，不覆寫 data/lights.json")

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
