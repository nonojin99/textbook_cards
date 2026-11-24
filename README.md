# textbook_cards — 교과서 카드뉴스 5개 계정 자동 게시

| 키 | 계정 | 게시 시각(KST) |
|---|---|---|
| dongyang | dongyang.cards (삼국지) | 20:00 (월·목) |
| fresco | fresco.myth (그리스 로마 신화) | 20:00 (화·금) |
| why | why.middleschool (중2 과학·수학) | 20:00 (과학 수 · 수학 토) |
| tken | threekingdoms.illustrated | 09:00 (월·목) |
| mythsen | myths.illustrated | 09:00 (화·금) |

- **토큰**: Secrets `IG_<키 대문자>_ACCESS_TOKEN` (Instagram API with Unified Login, 계정마다 1개). 계정 이름은 `accounts.json`.
- **연동 확인**: `Check accounts` 워크플로 → 결과 `status/accounts.json` (토큰이 다른 계정을 가리키면 FAIL). 다시 확인하려면 `status/recheck.txt` 를 바꿔 push 하거나 Actions 에서 Run workflow.
- **예약 게시**: `Publish scheduled posts` 가 30분마다 `publish/slots/<날짜>_<HHMM>_<키>.json` 중 시각이 지난 오늘 항목을 순서대로 올린다.
- **게시 스위치**: `publish/LIVE` 파일이 있어야 실제로 올린다. 없으면 확인만(dry run).
- **게시 기록**: `publish/.done.json`. 실패한 요청은 같은 날 다음 실행이 다시 시도하고, 날짜가 지나면 올리지 않는다.
- **게시 전 검사**: `python3 tools/check_slots.py` — 일정(요일·시각)·카드 장수·캡션 한도·중복 예약을 확인한다. 예약 파일을 push 하면 `Check slots` 워크플로가 자동으로 돌린다. 일정 밖 슬롯은 스크립트의 `OFF_SCHEDULE` 에 이유와 함께 적어야 통과한다. 앱에서 직접 올린 게시물은 `publish/.done.json` 에 `"<슬롯>#<번호>": "already posted (…)"` 로 적어 중복 게시를 막는다.
- 카드·캡션·예약 파일은 원본 작업 폴더의 `tools/package.py` → `tools/export_repo.py` 로 만든다(직접 고치지 않는다).
- 목차 게시물 고정(핀)은 API 로 안 된다 — 게시 뒤 앱에서 직접 고정.
- 토큰 만료 전 갱신(구성 미리보기의 만료 기간 기준). `Check accounts` 가 매주 화 08:00 에 확인한다.
