#!/usr/bin/env python3
"""Publish a Kodama blog post: markdown draft → styled HTML page + index + RSS.

Usage: python3 bin/publish-post.py <draft.md> [--live]
  --live   footer links to the App Store (post-launch); default = "launching soon"

Draft format: markdown with an H1 title; optional header comments:
  <!-- slug: why-one-word · SEO title: ... -->  (slug required)
Writes blog/<slug>/index.html, prepends the card to blog/index.html, prepends the
RSS item to blog/feed.xml. Idempotent per slug (re-publish overwrites the page and
skips duplicate index/feed entries). Deploy separately with wrangler.
"""
import re, sys, html, pathlib, datetime

ROOT = pathlib.Path(__file__).resolve().parent.parent
LIVE = '--live' in sys.argv
SRC = pathlib.Path([a for a in sys.argv[1:] if not a.startswith('--')][0])
md = SRC.read_text()

slug_m = re.search(r'slug:\s*([a-z0-9-]+)', md)
if not slug_m:
    sys.exit('draft has no slug marker')
slug = slug_m.group(1)
seo_m = re.search(r'SEO title:\s*([^\n>]+?)\s*-->', md)
title_m = re.search(r'^# (.+)$', md, re.M)
title = title_m.group(1).strip()
seo = (seo_m.group(1).strip() if seo_m else title)

body_md = re.sub(r'<!--.*?-->', '', md, flags=re.S)
body_md = re.sub(r'^# .+$', '', body_md, count=1, flags=re.M).strip()

# tiny md → html (paragraphs, em/strong, links); enough for essay prose
def mdline(s: str) -> str:
    s = html.escape(s)
    s = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', s)
    s = re.sub(r'\*(.+?)\*', r'<em>\1</em>', s)
    s = re.sub(r'\[(.+?)\]\((.+?)\)', r'<a href="\2">\1</a>', s)
    return s

paras = [p.strip() for p in re.split(r'\n\s*\n', body_md) if p.strip()]
FOOT_RE = re.compile(r'^\*Kodama is .*\*$', re.S)
foot_live = ('<em>Kodama is a one-word journal for iPhone — US$7.99 once, no subscription, '
             'no account, no ads. Your words never leave your phone. '
             '<a href="https://apps.apple.com/app/id6799396764">Get it on the App Store.</a></em>')
foot_soon = ('<em>Kodama is a one-word journal for iPhone — arriving on the App Store soon. '
             'US$7.99 once, no subscription, no account, no ads. '
             'Your words never leave your phone.</em>')
out_paras = []
for p in paras:
    if FOOT_RE.match(p):
        out_paras.append('<p class="foot">' + (foot_live if LIVE else foot_soon) + '</p>')
    else:
        out_paras.append('<p>' + mdline(' '.join(p.splitlines())) + '</p>')
body_html = '\n'.join(out_paras)

date = datetime.date.today()
datestr = date.strftime('%-d %B %Y')
rfc822 = date.strftime('%a, %d %b %Y 08:00:00 +0800')

page = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{html.escape(seo)} — Kodama</title>
<meta name="description" content="{html.escape(paras[0][:150])}">
<link rel="canonical" href="https://kodamajournal.app/blog/{slug}/">
<link rel="alternate" type="application/rss+xml" title="Kodama Blog" href="/blog/feed.xml">
<style>
  :root {{ --ink:#f6f1e4; --bg1:#4a5aa8; --bg2:#8a7fb0; --bg3:#e8a887; --card:rgba(20,16,38,.35); --pink:#f58fb8; }}
  * {{ margin:0; padding:0; box-sizing:border-box; }}
  body {{ min-height:100vh; font-family: Georgia, 'Times New Roman', serif; color:var(--ink);
         background: linear-gradient(180deg, var(--bg1), var(--bg2) 45%, var(--bg3)); background-attachment: fixed; }}
  main {{ max-width:38rem; margin:0 auto; padding:12vh 1.5rem 5rem; }}
  .back {{ font-family:-apple-system, system-ui, sans-serif; font-size:.75rem; opacity:.75; text-decoration:none; color:var(--ink); }}
  h1 {{ font-style:italic; font-weight:500; font-size:2rem; margin:.9rem 0 .3rem; }}
  .date {{ font-family:-apple-system, system-ui, sans-serif; font-size:.75rem; opacity:.7; margin-bottom:2.2rem; }}
  article p {{ font-size:1.02rem; line-height:1.75; margin-bottom:1.25rem; }}
  article p.foot {{ border-top:1px solid rgba(246,241,228,.25); padding-top:1.2rem; margin-top:2rem;
    font-size:.9rem; opacity:.9; }}
  a {{ color:var(--pink); }}
  footer {{ font-family:-apple-system, system-ui, sans-serif; font-size:.75rem; opacity:.7; margin-top:3rem; }}
</style>
</head>
<body>
<main>
  <a class="back" href="/blog/">&larr; Notes</a>
  <h1>{html.escape(title)}</h1>
  <div class="date">{datestr}</div>
  <article>
{body_html}
  </article>
  <footer>Kodama · a feelsrealco product · Singapore</footer>
</main>
</body>
</html>
"""
outdir = ROOT / 'blog' / slug
outdir.mkdir(parents=True, exist_ok=True)
(outdir / 'index.html').write_text(page)

# index card (skip if present)
idx = ROOT / 'blog' / 'index.html'
it = idx.read_text()
card = (f'  <div class="card">\n    <h2><a href="/blog/{slug}/">{html.escape(title)}</a></h2>\n'
        f'    <p>{html.escape(paras[0][:180])}…</p>\n  </div>\n')
if f'/blog/{slug}/' not in it:
    it = it.replace('  <!-- Essays land here as they clear the quality gates and HC approves publish. -->',
                    '  <!-- Essays land here as they clear the quality gates and HC approves publish. -->\n' + card)
    it = it.replace('  <p class="empty">Nothing published yet — check back soon.</p>\n', '')
    idx.write_text(it)

# rss item (skip if present)
feed = ROOT / 'blog' / 'feed.xml'
ft = feed.read_text()
if f'/blog/{slug}/' not in ft:
    item = (f'  <item>\n    <title>{html.escape(title)}</title>\n'
            f'    <link>https://kodamajournal.app/blog/{slug}/</link>\n'
            f'    <guid>https://kodamajournal.app/blog/{slug}/</guid>\n'
            f'    <pubDate>{rfc822}</pubDate>\n'
            f'    <description>{html.escape(paras[0][:250])}</description>\n  </item>\n')
    ft = ft.replace('  <!-- <item> entries land here as essays publish. -->',
                    '  <!-- <item> entries land here as essays publish. -->\n' + item)
    feed.write_text(ft)

print(f'published blog/{slug}/ ({"live" if LIVE else "launching-soon"} footer)')
