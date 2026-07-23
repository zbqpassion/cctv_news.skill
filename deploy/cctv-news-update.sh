#!/usr/bin/env bash

set -Eeuo pipefail
umask 027

REPO_DIR="${CCTV_NEWS_REPO_DIR:-/opt/cctv-news-sync}"
BUN_BIN="${CCTV_NEWS_BUN_BIN:-/root/.bun/bin/bun}"
LOCK_FILE="${CCTV_NEWS_LOCK_FILE:-/run/lock/cctv-news-update.lock}"

log() {
  printf '%s %s\n' "$(date --iso-8601=seconds)" "$*"
}

if [[ $# -gt 1 ]] || { [[ $# -eq 1 ]] && [[ ! "$1" =~ ^[0-9]{8}$ ]]; }; then
  echo "Usage: $0 [YYYYMMDD]" >&2
  exit 64
fi

exec 9>"$LOCK_FILE"
if ! flock -n 9; then
  log "Another update is already running; skip."
  exit 0
fi

beijing_hour="$(TZ=Asia/Shanghai date +%H)"
beijing_hour_number=$((10#$beijing_hour))

if [[ $# -eq 0 ]] &&
  ((beijing_hour_number != 0 && (beijing_hour_number < 21 || beijing_hour_number > 23))); then
  log "Outside the scheduled Beijing-time update window; skip."
  exit 0
fi

if [[ $# -eq 1 ]]; then
  target_date="$1"
elif ((beijing_hour_number < 6)); then
  target_date="$(TZ=Asia/Shanghai date --date='yesterday' +%Y%m%d)"
else
  target_date="$(TZ=Asia/Shanghai date +%Y%m%d)"
fi

target_file="news/${target_date}.md"

discard_partial_fetch() {
  git restore --staged --worktree INDEX.md 2>/dev/null || true
  rm -f "$target_file"
  git clean -fd -- dump_htmls >/dev/null 2>&1 || true
}

cd "$REPO_DIR"

if [[ "$(git branch --show-current)" != "main" ]]; then
  log "Expected the main branch in ${REPO_DIR}."
  exit 1
fi

if ! git diff --quiet || ! git diff --cached --quiet; then
  log "Tracked files are dirty; refusing to overwrite local changes."
  exit 1
fi

# Remove only stale untracked output left by an interrupted prior run.
git clean -fd -- dump_htmls "$target_file" >/dev/null

log "Syncing main before fetching ${target_date}."
git fetch origin main
git rebase origin/main

if [[ -s "$target_file" ]]; then
  log "${target_file} already exists; nothing to do."
  exit 0
fi

"$BUN_BIN" install --frozen-lockfile

if ! "$BUN_BIN" run fetch -- "$target_date"; then
  discard_partial_fetch
  log "Fetch failed for ${target_date}; a later timer run will retry."
  exit 1
fi

file_size="$(stat --format=%s "$target_file" 2>/dev/null || printf '0')"
if ((file_size < 1000)) ||
  ! grep -q '^## 新闻摘要' "$target_file" ||
  ! grep -q '^## 详细新闻' "$target_file" ||
  grep -Eq 'ABSTRACT_NOT_FOUND|CONTENT_NOT_FOUND|TITLE_NOT_FOUND' "$target_file"; then
  discard_partial_fetch
  log "Validation failed for ${target_file}; discarded partial output."
  exit 1
fi

if ! "$BUN_BIN" run make-index; then
  discard_partial_fetch
  log "Index generation failed for ${target_date}."
  exit 1
fi

if ! grep -Fq "](./news/${target_date}.md)" INDEX.md; then
  discard_partial_fetch
  log "INDEX.md does not contain ${target_date}; discarded partial output."
  exit 1
fi

git add INDEX.md "$target_file" dump_htmls

if git diff --cached --quiet; then
  log "No changes to commit for ${target_date}."
  exit 0
fi

git commit -m "[bot] AUTO UPDATE"
git fetch origin main
git rebase origin/main
git push origin HEAD:main

log "Published ${target_file} to GitHub."
