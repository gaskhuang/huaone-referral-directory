#!/usr/bin/env python3
"""把 Google Slides JSON 解析成 members.json"""
import json, re, os

RAW = "data/raw"
LABELS = {"我的專業", "三層引薦", "本週引薦需求", "華One分會", "華ONE分會",
          "本週我有", "本週我要", "我有", "我要", "投資人", "本週引薦",
          "本週我有資源", "本週我要資源", "我有資源", "我要資源",
          "公司", "公司Logo", "公司 Logo", "職稱", "公司名稱", "專業別"}
PLACEHOLDER = {"公司", "公司Logo", "公司 Logo", "職稱", "公司名稱", "專業別",
               "NO. 專業別：", "NO.專業別：", "專業別："}


def clean(s):
    s = s.replace("\x0b", "\n").replace("\r", "\n")
    s = re.sub(r"[ \t　]+", " ", s)
    s = "\n".join(l.strip() for l in s.split("\n"))
    s = re.sub(r"\n{3,}", "\n\n", s)
    return s.strip()


def boxes(slide):
    out = []
    for el in slide.get("pageElements", []):
        sh = el.get("shape") or {}
        txt = sh.get("text")
        if not txt:
            continue
        raw = "".join(te.get("textRun", {}).get("content", "")
                      for te in txt.get("textElements", []))
        t = clean(raw)
        if not t:
            continue
        tr = el.get("transform", {})
        sz = el.get("size", {})
        out.append({
            "t": t,
            "x": tr.get("translateX", 0) or 0,
            "y": tr.get("translateY", 0) or 0,
            "w": abs((sz.get("width", {}).get("magnitude", 0) or 0) * (tr.get("scaleX", 1) or 1)),
            "h": abs((sz.get("height", {}).get("magnitude", 0) or 0) * (tr.get("scaleY", 1) or 1)),
        })
    return out


def is_label(t):
    s = t.replace("：", "").replace(":", "").strip()
    return (not s) or s in LABELS


NAME_RE = re.compile(r"^\s*(?:no\.?\s*)?(\d{1,3})(?![0-9])(.*)$", re.S | re.I)
NO_PREFIX_RE = re.compile(r"^\s*no\.?\s*\d", re.I)
LIST_RE = re.compile(r"^\s*\d{1,2}\s*[.、)）]")


def strip_label(t):
    return re.sub(r"^\s*(本週)?(我有|我要)(資源)?\s*[：:]?\s*", "", t).strip()


def strip_prefix(t):
    t = re.sub(r"^\s*(公司|公司名稱|職稱|專業別)\s*[：:]\s*", "", t)
    return t.strip()


def find_below(bs, anchor, used):
    cands = [b for b in bs if id(b) not in used
             and b["y"] > anchor["y"] + anchor["h"] * 0.4
             and abs(b["x"] - anchor["x"]) < 900000 and not is_label(b["t"])]
    return min(cands, key=lambda b: b["y"]) if cands else None


