#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
百度网盘「原分享 → 你的账号（绑任推邦）→ 生成推广分享链接」转存脚本
仅用于你自己的账号，凭证本地读取（secrets/.env），不外发。

流程：
  1. 读取第一步产出的 extracted_links.json
  2. 对每个百度盘链接，调用分享列表接口拿到 uk/shareid/file list
  3. （--go 时）转存到你的账号指定目录
  4. （--go 时）用你账号生成新的分享链接（自动带你的 UK → 任推邦计佣）

用法：
  python transfer_baidu.py                # 仅列出待转存内容（dry-run）
  python transfer_baidu.py --go           # 真正转存 + 生成推广链接
  python transfer_baidu.py --go --test-one # 只转第一条做冒烟测试
"""
import os
import sys
import re
import json
import time
import hashlib
import urllib.parse
import urllib.request
import urllib.error

BASE = os.path.dirname(__file__)
ENV_PATH = os.path.join(BASE, "secrets", ".env")
LINKS_PATH = os.path.join(BASE, "extracted_links.json")
RESULT_PATH = os.path.join(BASE, "transfer_results.json")
DEST_DIR = "/我的资源/网赚合集"  # 转存目标目录，可按需改

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36"


def load_env(path):
    env = {}
    if not os.path.exists(path):
        return env
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            env[k.strip()] = v.strip()
    return env


def build_opener(bduss, stoken):
    cookie = f"BDUSS={bduss}"
    if stoken:
        cookie += f"; STOKEN={stoken}"
    return cookie


def http_json(url, data=None, cookie=""):
    req = urllib.request.Request(url, headers={"Cookie": cookie, "User-Agent": UA,
                                               "Referer": "https://pan.baidu.com/"})
    if data is not None:
        req.add_header("Content-Type", "application/x-www-form-urlencoded")
        req.data = urllib.parse.urlencode(data).encode("utf-8")
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        try:
            return json.loads(e.read().decode("utf-8"))
        except Exception:
            return {"errno": -1, "errmsg": f"HTTP {e.code}"}
    except Exception as e:
        return {"errno": -1, "errmsg": str(e)}


def get_bdstoken(cookie):
    # gettoken 接口已失效(404)，改为从 pan.baidu.com 主页 HTML 提取登录态 bdstoken
    req = urllib.request.Request("https://pan.baidu.com/",
                                 headers={"Cookie": cookie, "User-Agent": UA})
    try:
        html = urllib.request.urlopen(req, timeout=15).read().decode("utf-8", "ignore")
    except Exception:
        return None
    m = re.search(r'bdstoken"?\s*[:=]\s*"([a-f0-9]{32})"', html)
    return m.group(1) if m else None


def parse_surl(url):
    # 形如 https://pan.baidu.com/s/1If65C8_QnbiInnVt9SZG3Q
    parts = url.split("/s/")
    return parts[1].split("?")[0].strip() if len(parts) > 1 else ""


def list_share(surl, pwd, cookie):
    """读取分享内容，返回 (uk, shareid, files)"""
    url = ("https://pan.baidu.com/share/wxlist?shorturl=%s&pwd=%s"
           % (urllib.parse.quote(surl), urllib.parse.quote(pwd or "")))
    d = http_json(url, cookie=cookie)
    if d.get("errno") != 0:
        return None, None, None, d
    info = d.get("data", d)
    uk = info.get("uk")
    shareid = info.get("shareid")
    files = info.get("list") or []
    return uk, shareid, files, d


def compute_sign(shareid, uk, fid_list_str, timestamp):
    # 百度 transfer 接口签名（社区通用算法）
    raw = f"{timestamp}gbk1{shareid}{uk}{fid_list_str}"
    return hashlib.md5(raw.encode("utf-8")).hexdigest()


def transfer(surl, pwd, uk, shareid, fid_list, cookie, bdstoken):
    timestamp = int(time.time())
    fid_list_str = json.dumps(fid_list)
    sign = compute_sign(shareid, uk, fid_list_str, timestamp)
    query = {
        "method": "transfer",
        "app_id": "250528",
        "bdstoken": bdstoken,
        "logid": "",
        "channel": "chunlei",
        "clienttype": "0",
        "web": "1",
        "timestamp": str(timestamp),
        "sign": sign,
    }
    url = "https://pan.baidu.com/rest/2.0/xpan/share?" + urllib.parse.urlencode(query)
    form = {
        "shareid": shareid,
        "from": uk,
        "sekey": pwd or "",
        "fid_list": fid_list_str,
        "path": DEST_DIR,
    }
    return http_json(url, data=form, cookie=cookie)


def create_share(fid_list, cookie, bdstoken):
    url = ("https://pan.baidu.com/rest/2.0/xpan/share?method=setshared&app_id=250528"
           "&bdstoken=%s&channel=chunlei&clienttype=0&web=1" % bdstoken)
    form = {
        "expiration": "0",
        "fid_list": json.dumps(fid_list),
        "schannel": "0",
        "channel_list": "[]",
        "period": "0",
    }
    return http_json(url, data=form, cookie=cookie)


def main():
    env = load_env(ENV_PATH)
    bduss = env.get("BAIDU_BDUSS")
    stoken = env.get("BAIDU_STOKEN")
    if not bduss:
        print("[!] secrets/.env 缺少 BAIDU_BDUSS，请先填入。")
        sys.exit(1)

    do_go = "--go" in sys.argv
    test_one = "--test-one" in sys.argv

    if not os.path.exists(LINKS_PATH):
        print("[!] 找不到 extracted_links.json，请先跑 extract_links.py。")
        sys.exit(1)

    links = json.load(open(LINKS_PATH, encoding="utf-8"))["links"]
    baidu_links = [l for l in links if l["platform"] == "baidu"]
    print(f"[i] 共 {len(baidu_links)} 条百度盘链接待处理。")

    cookie = build_opener(bduss, stoken)
    bdstoken = get_bdstoken(cookie)
    print(f"[i] bdstoken: {bdstoken[:8]}... (用于真实转存)\n")

    results = []
    for i, link in enumerate(baidu_links):
        surl = parse_surl(link["url"])
        pwd = link.get("code") or ""
        uk, shareid, files, raw = list_share(surl, pwd, cookie)
        if uk is None:
            print(f"[{i+1}] ✗ 读取失败: {link['title'][:30]} | errno={raw.get('errno')} {raw.get('errmsg')}")
            results.append({"title": link["title"], "url": link["url"], "ok": False,
                            "error": raw.get("errmsg"), "files": []})
            if test_one:
                break
            continue

        total = sum(int(f.get("size", 0)) for f in files)
        print(f"[{i+1}] ✓ {link['title'][:40]}")
        print(f"     源 uk={uk} shareid={shareid} 文件数={len(files)} 大小≈{total/1024/1024:.1f}MB")
        for f in files[:5]:
            print(f"       - {f.get('server_filename', f.get('filename',''))} ({int(f.get('size',0))/1024/1024:.1f}MB)")

        entry = {"title": link["title"], "url": link["url"], "code": pwd,
                 "uk": uk, "shareid": shareid, "files": files, "ok": True}

        if do_go:
            fid_list = [f["fs_id"] for f in files]
            r = transfer(surl, pwd, uk, shareid, fid_list, cookie, bdstoken)
            if r.get("errno") == 0:
                task = r.get("task_id") or r.get("info")
                print(f"     → 转存已提交 task_id={task}")
                # 生成你账号的推广分享链接
                new_share = create_share(fid_list, cookie, bdstoken)
                if new_share.get("errno") == 0:
                    link_url = new_share.get("shorturl") or new_share.get("link") or new_share.get("url")
                    entry["new_share_url"] = link_url
                    entry["new_share_id"] = new_share.get("shareid")
                    print(f"     → 推广分享链接: {link_url}")
                else:
                    entry["share_error"] = new_share.get("errmsg")
                    print(f"     → 生成分享链接失败: {new_share.get('errmsg')}")
            else:
                entry["ok"] = False
                entry["error"] = r.get("errmsg")
                print(f"     → 转存失败: errno={r.get('errno')} {r.get('errmsg')}")

        results.append(entry)
        if test_one:
            break

    if do_go:
        json.dump({"results": results}, open(RESULT_PATH, "w", encoding="utf-8"),
                  ensure_ascii=False, indent=2)
        print(f"\n[✓] 已写入 {RESULT_PATH}")

    print("\n[i] 提示：刚才为 dry-run（仅列待转存）。加 --go 才会真正搬运并生成推广链接。")


if __name__ == "__main__":
    main()
