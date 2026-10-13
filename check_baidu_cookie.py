#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
百度网盘 cookie 有效性自检
读取 secrets/.env 里的 BAIDU_BDUSS / BAIDU_STOKEN，调用网盘 uinfo 接口验证登录态。
用法: python check_baidu_cookie.py
（仅用于你自己的账号，凭证本地读取，不外发）
"""
import os
import sys
import json
import urllib.request
import urllib.error

ENV_PATH = os.path.join(os.path.dirname(__file__), "secrets", ".env")


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


def main():
    env = load_env(ENV_PATH)
    bduss = env.get("BAIDU_BDUSS")
    stoken = env.get("BAIDU_STOKEN")
    if not bduss:
        print("[!] secrets/.env 里没有 BAIDU_BDUSS，请先按指引填入后再运行。")
        sys.exit(1)

    cookie = f"BDUSS={bduss}"
    if stoken:
        cookie += f"; STOKEN={stoken}"

    url = "https://pan.baidu.com/rest/2.0/xpan/nas?method=uinfo"
    req = urllib.request.Request(url, headers={
        "Cookie": cookie,
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    })
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        print(f"[!] HTTP 错误: {e.code}")
        sys.exit(1)
    except Exception as e:
        print(f"[!] 请求失败: {e}")
        sys.exit(1)

    # uinfo 接口把字段放在顶层（errno/uk/baidu_name 等），
    # 与含 data 包裹的接口不同，这里以 errno==0 且拿到 uk 作为有效判定。
    if data.get("errno") == 0 and data.get("uk"):
        print("[✓] Cookie 有效！登录态正常。")
        print(f"    百度账号 uk : {data.get('uk')}")
        print(f"    网盘名     : {data.get('netdisk_name') or data.get('baidu_name') or '(接口未返回)'}")
        print(f"    VIP 类型   : {data.get('vip_type', 0)}")
        print("    → 可以开始写转存脚本了。")
    else:
        print("[✗] Cookie 无效或已过期。")
        print(f"    接口返回: {json.dumps(data, ensure_ascii=False)}")
        print("    请重新按指引获取 BDUSS / STOKEN 并覆盖 secrets/.env。")


if __name__ == "__main__":
    main()
