#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
QQ 群聊网盘链接提取器 v1.2
--------------------------------
从导出的 QQ 群聊文本中提取：
  - 百度网盘 分享链接 (pan.baidu.com/s/...，兼容带/不带 http(s):// 前缀)
  - 夸克网盘 分享链接 (pan.quark.cn/s/...)
  - 提取码：优先取 URL 里的 ?pwd=xxx（百度新版格式），再回退到文字“提取码/密码/访问码”
  - 资源标题：自动取链接上方最近的一行描述文字（用于第三步建目录）

用法（三选一）:
  python extract_links.py                      # 自动：优先 chat_export.txt，否则扫描 inbox/*.txt
  python extract_links.py <文件.txt>            # 指定单个文件
  python extract_links.py inbox/群A.txt         # 指定 inbox 内某文件

多群聊建议：分别存为 inbox/群A.txt、inbox/群B.txt，一次全部提取并跨文件去重。
输出: extracted_links.json（供第二步转存 / 第三步建站）
"""

import re
import json
import sys
import os
from datetime import datetime

# 百度网盘分享链接（兼容带/不带 http(s):// 前缀；可选 ?pwd= 提取码）
BAIDU_RE = re.compile(
    r'(?:https?://)?(?:www\.)?pan\.baidu\.com/s/([a-zA-Z0-9_-]+)(?:\?pwd=([a-zA-Z0-9_-]+))?'
)
# 夸克网盘分享链接（同上）
QUARK_RE = re.compile(
    r'(?:https?://)?(?:www\.)?pan\.quark\.cn/s/([a-zA-Z0-9_-]+)(?:\?pwd=([a-zA-Z0-9_-]+))?'
)
# 文字提取码 / 密码（4~8 位字母数字，常见前缀：提取码 / 密码 / 访问码）
CODE_RE = re.compile(r'(?:提取码|密码|访问码|提取)[:：\s]*([a-zA-Z0-9]{4,8})')


def is_link_line(line):
    return bool(BAIDU_RE.search(line) or QUARK_RE.search(line))


def find_code(lines, idx):
    """在当前行及之后 2 行内寻找文字提取码 / 密码（仅当 URL 没有 ?pwd= 时作回退）。"""
    for ln in lines[idx:idx + 3]:
        m = CODE_RE.search(ln)
        if m:
            return m.group(1)
    return None


def find_title(lines, idx):
    """向上找最近的一行非链接、非“链接:”、非“[图片]”的描述文字作为标题。"""
    for j in range(idx - 1, -1, -1):
        ln = lines[j].strip()
        if not ln:
            continue
        if is_link_line(ln):
            continue
        if ln == "链接:" or ln.startswith("[图片]"):
            continue
        return ln
    return None


def extract(text):
    results = []
    lines = text.splitlines()
    for i, line in enumerate(lines):
        for m in BAIDU_RE.finditer(line):
            sid = m.group(1)
            pwd = m.group(2)
            url = f"https://pan.baidu.com/s/{sid}" + (f"?pwd={pwd}" if pwd else "")
            results.append({
                "platform": "baidu",
                "url": url,
                "share_id": sid,
                "code": pwd or find_code(lines, i),
                "title": find_title(lines, i),
                "context": line.strip(),
                "line": i + 1,
            })
        for m in QUARK_RE.finditer(line):
            sid = m.group(1)
            pwd = m.group(2)
            url = f"https://pan.quark.cn/s/{sid}" + (f"?pwd={pwd}" if pwd else "")
            results.append({
                "platform": "quark",
                "url": url,
                "share_id": sid,
                "code": pwd or find_code(lines, i),
                "title": find_title(lines, i),
                "context": line.strip(),
                "line": i + 1,
            })
    return results


def main():
    inbox = "inbox"
    arg = sys.argv[1] if len(sys.argv) > 1 else None

    if arg:
        if not os.path.exists(arg):
            print(f"[!] 找不到文件: {arg}")
            sys.exit(1)
        files = [arg]
    elif os.path.exists("chat_export.txt"):
        files = ["chat_export.txt"]
    elif os.path.isdir(inbox):
        files = sorted(
            os.path.join(inbox, f)
            for f in os.listdir(inbox)
            if f.lower().endswith(".txt")
        )
        if not files:
            print(f"[!] inbox/ 目录下没有 .txt 文件")
            sys.exit(1)
    else:
        print("[!] 找不到输入：请把聊天文本保存为 chat_export.txt，或放进 inbox/ 目录，或传入文件路径")
        sys.exit(1)

    all_links = []
    processed = []
    for fp in files:
        with open(fp, encoding="utf-8", errors="ignore") as f:
            text = f.read()
        links = extract(text)
        all_links.extend(links)
        processed.append((os.path.basename(fp), len(links)))

    # 跨文件去重（同一链接 + 同一提取码视为一条）
    seen = set()
    out = []
    for r in all_links:
        key = r["url"] + "|" + str(r["code"])
        if key not in seen:
            seen.add(key)
            out.append(r)

    out_path = "extracted_links.json"
    payload = {
        "extracted_at": datetime.now().isoformat(timespec="seconds"),
        "source_files": [p for p, _ in processed],
        "count": len(out),
        "links": out,
    }
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

    # 控制台摘要
    by_platform = {}
    for r in out:
        by_platform[r["platform"]] = by_platform.get(r["platform"], 0) + 1
    print(f"[✓] 已处理 {len(processed)} 个文件，提取 {len(out)} 条有效链接（已跨文件去重）")
    for p, n in processed:
        print(f"    - {p}: {n} 条")
    print(f"    平台分布: {by_platform}")
    no_code = [r for r in out if not r["code"]]
    if no_code:
        print(f"    [!] 其中 {len(no_code)} 条未识别到提取码，需人工补录：")
        for r in no_code:
            print(f"        · {r['title']}  ->  {r['url']}")
    print(f"    结果已写入: {out_path}")


if __name__ == "__main__":
    main()
