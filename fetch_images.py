#!/usr/bin/env python3
"""Download watermark-free original images (v2-<token>, no _r suffix) and equation SVGs for every
item in items/, then rewrite the @@IMG:...@@ / @@EQ:...@@ placeholders in index.md / index.html.
Resumable: files already on disk are skipped; run again to retry failures."""
import os, re, sys, glob, json, urllib.request, urllib.parse
from concurrent.futures import ThreadPoolExecutor

ROOT = os.path.dirname(os.path.abspath(__file__))
UA = {"User-Agent": "Mozilla/5.0", "Referer": "https://www.zhihu.com/"}
EXT = {"image/png": "png", "image/jpeg": "jpg", "image/gif": "gif", "image/webp": "webp", "image/svg+xml": "svg"}
HOSTS = ["pic1.zhimg.com", "pic2.zhimg.com", "pic3.zhimg.com", "pic4.zhimg.com", "picx.zhimg.com"]


def get(url):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.read(), r.headers.get_content_type()


def existing(d, stem):
    g = glob.glob(os.path.join(d, stem + ".*"))
    return os.path.basename(g[0]) if g else None


def fetch(job):
    d, kind, key = job
    os.makedirs(d, exist_ok=True)
    stem = key if kind == "IMG" else "eq_" + re.sub(r"\W", "", str(abs(hash(key))))[:12]
    if kind == "EQ":
        stem = "eq_" + __import__("hashlib").md5(key.encode()).hexdigest()[:12]
    got = existing(d, stem)
    if got:
        return job, got
    urls = ([f"https://{h}/{key}.jpg" for h in HOSTS] if kind == "IMG"
            else ["https://www.zhihu.com/equation?tex=" + urllib.parse.quote(urllib.parse.unquote(key), safe="")])
    for u in urls:
        try:
            data, ct = get(u)
            ext = EXT.get(ct)
            if not ext or not data:
                continue
            if kind == "IMG" and ext == "svg":
                continue
            name = f"{stem}.{ext}"
            with open(os.path.join(d, name), "wb") as f:
                f.write(data)
            return job, name
        except Exception:
            continue
    return job, None


def main():
    jobs, items = set(), glob.glob(os.path.join(ROOT, "items", "*"))
    for it in items:
        for fn in ("index.md", "index.html"):
            p = os.path.join(it, fn)
            if os.path.exists(p):
                txt = open(p, encoding="utf-8").read()
                for k, v in re.findall(r"@@(IMG|EQ):([^@]+)@@", txt):
                    jobs.add((os.path.join(it, "images"), k, v))
    print(f"{len(jobs)} unique assets")
    names, fails = {}, []
    with ThreadPoolExecutor(8) as ex:
        for i, (job, name) in enumerate(ex.map(fetch, sorted(jobs)), 1):
            if name:
                names[job] = name
            else:
                fails.append(job)
            if i % 100 == 0:
                print(i, "done", flush=True)
    for it in items:
        d = os.path.join(it, "images")
        for fn in ("index.md", "index.html"):
            p = os.path.join(it, fn)
            if not os.path.exists(p):
                continue
            txt = open(p, encoding="utf-8").read()
            txt = re.sub(r"@@(IMG|EQ):([^@]+)@@",
                         lambda m: "images/" + names[(d, m.group(1), m.group(2))] if (d, m.group(1), m.group(2)) in names else m.group(0), txt)
            open(p, "w", encoding="utf-8").write(txt)
    json.dump([list(f) for f in fails], open(os.path.join(ROOT, "failed_assets.json"), "w"), ensure_ascii=False, indent=1)
    print(f"ok {len(names)}, failed {len(fails)} (see failed_assets.json; rerun to retry)")


if __name__ == "__main__":
    main()
