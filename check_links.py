#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
死链检测：逐条探测 transfer_results.json 里的网盘分享链接，
把结果回写到每条的 "status" 字段（ok / dead / unknown），build_site.py 据此渲染徽标。

原理（实测验证，2026-10-13）：
- 百度分享页无 cookie 直接 GET 不触发 9019 风控；
- 有效分享  → HTTP 200，页面含 shareid/file_list；
- 不存在的链接 → HTTP 404；
- 被取消/过期 → 页面含"已经被取消/分享已过期"等标记。

用法: python check_links.py            # 检测全部并回写
      python check_links.py --dry     # 只看结果不回写
"""
import os
import re
import json
import sys
import time
import urllib.request

BASE = os.path.dirname(__file__)
DATA = os.path.join(BASE, "transfer_results.json")

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
DEAD_MARKS = ["已经被取消", "分享已过期", "链接不存在", "文件已删除", "页面不存在"]

# 检测间隔（秒）：太密容易触发百度风控，保持 >=1.5s
DELAY = 2.0


def parse_url(url):
    """从分享链接里取短码和提取码。"""
    m = re.search(r"/s/([a-zA-Z0-9_-]+)", url)
    surl = m.group(1) if m else None
    p = re.search(r"[?&]pwd=([a-zA-Z0-9]+)", url)
    pwd = p.group(1) if p else ""
    return surl, pwd


def probe(surl, pwd):
    """探测单条分享。返回 'ok' / 'dead' / 'unknown'。"""
    url = f"https://pan.baidu.com/s/{surl}"
    if pwd:
        url += f"?pwd={pwd}"
    req = urllib.request.Request(url, headers={
        "User-Agent": UA,
        "Accept-Language": "zh-CN,zh;q=0.9",
    })
    try:
        r = urllib.request.urlopen(req, timeout=20)
        body = r.read().decode("utf-8", "ignore")
    except urllib.error.HTTPError as e:
        if e.code in (404, 410):
            return "dead"
        return "unknown"
    except Exception:
        return "unknown"

    if any(m in body for m in DEAD_MARKS):
        return "dead"
    # 有效页特征：含分享数据结构
    if ("shareid" in body) or ("file_list" in body) or ("dentryList" in body):
        return "ok"
    # 有提取码输入页且无死链标记 → 视为有效（需提码但链接在）
    if "请输入提取码" in body:
        return "ok"
    return "unknown"


def main():
    dry = "--dry" in sys.argv
    data = json.load(open(DATA, encoding="utf-8"))
    items = data["results"]
    stat = {"ok": 0, "dead": 0, "unknown": 0}

    for i, it in enumerate(items, 1):
        surl, pwd = parse_url(it["url"])
        if not surl:
            it["status"] = "unknown"
            print(f"[{i}/{len(items)}] ⚠ 无法解析链接: {it['title']}")
            continue
        s = probe(surl, pwd)
        stat[s] += 1
        icon = {"ok": "✅", "dead": "❌", "unknown": "⚠"}[s]
        print(f"[{i}/{len(items)}] {icon} {s:7} | {it['title'][:30]}")
        it["status"] = s
        if i < len(items):
            time.sleep(DELAY)

    print(f"\n合计: ✅有效 {stat['ok']} | ❌失效 {stat['dead']} | ⚠未知 {stat['unknown']}")

    if dry:
        print("(dry-run，未回写 JSON)")
        return

    json.dump(data, open(DATA, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    print(f"[✓] 结果已回写 {DATA}，重新运行 build_site.py 即可更新站点徽标。")


if __name__ == "__main__":
    main()
