#!/usr/bin/env python3
"""위비티·콘테스트코리아·씽유에서 접수중 공모전을 모아 index.html 생성."""
import re, json, html, datetime, urllib.request
from concurrent.futures import ThreadPoolExecutor
from zoneinfo import ZoneInfo

NOW = datetime.datetime.now(ZoneInfo("Asia/Seoul"))
TODAY = NOW.date()
UA = {"User-Agent": "Mozilla/5.0"}

def get(u):
    for _ in range(3):
        try:
            return urllib.request.urlopen(urllib.request.Request(u, headers=UA), timeout=30).read().decode("utf-8", "ignore")
        except Exception:
            pass
    return ""

def pmap(f, xs):
    with ThreadPoolExecutor(8) as ex:
        return list(ex.map(f, xs))

# ---------- 위비티 ----------
def wevity():
    def page(a):
        mode, p = a
        t = get(f"https://www.wevity.com/?c=find&s=1&gub=1&gbn=list{mode}&gp={p}")
        out = []
        for b in t.split("<li"):
            if "ix=" not in b or 'class="tit"' not in b:
                continue
            m = re.search(r'<a href="([^"]+)">(.*?)</a>', b, re.S)
            d = re.search(r'class="day">\s*D-(\d+)', b)
            if not m or not d:
                continue
            cat = re.search(r"분야 : (.*?)</div>", b, re.S)
            org = re.search(r'class="organ">(.*?)</div>', b, re.S)
            out.append(dict(
                id=re.search(r"ix=(\d+)", m.group(1)).group(1),
                t=re.sub(r"\s*SPECIAL\s*$", "", html.unescape(re.sub(r"<[^>]+>", "", m.group(2))).strip()),
                o=html.unescape(org.group(1)).strip() if org else "",
                c=[x.strip() for x in html.unescape(cat.group(1)).split(",")] if cat else [],
                n=int(d.group(1))))
        return out
    jobs = [("&mode=ing", p) for p in range(1, 26)] + [("&mode=soon", p) for p in range(1, 12)] + [("", p) for p in range(1, 40)]
    res = {}
    for L in pmap(page, jobs):
        for x in L:
            res[x["id"]] = x
    return [dict(t=x["t"], o=x["o"], c=x["c"], n=x["n"], link=f"https://www.wevity.com/?c=find&s=1&gub=1&gbn=view&ix={x['id']}") for x in res.values()]

# ---------- 콘테스트코리아 ----------
def contestkorea():
    def page(a):
        code, p = a
        t = get(f"https://www.contestkorea.com/sub/list.php?int_gbn=1&Txt_bcode={code}&page={p}")
        out = []
        for r in t.split("<li>"):
            m = re.search(r'href="view\.php\?int_gbn=1&Txt_bcode=(\d+)&str_no=(\d+)"', r)
            tt = re.search(r'<span class="txt">(.*?)</span>', r, re.S)
            d = re.search(r"<em>접수</em>\s*(\d\d)\.(\d\d)\s*~\s*(\d\d)\.(\d\d)", r)
            if not (m and tt and d):
                continue
            cond = re.search(r'class="condition">(.*?)<', r)
            if cond and cond.group(1) == "접수예정":
                continue
            a_, b_, c_, e_ = map(int, d.groups())
            y = TODAY.year
            try:
                s = datetime.date(y, a_, b_); end = datetime.date(y, c_, e_)
            except ValueError:
                continue
            if end < s:
                end = datetime.date(y + 1, c_, e_)
            if s > TODAY or end < TODAY:
                continue
            org = re.search(r"<strong>주최</strong> \. (.*?)</li>", r)
            out.append(dict(
                t=html.unescape(tt.group(1)).strip(),
                o=html.unescape(org.group(1)).strip() if org else "",
                c=[html.unescape(x) for x in re.findall(r'class="category">(.*?)</span>', r)],
                n=(end - TODAY).days,
                link=f"https://www.contestkorea.com/sub/view.php?int_gbn=1&Txt_bcode={m.group(1)}&str_no={m.group(2)}"))
        return out
    codes = ["031210001", "030310001", "030610001", "030210001", "030110001"]
    return [x for L in pmap(page, [(c, p) for c in codes for p in range(1, 21)]) for x in L]

