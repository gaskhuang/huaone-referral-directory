#!/bin/zsh
# 從分會 Drive 資料夾抓成員簡報（需要 gws CLI 已登入）
#
# 預設只重抓「Drive 上的 modifiedTime 比本機快取新」的簡報，因為夥伴每週都會改
# 本週我有／我要。加 --force 就整批重抓。
set -e
cd "$(dirname "$0")/.."

FOLDER_ID="1iytHoLg1dH42tUC3GkN1b7mHhG6lgJXE"
FORCE=0
[[ "$1" == "--force" ]] && FORCE=1

mkdir -p data/raw
[[ -f data/mtimes.json ]] || echo '{}' > data/mtimes.json

echo "→ 取得資料夾清單…"
gws drive files list \
  --params "{\"q\":\"'$FOLDER_ID' in parents and trashed=false\",\"pageSize\":200,\"fields\":\"nextPageToken,files(id,name,mimeType,modifiedTime)\"}" \
  --page-all 2>/dev/null > data/files.ndjson

# 只要「編號 姓名」開頭的個人簡報，排除 H1/G1 統整簡報與空白簡報。
# 注意要在 jq 裡針對 .name 過濾——用 grep 比對整行會連 modifiedTime 的開頭數字一起中。
jq -sr '[.[].files[]] | .[]
        | select(.mimeType=="application/vnd.google-apps.presentation")
        | select(.name | test("^\\s*[0-9]{1,3}[^0-9]"))
        | [.id,.name,.modifiedTime] | @tsv' data/files.ndjson > data/members_full.tsv

cut -f1,2 data/members_full.tsv > data/members.tsv
echo "→ 共 $(wc -l < data/members.tsv | tr -d ' ') 份成員簡報"

fetched=0
skipped=0
while IFS=$'\t' read -r id name mtime; do
  out="data/raw/${id}.json"
  cached=$(jq -r --arg id "$id" '.[$id] // ""' data/mtimes.json)
  if [[ $FORCE -eq 0 && -s "$out" && "$cached" == "$mtime" ]]; then
    skipped=$((skipped+1))
    continue
  fi
  gws slides presentations get --params "{\"presentationId\":\"$id\"}" 2>/dev/null > "$out"
  if jq -e '.slides' "$out" >/dev/null 2>&1; then
    jq --arg id "$id" --arg t "$mtime" '.[$id]=$t' data/mtimes.json > data/mtimes.tmp \
      && mv data/mtimes.tmp data/mtimes.json
    fetched=$((fetched+1))
    echo "   更新 $name"
  else
    echo "   FAIL $id $name" | tee -a data/fetch_errors.log
    rm -f "$out"
  fi
done < data/members_full.tsv

echo "→ 重抓 $fetched 份、沿用快取 $skipped 份，data/raw 內共 $(ls data/raw | wc -l | tr -d ' ') 份"
