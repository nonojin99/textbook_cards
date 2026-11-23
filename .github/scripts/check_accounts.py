"""5개 계정 연동 확인(게시 없음). 결과를 status/accounts.json 에 쓴다(토큰·ID 숫자 없이 성공 여부만)."""
import datetime, json, sys
from ig import ROOT, accounts, resolve, call, ApiError

out, bad = {}, 0
for key, acc in accounts().items():
    r = {"expect": acc["expect"]}
    if not acc["token"]:
        r.update(ok=False, error=f"secret IG_{key.upper()}_ACCESS_TOKEN 없음"); bad += 1
    else:
        try:
            base, uid, name = resolve(acc)
            lim = call(base, "GET", f"{uid}/content_publishing_limit", acc["token"], fields="quota_usage,config")
            r.update(ok=True, username=name, api=base.split("/")[2], quota=(lim.get("data") or [{}])[0].get("quota_usage"))
        except ApiError as e:
            r.update(ok=False, error=str(e)[:500]); bad += 1
    out[key] = r
    print(key, "OK" if r["ok"] else "FAIL", r.get("username", ""), r.get("api", ""), r.get("error", ""))
now = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=9))).isoformat(timespec="minutes")
(ROOT / "status").mkdir(exist_ok=True)
(ROOT / "status/accounts.json").write_text(json.dumps({"checked": now, "accounts": out}, ensure_ascii=False, indent=1), encoding="utf-8")
sys.exit(1 if bad else 0)