# ---------- 씽유 ----------
def thinkyou():
    F = {0: "아이디어/마케팅", 1: "광고/디자인/웹툰", 2: "영상/UCC/사진", 3: "학술/논문", 4: "문학예술", 5: "IT/SW"}
    def page(a):
        f, st, p = a
        t = get(f"https://thinkyou.co.kr/contest/?serfield={f}&serstatus={st}&page={p}&pagesize=45")
        out = []
        for r in t.split('<div class="tr ">')[1:]:
            m = re.search(r'href="/contest/(\d+)/', r); h = re.search(r"<h3>(.*?)</h3>", r, re.S)
            d = re.search(r"~ (\d\d)-(\d\d)-(\d\d)", r)
            if not (m and h and d):
                continue
            end = datetime.date(2000 + int(d.group(1)), int(d.group(2)), int(d.group(3)))
            if end < TODAY:
                continue
            o = re.search(r"주최 : (.*?)&nbsp;", r)
            out.append(dict(t=re.sub(r"<[^>]+>", "", html.unescape(h.group(1))).strip(),
                            o=html.unescape(o.group(1)).strip() if o else "", c=[F[f]], n=(end - TODAY).days,
                            link=f"https://thinkyou.co.kr/contest/{m.group(1)}/"))
        return out
    return [x for L in pmap(page, [(f, s, p) for f in F for s in "01" for p in range(1, 6)]) for x in L]

# ---------- 합치기 ----------
CATS = ["영상·사진", "기획·마케팅", "디자인·미술", "글·학술", "IT·과학", "기타"]
def cat(cs):
    s = " ".join(cs); o = []
    if re.search(r"영상|UCC|사진|영화", s): o.append("영상·사진")
    if re.search(r"기획|아이디어|마케팅|광고|네이밍|슬로건|홍보", s): o.append("기획·마케팅")
    if re.search(r"디자인|웹툰|캐릭터|미술|건축|그림|만화", s): o.append("디자인·미술")
    if re.search(r"문학|글|시나리오|논문|학술|수기|리포트", s): o.append("글·학술")
    if re.search(r"IT|SW|웹(?!툰)|게임|소프트|과학", s): o.append("IT·과학")
    return o or ["기타"]

def main():
    norm = lambda s: re.sub(r"[^0-9a-z가-힣]", "", s.lower())
    merged = {}
    for src, L in [("위비티", wevity()), ("콘테스트코리아", contestkorea()), ("씽유", thinkyou())]:
        print(src, len(L))
        for x in L:
            k = norm(x["t"])
            if k in merged:
                if all(s[0] != src for s in merged[k]["s"]):
                    merged[k]["s"].append([src, x["link"]])
                continue
            dl = TODAY + datetime.timedelta(days=x["n"])
            merged[k] = dict(t=x["t"], o=x["o"], c=cat(x["c"]), n=x["n"], dl=dl.isoformat(), s=[[src, x["link"]]])
    data = sorted(merged.values(), key=lambda z: z["n"])
    data = [z for z in data if z["n"] >= 0]
    page = open("template.html", encoding="utf-8").read()
    page = page.replace("__DATA__", json.dumps(data, ensure_ascii=False).replace("</", "<\\/"))
    page = page.replace("__CATS__", json.dumps(CATS, ensure_ascii=False))
    page = page.replace("__UPDATED__", NOW.strftime("%Y-%m-%d %H:%M"))
    open("index.html", "w", encoding="utf-8").write(page)
    print("total", len(data))

if __name__ == "__main__":
    main()