def parse_slide(bs, fallback_no=None):
    used = set()
    r = {}

    name_box = None
    cands_n = []
    for b in sorted(bs, key=lambda b: b["y"]):
        if b["y"] > 2_000_000 or is_label(b["t"]):
            continue
        first = b["t"].split("\n")[0]
        if LIST_RE.match(first) and not NO_PREFIX_RE.match(first):
            continue
        if NAME_RE.match(first):
            cands_n.append(b)
    cands_n.sort(key=lambda b: (0 if NO_PREFIX_RE.match(b["t"].split("\n")[0]) else 1, b["y"]))
    if cands_n:
        b = cands_n[0]
        m = NAME_RE.match(b["t"].split("\n")[0])
        name_box = b
        r["no"] = m.group(1).zfill(3)
        nl = re.sub(r"^\s*編號\s*", "", m.group(2))
        r["name_line"] = clean(nl + "\n" + "\n".join(b["t"].split("\n")[1:]))
    if name_box:
        used.add(id(name_box))
    else:
        r["no"] = fallback_no or "---"
        r["name_line"] = ""

    ny = name_box["y"] if name_box else 900_000

    comp = [b for b in bs if id(b) not in used and not is_label(b["t"])
            and b["y"] < ny + 60_000 and b["y"] > 200_000]
    comp.sort(key=lambda b: -b["y"])
    comp = [b for b in comp if b["t"].strip() not in PLACEHOLDER]
    r["company"] = strip_prefix(comp[0]["t"]) if comp else ""
    if comp:
        used.add(id(comp[0]))

    tier = None
    for b in bs:
        if id(b) in used:
            continue
        if re.search(r"(一般引薦|一般\s*[：:]|基本引薦)", b["t"]):
            tier = b
            break
    if tier is None:
        cands = [b for b in bs if id(b) not in used and not is_label(b["t"])
                 and b["y"] > 2_900_000 and b["x"] < 3_000_000]
        tier = max(cands, key=lambda b: len(b["t"])) if cands else None
    if tier:
        used.add(id(tier))
    r["tier_raw"] = tier["t"] if tier else ""

    def grab(kw, xmin, xmax):
        hits = [b for b in bs if id(b) not in used and re.search(kw, b["t"])]
        for b in sorted(hits, key=lambda b: -len(b["t"])):
            body = strip_label(b["t"])
            used.add(id(b))
            if body:
                return body
            below = find_below(bs, b, used)
            if below:
                used.add(id(below))
                return below["t"]
            return ""
        cands = [b for b in bs if id(b) not in used and not is_label(b["t"])
                 and b["y"] > 3_000_000 and xmin <= b["x"] < xmax]
        if cands:
            b = max(cands, key=lambda b: len(b["t"]))
            used.add(id(b))
            return b["t"]
        return ""

    r["have"] = grab(r"^\s*(本週)?我有(資源)?\s*[：:]?", 3_000_000, 5_800_000)
    r["want"] = grab(r"^\s*(本週)?我要(資源)?\s*[：:]?", 5_800_000, 99_000_000)

    exp = [b for b in bs if id(b) not in used and not is_label(b["t"])
           and b["y"] > ny + 100_000 and b["y"] < 3_100_000]
    exp.sort(key=lambda b: (b["y"], b["x"]))
    r["expertise"] = "\n".join(b["t"] for b in exp)
    for b in exp:
        used.add(id(b))

    r["leftover"] = [b["t"] for b in bs if id(b) not in used and not is_label(b["t"])]
    return r


def split_tiers(raw):
    if not raw:
        return {"basic": "", "ideal": "", "dream": ""}
    txt = raw

    def seg(a, b):
        ma = re.search(a, txt)
        if not ma:
            return ""
        start = ma.end()
        mb = re.search(b, txt[start:]) if b else None
        end = start + mb.start() if mb else len(txt)
        return clean(txt[start:end].lstrip("：: \n"))

    A = r"(?:一般引薦|基本引薦|一般)\s*[：:]?"
    B = r"(?:理想引薦|理想)\s*[：:]?"
    C = r"(?:夢幻引薦|夢幻)\s*[：:]?"
    return {"basic": seg(A, B), "ideal": seg(B, C), "dream": seg(C, None)}


