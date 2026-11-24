#!/usr/bin/env python3
"""예약 게시 사전 검사 — publish/slots/*.json 이 계정 일정·카드·캡션과 맞는지 기계로 확인한다.
사용: python3 tools/check_slots.py   (FAIL 이 하나라도 있으면 종료 코드 1)"""
import datetime, json, re, sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
# README 의 게시 일정: 키 → (HHMM, 요일 0=월)
SCHEDULE = {"dongyang": ("2000", {0, 3}), "fresco": ("2000", {1, 4}), "why": ("2000", {2, 5}),
            "tken": ("0900", {0, 3}), "mythsen": ("0900", {1, 4})}
# 일정 밖이지만 의도한 슬롯 — 여기에 적어야만 통과한다(이유 필수)
OFF_SCHEDULE = {
    "2026-11-30_2000_why.json": "런칭 목차(월요일 동시 오픈) — 인스타 앱에서 수동 게시·고정 완료, publish/.done.json 에 already 처리",
}
MEDIA = {".jpg", ".mp4"}   # publish_slots.py 와 같은 조건(숫자 이름 + jpg/mp4)
NAME = re.compile(r"^(\d{4}-\d{2}-\d{2})_(\d{4})_([a-z]+)\.json$")

def main():
    accounts = json.loads((ROOT / "accounts.json").read_text())
    out, media_seen = [], Counter()
    F = lambda f, s: out.append(f"FAIL {f}: {s}")
    for f in sorted((ROOT / "publish/slots").glob("*.json")):
        m = NAME.match(f.name)
        if not m: F(f.name, "파일명이 <날짜>_<HHMM>_<키>.json 이 아님"); continue
        day, hhmm, key = datetime.date.fromisoformat(m[1]), m[2], m[3]
        if key not in accounts: F(f.name, f"accounts.json 에 없는 키 {key}"); continue
        t, days = SCHEDULE[key]
        if (hhmm != t or day.weekday() not in days) and f.name not in OFF_SCHEDULE:
            F(f.name, f"{key} 일정은 {t} {'·'.join('월화수목금토일'[d] for d in sorted(days))} — 이 슬롯은 {hhmm} {'월화수목금토일'[day.weekday()]}")
        for i, r in enumerate(json.loads(f.read_text()).get("requests", []), 1):
            tag = f"{f.name}#{i}"
            if r.get("account") != key: F(tag, f"account={r.get('account')} 가 파일명 키 {key} 와 다름")
            d = ROOT / r.get("media", "")
            files = sorted(p for p in d.iterdir() if p.suffix in MEDIA and p.stem.isdigit()) if d.is_dir() else []
            if not files: F(tag, f"카드 폴더가 없거나 비어 있음 {r.get('media')}")
            elif r.get("kind") == "image" and len(files) != 1: F(tag, f"image 인데 파일 {len(files)}개")
            elif r.get("kind") == "carousel" and not 2 <= len(files) <= 10: F(tag, f"carousel 은 2~10장 — {len(files)}장")
            media_seen[r.get("media")] += 1
            cp = ROOT / r.get("caption", "")
            if not cp.is_file(): F(tag, f"캡션 없음 {r.get('caption')}"); continue
            cap = cp.read_text(encoding="utf-8")
            cap = cap.strip()
            if len(cap) > 2200: F(tag, f"캡션 {len(cap)}자 — 인스타 한도 2,200자")
            if cap.count("#") > 5: F(tag, f"해시태그 {cap.count('#')}개 — 게시 스크립트 한도 5개")
            if not cap.strip(): F(tag, "캡션이 비어 있음")
    for media, n in media_seen.items():
        if n > 1: F(media, f"같은 카드 폴더를 {n}번 예약")
    print("\n".join(out) or "PASS")
    print(f"합계: FAIL {len(out)}")
    return 1 if out else 0

if __name__ == "__main__":
    sys.exit(main())
