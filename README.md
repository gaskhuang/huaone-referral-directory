# 華One 三層引薦名冊

BNI 華One 分會的成員名冊網站，把每位夥伴簡報裡的**一般引薦 / 理想引薦 / 夢幻引薦**攤在同一頁，
搭配搜尋與產業分類篩選，會前一分鐘就能找到今天該幫誰、該找誰。

資料來源是分會的 Google Drive 簡報資料夾，由腳本自動解析，沒有人工改寫內容。

## 目錄結構

```
docs/            # 網站本體（GitHub Pages 直接吃這個資料夾）
  index.html
  assets/styles.css
  assets/app.js
  data/members.js   # 由 scripts/build.py 產生
scripts/
  fetch.sh       # 從 Drive 抓 118 份成員簡報 → data/raw/*.json
  parse.py       # 版面座標解析 → data/members.json
  lights.py      # 抓區紅綠燈報告比對燈號 → data/lights.json（未進版控）
  build.py       # 併上產業分類與燈號 → docs/data/members.js
data/
  members.tsv    # 檔案 ID ↔ 簡報標題
  members.json   # 解析後的原始欄位（含 leftover 便於除錯）
  raw/           # Drive 原始 JSON，61MB，未進版控
```

## 更新資料

更新分成兩半，因為兩者的憑證需求完全不同。

### 簡報內容（需要 Google 授權 → 本機跑）

```bash
./scripts/update.sh          # 抓取 → 解析 → 燈號 → 產生 → 有變動才 push
./scripts/update.sh --dry    # 只更新本機，不 commit 不 push
./scripts/update.sh --force  # 整批重抓簡報，不看快取
```

`fetch.sh` 會比對 Drive 的 `modifiedTime`，只重抓真的動過的簡報。夥伴每週都在改
本週我有／我要，所以這個增量判斷是必要的——沒異動時整輪 8 秒跑完。

需要 [`gws`](https://github.com/) CLI（Google Workspace CLI）已登入，以及 `jq`。

### 紅綠燈（不需憑證 → GitHub Actions 每週自動跑）

`.github/workflows/weekly-lights.yml` 每週一早上 6 點（台北時間）自動跑
`lights.py` + `build.py` 並 push。來源是公開網頁，不需要任何 secret。

**為什麼簡報那半不放 GitHub Actions**：本機 `gws` 的 OAuth token 有 14 個 scope，
包含 `gmail.modify` 與完整 `drive` 寫入權。把它放進公開 repo 的 Secrets，等於讓一組
能讀寫整個 Gmail 的憑證住在 CI 裡。要搬上去的話得先另外開一組只有
`drive.readonly` + `presentations.readonly` 的憑證，而不是沿用這一組。

## 本機預覽

```bash
python3 -m http.server 4173 --directory docs
```

## 解析邏輯說明

每份簡報的版面是固定樣板，但實際填寫方式差異很大（有人把標題和內容放同一個文字框、有人編號後面沒空格、
有人整份還是空白樣板）。`parse.py` 用的是「版面座標 + 標籤錨點」混合判斷：

- **姓名列**：優先取有 `NO.` 前綴的文字框，排除 `1. 2. 3.` 這種條列
- **三層引薦**：先找含「一般引薦」的框，找不到再退回左下區塊面積最大的框
- **本週我有 / 我要**：以標籤開頭比對，標籤框內沒內容時往正下方找最近的框
- **我的專業**：姓名列以下、三層引薦區以上的所有非標籤框

簡報裡本來就空白的欄位，網站上顯示「尚未填寫」，不會補字。

## 產業分類

`build.py` 依「專業別 → 公司名 → 我的專業」的順序做關鍵字比對，推導出 12 個產業分類供篩選使用。
**這是為了方便篩選而推導的欄位，不是分會的正式分組。** 分類規則在 `scripts/build.py` 的 `CATEGORIES`。

## 紅綠燈燈號

姓名前的圓點取自 [BNI 新北市西B區紅綠燈報告](https://bninwb.autolab.cloud/202607/me.html)。
該頁把全區 1279 位的資料以 `var D=[...]` 內嵌在 HTML 裡，燈號門檻也寫在同一支 script
（70 分綠、50 分黃、30 分紅，其餘黑），`lights.py` 沿用同一套規則，不自行加工。

榜上姓名是「中文名+英文名」黏在一起（`黃俊凱Gask huang`），所以用中文前綴比對，
118 位中比對到 112 位。比對不到的顯示空心圓點，不做模糊猜測——`陳建豪`／榜上`陳健豪`
只差一個字，猜錯就是把別人的績效掛到他頭上。

**原報告載明「僅供區域及分會領導團隊參考，請勿對外散布」，所以網站只輸出燈號顏色，
個人分數與全區排名不寫進 `docs/data/members.js`。** 含分數的 `data/lights.json`
已列入 `.gitignore`。
