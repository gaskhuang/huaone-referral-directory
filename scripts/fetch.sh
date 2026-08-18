#!/bin/zsh
# 從分會 Drive 資料夾抓取所有成員簡報（需要 gws CLI 已登入）
set -e
cd "$(dirname "$0")/.."
FOLDER_ID="1iytHoLg1dH42tUC3GkN1b7mHhG6lgJXE"
mkdir -p data/raw

echo "→ 取得資料夾清單…"
gws drive files list \
  --params "{\"q\":\"'$FOLDER_ID' in parents and trashed=false\",\"pageSize\":200,\"fields\":\"nextPageToken,files(id,name,mimeType,modifiedTime)\"}" \
  --page-all 2>/dev/null > data/files.ndjson

jq -sr '[.[].files[]] | .[]
        | select(.mimeType=="application/vnd.google-apps.presentation")
        | [.id,.name] | @tsv' data/files.ndjson \
  | grep -E $'\t *[0-9]{1,3}' > data/members.tsv

echo "→ 共 $(wc -l < data/members.tsv) 份成員簡報"

while IFS=$'\t' read -r id name; do
  out="data/raw/${id}.json"
  [[ -s "$out" ]] && continue
  gws slides presentations get --params "{\"presentationId\":\"$id\"}" 2>/dev/null > "$out"
  if ! jq -e '.slides' "$out" >/dev/null 2>&1; then
    echo "FAIL $id $name" >> data/fetch_errors.log
    rm -f "$out"
  fi
done < data/members.tsv

echo "→ 完成，data/raw 內有 $(ls data/raw | wc -l | tr -d ' ') 份"