def split_name(line):
    line = clean(line)
    line = re.sub(r"^[\s.、,，:：\-－)）]+", "", line)
    parts = [p for p in line.split("\n") if p.strip()]
    head = parts[0] if parts else ""
    trade = "\n".join(parts[1:]).strip()
    m = re.match(r"^\s*([一-鿿]{2,4})(.*)$", head)
    if not m:
        return head, "", trade
    name = m.group(1)
    rest = m.group(2).strip()
    nick = ""
    mp = re.match(r"^[（(]([^）)]*)[）)]\s*(.*)$", rest)
    if mp:
        nick, rest = mp.group(1), mp.group(2).strip()
    elif rest:
        toks = [t for t in rest.split(" ") if t]
        if toks and re.match(r"^[A-Za-z][A-Za-z0-9.\-']*[一-鿿]{0,3}$", toks[0]):
            nick, rest = toks[0], " ".join(toks[1:]).strip()
    if not trade:
        trade = rest
    elif rest:
        trade = rest + " " + trade
    trade = strip_prefix(clean(trade))
    if re.match(r"^\s*no\.?\s*$|^\s*no\.?\s*專業別", trade, re.I):
        trade = ""
    return name, nick.strip(), trade


def bullets(s):
    if not s:
        return []
    out = []
    for ln in s.split("\n"):
        ln = re.sub(r"^\s*(?:[●•‧・\-—*]|\d+\s*[.、)）])\s*", "", ln).strip()
        if ln:
            out.append(ln)
    return out


members = []
titles = {}
for line in open("data/members.tsv", encoding="utf-8"):
    fid, title = line.rstrip("\n").split("\t", 1)
    titles[fid] = title.strip()

for fid, title in titles.items():
    path = f"{RAW}/{fid}.json"
    if not os.path.exists(path):
        continue
    doc = json.load(open(path, encoding="utf-8"))
    tno = re.match(r"\s*(\d{1,3})", title)
    fallback_no = tno.group(1).zfill(3) if tno else None
    for si, slide in enumerate(doc.get("slides", [])):
        bs = boxes(slide)
        if len(bs) < 3:
            continue
        r = parse_slide(bs, fallback_no)
        name, nick, trade = split_name(r["name_line"])
        if not name:
            tn = re.sub(r"^\s*\d{1,3}\s*", "", title).strip()
            name = tn.split(" ")[0] if tn else title
        exp_list = bullets(r["expertise"])
        if not trade and exp_list:
            head = strip_prefix(exp_list[0])
            if len(head) <= 22 and len(exp_list) > 1:
                trade, exp_list = head, exp_list[1:]
        if not trade:
            for lo in r["leftover"]:
                lo = strip_prefix(lo)
                if 2 <= len(lo) <= 22 and "\n" not in lo:
                    trade = lo
                    break
        members.append({
            "no": r["no"],
            "name": name,
            "nickname": nick,
            "trade": trade,
            "company": r["company"],
            "tiers": split_tiers(r["tier_raw"]),
            "tier_raw": r["tier_raw"],
            "have": bullets(r["have"]),
            "want": bullets(r["want"]),
            "expertise": exp_list,
            "slideId": fid,
            "slideIndex": si,
            "slideUrl": f"https://docs.google.com/presentation/d/{fid}/edit",
            "sourceTitle": title,
            "leftover": r["leftover"],
        })

def richness(m):
    return (len(m["tier_raw"]) + len(" ".join(m["have"])) + len(" ".join(m["want"]))
            + len(" ".join(m["expertise"])) + len(m["company"]))


best = {}
for m in members:
    key = (m["no"], m["name"], m["slideIndex"])
    if key not in best or richness(m) > richness(best[key]):
        best[key] = m
members = list(best.values())
members.sort(key=lambda m: (m["no"], m["slideIndex"]))
json.dump(members, open("data/members.json", "w", encoding="utf-8"),
          ensure_ascii=False, indent=1)
print(f"parsed {len(members)} entries")
print("missing basic:", [m["no"] + m["name"] for m in members if not m["tiers"]["basic"]])
print("missing company:", [m["no"] + m["name"] for m in members if not m["company"]])
print("missing trade:", [m["no"] + m["name"] for m in members if not m["trade"]])
print("missing expertise:", [m["no"] + m["name"] for m in members if not m["expertise"]])
print("no have:", len([m for m in members if not m["have"]]),
      "| no want:", len([m for m in members if not m["want"]]))
