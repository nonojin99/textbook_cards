"""인스타그램 게시 공용 함수 (교과서 카드뉴스 5개 계정).

토큰: GitHub Secrets IG_<KEY>_ACCESS_TOKEN (KEY = accounts.json 의 키를 대문자로).
계정 이름: accounts.json (Variables EXPECT_<KEY>_USERNAME 이 있으면 그쪽이 이긴다).
API: Unified Login(Facebook Login for Business) 토큰은 graph.facebook.com, Instagram Login 토큰은 graph.instagram.com.
     resolve() 가 토큰으로 두 경로를 차례로 시도해 계정 ID·이름·API 주소를 찾는다.
토큰 값은 절대 출력하지 않는다(오류 메시지에서도 지운다).
"""
import json, os, pathlib, time, urllib.error, urllib.parse, urllib.request

ROOT = pathlib.Path(__file__).resolve().parents[2]
VER_FB = os.environ.get("FB_API_VERSION", "v24.0")
VER_IG = os.environ.get("IG_API_VERSION", "v23.0")
FB = f"https://graph.facebook.com/{VER_FB}"
IGB = f"https://graph.instagram.com/{VER_IG}"


def accounts():
    a = json.loads((ROOT / "accounts.json").read_text(encoding="utf-8"))
    out = {}
    for key, name in a.items():
        name = (os.environ.get(f"EXPECT_{key.upper()}_USERNAME") or name).strip().lstrip("@")
        out[key] = dict(key=key, expect=name, token=os.environ.get(f"IG_{key.upper()}_ACCESS_TOKEN", "").strip())
    return out


class ApiError(Exception):
    def __init__(self, status, body):
        self.status, self.body = status, body
        super().__init__(f"HTTP {status}: {body}")


def _clean(s, token):
    return s.replace(token, "***") if token else s


def call(base, method, path, token, **params):
    params["access_token"] = token
    data = urllib.parse.urlencode(params).encode()
    url = f"{base}/{path}"
    if method == "GET":
        req = urllib.request.Request(url + "?" + data.decode())
    else:
        req = urllib.request.Request(url, data=data, method=method)
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        body = _clean(e.read().decode(errors="replace"), token)[:600]
        raise ApiError(e.code, body) from None
    except urllib.error.URLError as e:
        raise ApiError(0, _clean(str(e), token)) from None


def resolve(acc):
    """토큰 → (API 주소, 인스타 계정 ID, 계정 이름). 맞는 계정을 못 찾으면 ApiError."""
    tok, want = acc["token"], acc["expect"].lower()
    tried = []
    # ① Unified Login: 토큰에 배정된 인스타 계정 목록
    try:
        d = call(FB, "GET", "me/assigned_instagram_accounts", tok, fields="id,username")
        for x in d.get("data", []):
            if (x.get("username") or "").lower() == want:
                return FB, x["id"], x["username"]
        tried.append("assigned_instagram_accounts: " + ", ".join(x.get("username", "?") for x in d.get("data", [])))
    except ApiError as e:
        tried.append(f"assigned_instagram_accounts: {e}")
    # ② Facebook 사용자 토큰: 연결된 페이지의 인스타 계정
    try:
        d = call(FB, "GET", "me/accounts", tok, fields="instagram_business_account{id,username}")
        for p in d.get("data", []):
            x = p.get("instagram_business_account") or {}
            if (x.get("username") or "").lower() == want:
                return FB, x["id"], x["username"]
        tried.append("me/accounts: " + ", ".join((p.get("instagram_business_account") or {}).get("username", "-") for p in d.get("data", [])))
    except ApiError as e:
        tried.append(f"me/accounts: {e}")
    # ③ Instagram Login 토큰
    try:
        d = call(IGB, "GET", "me", tok, fields="user_id,username")
        if (d.get("username") or "").lower() == want:
            return IGB, d.get("user_id") or d.get("id"), d["username"]
        tried.append(f"graph.instagram.com/me: @{d.get('username')}")
    except ApiError as e:
        tried.append(f"graph.instagram.com/me: {e}")
    raise ApiError(0, f"@{acc['expect']} 계정을 이 토큰으로 찾지 못함 — " + " | ".join(tried))


def wait_ready(base, cid, token, timeout=900):
    t0 = time.time()
    while time.time() - t0 < timeout:
        s = call(base, "GET", cid, token, fields="status_code").get("status_code")
        if s == "FINISHED":
            return
        if s in ("ERROR", "EXPIRED"):
            raise ApiError(0, f"container {cid} status {s}")
        time.sleep(8)
    raise ApiError(0, f"container {cid} not ready after {timeout}s")


def head_ok(url):
    try:
        with urllib.request.urlopen(urllib.request.Request(url, method="HEAD"), timeout=30) as r:
            return r.status == 200
    except Exception:
        return False
