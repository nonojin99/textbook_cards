"""예약 게시: publish/slots/<YYYY-MM-DD>_<HHMM>_<이름>.json 중 '오늘(KST)·시각이 지난·아직 안 한' 항목을 차례로 올린다.

요청 파일: {"requests": [{"account": "dongyang", "kind": "carousel|image", "media": "cards/…", "caption": "captions/….txt"}, …]}
- 같은 파일 안 요청은 적힌 순서대로, 사이에 GAP 초를 둔다(막 구분 03 → 02 → 01 → 본편 순서가 그리드에 그대로 남게).
- 게시 스위치: publish/LIVE 파일이 있어야 실제로 올린다. 없으면 모든 확인(계정·파일 공개·캡션)만 하고 끝(dry run).
- 처리 기록: publish/.done.json — 요청 단위("파일#번호"). 실패한 요청은 같은 날 다음 실행이 다시 시도한다. 날짜가 지나면 올리지 않는다.
- 같은 캡션이 최근 게시물에 있으면 이미 올라간 것으로 보고 건너뛴다(중복 게시 방지).
"""
import datetime, json, os, pathlib, sys, time
from ig import ROOT, accounts, resolve, call, wait_ready, head_ok, ApiError

KST = datetime.timezone(datetime.timedelta(hours=9))
NOW = datetime.datetime.now(KST)
TODAY = NOW.strftime("%Y-%m-%d")
LIVE = (ROOT / "publish/LIVE").exists() and os.environ.get("FORCE_DRY", "") != "1"
PUBLIC = os.environ.get("PUBLIC_BASE", "https://raw.githubusercontent.com/nonojin99/textbook_cards/main").rstrip("/")
GAP = int(os.environ.get("GAP_SEC", "75"))
DONE_F = ROOT / "publish/.done.json"
done = json.loads(DONE_F.read_text(encoding="utf-8")) if DONE_F.exists() else {}
ACC = accounts()
resolved = {}


def media_files(media):
    d = ROOT / media
    return sorted(p.name for p in d.iterdir() if p.suffix in (".jpg", ".mp4") and p.stem.isdigit())


def check_caption(cap):
    if len(cap) > 2200: raise ApiError(0, f"caption {len(cap)} chars > 2200")
    if cap.count("#") > 5: raise ApiError(0, f"caption has {cap.count('#')} hashtags > 5")


def recent_has(base, uid, tok, cap):
    rec = call(base, "GET", f"{uid}/media", tok, fields="caption,permalink", limit="15").get("data", [])
    return next((r for r in rec if (r.get("caption") or "").strip() == cap.strip()), None)


def child(base, uid, tok, url, is_video):
    if is_video:
        cid = call(base, "POST", f"{uid}/media", tok, media_type="VIDEO", video_url=url, is_carousel_item="true")["id"]
        wait_ready(base, cid, tok)
        return cid
    return call(base, "POST", f"{uid}/media", tok, image_url=url, is_carousel_item="true")["id"]


def publish(req):
    acc = ACC[req["account"]]
    if not acc["token"]:
        raise ApiError(0, f"secret IG_{req['account'].upper()}_ACCESS_TOKEN 없음")
    if req["account"] not in resolved:
        resolved[req["account"]] = resolve(acc)
    base, uid, name = resolved[req["account"]]
    tok = acc["token"]
    files = media_files(req["media"])
    cap = (ROOT / req["caption"]).read_text(encoding="utf-8").strip() if req.get("caption") else ""
    check_caption(cap)
    kind = req.get("kind", "carousel")
    if kind == "carousel" and not 2 <= len(files) <= 10: raise ApiError(0, f"carousel needs 2–10 files, got {len(files)}")
    if kind == "image" and len(files) != 1: raise ApiError(0, f"image post needs 1 file, got {len(files)}")
    urls = [f"{PUBLIC}/{req['media']}/{f}" for f in files]
    for u in urls:
        for _ in range(20):
            if head_ok(u): break
            time.sleep(30)
        else:
            raise ApiError(0, f"not public: {u}")
    print(f"   @{name} · {kind} · {len(files)}장 · 캡션 {len(cap)}자 #{cap.count('#')}")
    if not LIVE:
        return "dry-run ok"
    if cap and recent_has(base, uid, tok, cap):
        return "already posted (same caption)"
    if kind == "image":
        cid = call(base, "POST", f"{uid}/media", tok, image_url=urls[0], caption=cap)["id"]
    else:
        kids = [child(base, uid, tok, u, u.endswith(".mp4")) for u in urls]
        cid = call(base, "POST", f"{uid}/media", tok, media_type="CAROUSEL", children=",".join(kids), caption=cap)["id"]
    wait_ready(base, cid, tok)
    try:
        mid = call(base, "POST", f"{uid}/media_publish", tok, creation_id=cid)["id"]
        return f"published {mid}"
    except ApiError as e:
        if e.status == 403 and "2207051" in e.body and cap:   # 막혔다고 하지만 실제로 올라간 적이 있다 — 15분 동안 확인
            for _ in range(15):
                time.sleep(60)
                if recent_has(base, uid, tok, cap): return "published (confirmed after 403)"
        raise


def main():
    print(f"{NOW:%Y-%m-%d %H:%M} KST · {'LIVE' if LIVE else 'DRY RUN (publish/LIVE 없음)'}")
    fails = 0
    slots = sorted((ROOT / "publish/slots").glob("*.json"))
    for f in slots:
        day, hhmm = f.name[:10], f.name[11:15]
        if day != TODAY or hhmm > NOW.strftime("%H%M"):
            continue
        reqs = json.loads(f.read_text(encoding="utf-8"))["requests"]
        for i, req in enumerate(reqs):
            key = f"{f.name}#{i+1}"
            if LIVE and str(done.get(key, "")).startswith(("published", "already")):
                continue
            print(f"── {key} [{req['account']}] {req['media']}")
            try:
                res = publish(req)
                print("   →", res)
                if LIVE:
                    done[key] = res
                    DONE_F.write_text(json.dumps(done, ensure_ascii=False, indent=1), encoding="utf-8")
                    if i + 1 < len(reqs): time.sleep(GAP)
            except ApiError as e:
                fails += 1
                print(f"::error::{key}: {e}")
                if LIVE:
                    done[key] = f"failed: {str(e)[:200]}"
                    DONE_F.write_text(json.dumps(done, ensure_ascii=False, indent=1), encoding="utf-8")
                break   # 순서가 중요하므로 같은 파일의 뒤 요청은 다음 실행에서
    sys.exit(1 if fails else 0)


if __name__ == "__main__":
    main()
