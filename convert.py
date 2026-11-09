#!/usr/bin/env python3
"""raw/*.json -> items/article_<id>/{index.md,index.html,meta.json,images/}; image URLs become @@IMG:token@@
placeholders that fetch_images.py resolves. Also writes zhihu_index.csv."""
import json, glob, os, re, html, csv, datetime
ROOT = os.path.dirname(os.path.abspath(__file__))
day = lambda t: datetime.datetime.fromtimestamp(t).strftime("%Y-%m-%d")

def inline(s):
    s = re.sub(r"<br\s*/?>", "  \n", s)
    s = re.sub(r"<(b|strong)>(.*?)</\1>", r"**\2**", s, flags=re.S)
    s = re.sub(r"<(i|em)>(.*?)</\1>", r"*\2*", s, flags=re.S)
    s = re.sub(r"<code>(.*?)</code>", r"`\1`", s, flags=re.S)
    s = re.sub(r'<a [^>]*href="([^"]*)"[^>]*>(.*?)</a>', lambda m: f"[{re.sub('<[^>]+>','',m.group(2))}]({html.unescape(m.group(1))})", s, flags=re.S)
    return html.unescape(re.sub(r"<[^>]+>", "", s)).strip()

def to_md(h):
    h = re.sub(r'<img [^>]*data-original-token="([^"]+)"[^>]*/?>', r"@@IMGTAG:\1@@", h)
    out = []
    for blk in re.findall(r"<(?:p|h[1-6]|figure|ul|ol|blockquote|pre|table)\b.*?</(?:p|h[1-6]|figure|ul|ol|blockquote|pre|table)>", h, flags=re.S):
        tag = re.match(r"<(\w+)", blk).group(1)
        if tag == "figure":
            m = re.search(r"@@IMGTAG:([^@]+)@@", blk)
            cap = re.search(r"<figcaption>(.*?)</figcaption>", blk, re.S)
            cap = inline(cap.group(1)) if cap else ""
            if m: out.append(f"![{cap}](@@IMG:{m.group(1)}@@)" + (f"\n\n*{cap}*" if cap else ""))
        elif tag[0] == "h":
            out.append("#" * int(tag[1]) + " " + inline(blk))
        elif tag in ("ul", "ol"):
            lis = re.findall(r"<li[^>]*>(.*?)</li>", blk, re.S)
            out.append("\n".join((f"{i}. " if tag == "ol" else "- ") + inline(l) for i, l in enumerate(lis, 1)))
        elif tag == "blockquote":
            out.append("> " + inline(blk))
        else:
            for part in re.split(r"(@@IMGTAG:[^@]+@@)", blk):
                m = re.match(r"@@IMGTAG:([^@]+)@@", part)
                t = f"![](@@IMG:{m.group(1)}@@)" if m else inline(part)
                if t: out.append(t)
    return "\n\n".join(out)

rows = []
for f in sorted(glob.glob(os.path.join(ROOT, "raw", "*.json"))):
    it = json.load(open(f, encoding="utf-8"))
    d = os.path.join(ROOT, "items", f"article_{it['id']}")
    os.makedirs(d, exist_ok=True)
    md = to_md(it["content"])
    hh = re.sub(r'<img [^>]*data-original-token="([^"]+)"[^>]*/?>', r'<img src="@@IMG:\1@@">', it["content"])
    hh = re.sub(r"<noscript>.*?</noscript>", "", hh, flags=re.S)
    open(os.path.join(d, "index.md"), "w", encoding="utf-8").write(
        f"# {it['title']}\n\n> 来源:{it['url']}  \n> 日期:{day(it['created'])} · 赞同:{it.get('voteup') or ''} · 文章\n\n{md}\n")
    open(os.path.join(d, "index.html"), "w", encoding="utf-8").write(
        f'<!doctype html><html><head><meta charset="utf-8"><title>{html.escape(it["title"])}</title>'
        f'<style>body{{max-width:760px;margin:2em auto;line-height:1.8}}img{{max-width:100%}}</style></head><body><h1>{html.escape(it["title"])}</h1>\n{hh}</body></html>')
    json.dump({"kind": "articles", "id": it["id"], "title": it["title"], "url": it["url"], "created": it["created"],
               "updated": it["updated"], "topics": it["topics"], "fullText": not it["truncated"]},
              open(os.path.join(d, "meta.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    rows.append(["文章", it["id"], it["title"], it["url"], day(it["created"]), day(it["updated"]), it.get("voteup"), it["topics"], len(re.sub(r"\s|!\[.*?\]\(.*?\)", "", md)), "是" if not it["truncated"] else "否"])
rows.sort(key=lambda r: r[4])
with open(os.path.join(ROOT, "zhihu_index.csv"), "w", encoding="utf-8-sig", newline="") as fh:
    w = csv.writer(fh); w.writerow(["类型", "ID", "标题", "链接", "创建日期", "更新日期", "赞数", "话题", "字数", "全文"]); w.writerows(rows)
print(len(rows), "items")
