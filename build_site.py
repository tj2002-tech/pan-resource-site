#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
站点生成器：读取 transfer_results.json → 输出静态站点到 site/
纯静态预渲染（SEO 友好），可直接部署 Cloudflare Pages。
用法: python build_site.py
"""
import os
import json
import html

BASE = os.path.dirname(__file__)
DATA = os.path.join(BASE, "transfer_results.json")
OUT = os.path.join(BASE, "site")

# ===== 站点配置（按需修改）=====
SITE_TITLE = "网赚资源库 · 精选教程与项目合集"
SITE_DESC = "精选网赚实战教程、短视频玩法、信息差副业项目网盘资源合集，一键转存即可获取。"
SITE_CONTACT = "【替换为你的微信号】"
ADSTERRA_BANNER = "<!-- Adsterra 横幅广告位 728x90：在此粘贴 Adsterra 提供的 <script> 代码 -->"
ADSTERRA_NATIVE = "<!-- Adsterra 原生/插页广告位：在此粘贴 Adsterra 提供的 <script> 代码 -->"


def esc(s):
    return html.escape(str(s))


def build():
    data = json.load(open(DATA, encoding="utf-8"))
    items = data["results"]
    contact = data.get("site_contact") or SITE_CONTACT

    # 按分类聚合
    cats = {}
    for it in items:
        cats.setdefault(it["category"], []).append(it)

    # 分类导航
    nav_links = "".join(
        f'<a href="#cat-{esc(c)}" class="nav-link">{esc(c)}</a>' for c in cats
    )

    # 资源卡片
    sections = []
    total = 0
    for cat, its in cats.items():
        cards = []
        for it in its:
            total += 1
            cards.append(f"""
      <article class="card">
        <div class="card-head">
          <h3>{esc(it['title'])}</h3>
          <span class="tag">{esc(it['category'])}</span>
        </div>
        <div class="code">提取码：<b>{esc(it['code'])}</b></div>
        <a class="btn" href="{esc(it['url'])}" target="_blank" rel="noopener">前往网盘转存 / 下载</a>
      </article>""")
        sections.append(f"""
    <section id="cat-{esc(cat)}" class="cat">
      <h2>{esc(cat)} <small>（{len(its)} 个资源）</small></h2>
      <div class="grid">{''.join(cards)}</div>
    </section>""")

    year = 2026
    page = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(SITE_TITLE)}</title>
<meta name="description" content="{esc(SITE_DESC)}">
<meta property="og:title" content="{esc(SITE_TITLE)}">
<meta property="og:description" content="{esc(SITE_DESC)}">
<link rel="stylesheet" href="assets/style.css">
</head>
<body>
<header class="top">
  <div class="wrap">
    <h1>{esc(SITE_TITLE)}</h1>
    <nav class="nav">{nav_links}
      <a href="#contact" class="nav-link">联系站长</a>
    </nav>
  </div>
</header>

<div class="ad-top wrap">{ADSTERRA_BANNER}</div>

<main class="wrap">
  <section class="intro">
    <p>共收录 <b>{total}</b> 个精选网赚实战资源，覆盖无人直播、AI 短视频、信息差副业等方向。
    点击资源卡片即可前往网盘 <b>转存 / 下载</b>，转存后内容存到你自己的网盘，永久可用。</p>
  </section>

  {''.join(sections)}

  <div class="ad-mid wrap">{ADSTERRA_NATIVE}</div>

  <section id="contact" class="contact">
    <h2>联系站长</h2>
    <p>获取更多资源或一对一指导，请加站长微信：<b>{esc(contact)}</b></p>
    <p class="muted">（资源持续更新，加微信第一时间获取新项目）</p>
  </section>
</main>

<footer class="foot">
  <div class="wrap">
    <p>免责声明：本站点仅作资源索引与信息整理，所有资源均来自第三方公开分享，版权归原作者所有。
    使用者须遵守相关平台规则与当地法律法规，因使用资源产生的任何后果由使用者自行承担。</p>
    <p class="muted">© {year} {esc(SITE_TITLE)}</p>
  </div>
</footer>
</body>
</html>"""

    os.makedirs(os.path.join(OUT, "assets"), exist_ok=True)
    with open(os.path.join(OUT, "index.html"), "w", encoding="utf-8") as f:
        f.write(page)

    # 样式
    css = """
:root{--bg:#0f1115;--card:#171a21;--fg:#e6e8eb;--muted:#9aa0a6;--accent:#3b82f6;--tag:#2a3340}
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:-apple-system,"Segoe UI",Roboto,"PingFang SC","Microsoft YaHei",sans-serif;background:var(--bg);color:var(--fg);line-height:1.6}
.wrap{max-width:960px;margin:0 auto;padding:0 16px}
.top{background:#11141a;border-bottom:1px solid #222;padding:18px 0}
.top h1{font-size:20px}
.nav{margin-top:10px;display:flex;flex-wrap:wrap;gap:10px}
.nav-link{color:var(--muted);text-decoration:none;font-size:14px;padding:4px 8px;border-radius:6px}
.nav-link:hover{color:var(--fg);background:var(--tag)}
.ad-top{margin:16px auto}
.intro{background:var(--card);border:1px solid #222;border-radius:12px;padding:18px;margin:20px 0}
.cat{margin:28px 0}
.cat h2{font-size:18px;margin-bottom:14px;border-left:4px solid var(--accent);padding-left:10px}
.cat small{color:var(--muted);font-weight:400}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(260px,1fr));gap:14px}
.card{background:var(--card);border:1px solid #222;border-radius:12px;padding:16px;display:flex;flex-direction:column;gap:10px}
.card-head{display:flex;justify-content:space-between;align-items:flex-start;gap:8px}
.card h3{font-size:15px;line-height:1.4}
.tag{background:var(--tag);color:var(--muted);font-size:12px;padding:2px 8px;border-radius:20px;white-space:nowrap}
.code{font-size:14px;color:var(--muted)}
.code b{color:var(--fg);letter-spacing:1px}
.btn{margin-top:auto;display:inline-block;text-align:center;background:var(--accent);color:#fff;text-decoration:none;padding:9px 12px;border-radius:8px;font-size:14px}
.btn:hover{opacity:.9}
.contact{background:var(--card);border:1px solid #222;border-radius:12px;padding:20px;margin:30px 0}
.contact h2{font-size:18px;margin-bottom:10px}
.muted{color:var(--muted);font-size:13px}
.foot{border-top:1px solid #222;margin-top:30px;padding:20px 0;font-size:13px}
.foot p{max-width:960px}
"""
    with open(os.path.join(OUT, "assets", "style.css"), "w", encoding="utf-8") as f:
        f.write(css)

    # robots + sitemap
    with open(os.path.join(OUT, "robots.txt"), "w", encoding="utf-8") as f:
        f.write("User-agent: *\nAllow: /\n")
    with open(os.path.join(OUT, "sitemap.xml"), "w", encoding="utf-8") as f:
        f.write('<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
                '  <url><loc>/</loc><changefreq>daily</changefreq></url>\n</urlset>\n')

    print(f"[✓] 站点已生成到 {OUT}")
    print(f"    资源总数: {total} | 分类数: {len(cats)}")
    print(f"    本地预览: 用浏览器打开 {os.path.join(OUT, 'index.html')}")


if __name__ == "__main__":
    build()
