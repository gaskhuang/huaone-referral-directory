#!/bin/zsh
# 每週更新：重抓有改過的簡報 → 解析 → 更新燈號 → 產生網站資料 → 推上 GitHub Pages
#
#   ./scripts/update.sh          正常更新並推上線
#   ./scripts/update.sh --dry    只更新本機，不 commit 不 push
#   ./scripts/update.sh --force  整批重抓簡報（不看快取）
set -e
cd "$(dirname "$0")/.."

DRY=0
FETCH_ARGS=()
for a in "$@"; do
  case "$a" in
    --dry) DRY=1 ;;
    --force) FETCH_ARGS+=(--force) ;;
    *) echo "未知參數：$a"; exit 1 ;;
  esac
done

log() { print -P "%F{cyan}▸%f $1" }

# --- 前置檢查：gws 沒登入的話後面全都會靜默失敗 ---
if ! command -v gws >/dev/null; then
  echo "找不到 gws CLI，無法更新簡報。安裝後再跑一次。"; exit 1
fi
if ! gws drive files list --params '{"pageSize":1}' >/dev/null 2>&1; then
  echo "gws 未登入或授權過期，先跑 gws auth login 再回來。"; exit 1
fi

before=$(md5 -q docs/data/members.js 2>/dev/null || echo none)

log "1/4 抓取簡報"
./scripts/fetch.sh "${FETCH_ARGS[@]}"

log "2/4 解析簡報"
python3 scripts/parse.py

log "3/4 更新紅綠燈"
# 燈號抓不到就沿用上次的，不要讓整批更新失敗
if ! python3 scripts/lights.py; then
  echo "   紅綠燈來源抓取失敗，沿用上次的 data/lights.json"
fi

log "4/4 產生網站資料"
python3 scripts/build.py

after=$(md5 -q docs/data/members.js)

if [[ "$before" == "$after" ]]; then
  log "資料沒有變動，不需要部署"
  exit 0
fi

if [[ $DRY -eq 1 ]]; then
  log "--dry：本機已更新，未 commit。用 python3 -m http.server 4173 --directory docs 預覽"
  exit 0
fi

log "推上 GitHub Pages"
git add data/members.json data/members.tsv docs/data/members.js
git commit -q -m "每週更新：同步簡報內容與紅綠燈燈號 $(date '+%Y-%m-%d')"
git push -q origin main

log "完成。約 1-2 分鐘後生效：https://gaskhuang.github.io/huaone-referral-directory/"
