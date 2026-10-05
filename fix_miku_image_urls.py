#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把历史日报里失效的装饰图链（img.heliar.top）批量换成 jsDelivr 直链。

背景：旧版模板把 7 个装饰图硬编码在第三方图床 img.heliar.top 上，该图床已彻底失效
（DNS 在、源站没了）。插件新版已改用镜像直链，但**存量 HTML 不会自己变**。
映射表取自工具仓库 shiitin/astrbot_plugin_qq_group_daily_analysis_miku_template_upgrade-fix
（原名 miku-template-image-fix）的 replace_miku_image_url.sh。

用法：
  python3 fix_miku_image_urls.py 日报目录 [--backup-dir 目录] [--dry-run]
  python3 fix_miku_image_urls.py 日报目录 --check     # 只统计还剩多少处，不写盘

映射（旧文件名 → 插件 assets/HatsuneMiku/ 下的规范名）：
  1776606860022_retouch_2026032802083201.png  → retouch_2026032802083201.png   峰值区装饰图
  1778303907562_retouch_2026032810150449.png  → retouch_2026032810150449.png   质量区小人
  1778265932033_retouch_2026032810150449.jpeg → retouch_2026032810150449.png   话题图1（同一张图）
  1778265932542_retouch_2026032810143720.jpeg → retouch_2026032810143720.png   话题图2
  1778265934386_retouch_2026032810151717.jpeg → retouch_2026032810151717.png   话题图3
  1778265931177_retouch_2026032810153327__1_.jpeg → retouch_2026032810153327.png  话题图4
  1778265933286_retouch_2026032810145078.jpeg → retouch_2026032810145078.png   话题图5（c 后缀）
"""

from __future__ import annotations

import argparse
import os
import re
import shutil
import sys

OLD = "https://img.heliar.top/file/"
NEW = ("https://fastly.jsdelivr.net/gh/SXP-Simon/astrbot_plugin_qq_group_daily_analysis"
       "@main/assets/HatsuneMiku/")

MAP = {
    "1776606860022_retouch_2026032802083201.png": "retouch_2026032802083201.png",
    "1778303907562_retouch_2026032810150449.png": "retouch_2026032810150449.png",
    "1778265932033_retouch_2026032810150449.jpeg": "retouch_2026032810150449.png",
    "1778265932542_retouch_2026032810143720.jpeg": "retouch_2026032810143720.png",
    "1778265934386_retouch_2026032810151717.jpeg": "retouch_2026032810151717.png",
    "1778265931177_retouch_2026032810153327__1_.jpeg": "retouch_2026032810153327.png",
    "1778265933286_retouch_2026032810145078.jpeg": "retouch_2026032810145078.png",
}


def fix_text(text: str) -> tuple:
    """返回 (新文本, 替换处数, 未知旧链列表)。"""
    n = 0
    for old, new in MAP.items():
        n += text.count(OLD + old)
        text = text.replace(OLD + old, NEW + new)
    left = re.findall(r"https://img\.heliar\.top/file/[^\"')\s]+", text)
    return text, n, sorted(set(left))


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="历史日报失效装饰图链 img.heliar.top → jsDelivr 批量替换")
    ap.add_argument("path", help="日报目录")
    ap.add_argument("--backup-dir", help="备份目录（按绝对路径镜像；不给就同目录 .bak）")
    ap.add_argument("--dry-run", action="store_true", help="只列要改的文件")
    ap.add_argument("--check", action="store_true", help="只统计残留处数")
    args = ap.parse_args(argv)

    files = []
    for root, _d, fs in os.walk(args.path):
        files += [os.path.join(root, f) for f in sorted(fs) if f.endswith(".html")]

    total, hit, unknown, checked = 0, 0, set(), 0
    for fp in files:
        s = open(fp, encoding="utf-8").read()
        if OLD not in s:
            continue
        checked += 1
        if args.check or args.dry_run:
            _, n, left = fix_text(s)
            total += n
            unknown |= set(left)
            print(f"[待修] {fp}  {n} 处" + (f"（{len(left)} 处映射表里没有）" if left else ""))
            continue
        new, n, left = fix_text(s)
        bak = (os.path.join(args.backup_dir, os.path.abspath(fp).lstrip("/")) + ".bak"
               if args.backup_dir else fp + ".bak")
        if not os.path.exists(bak):
            os.makedirs(os.path.dirname(bak) or ".", exist_ok=True)
            shutil.copy2(fp, bak)
        tmp = fp + ".tmp-imgfix"
        with open(tmp, "w", encoding="utf-8") as fh:
            fh.write(new)
        os.replace(tmp, fp)
        if os.path.exists(bak):
            try:
                os.chmod(fp, os.stat(bak).st_mode & 0o7777)
            except OSError:
                pass
        total += n
        hit += 1
        unknown |= set(left)
        print(f"[已修] {fp}  {n} 处" + (f"（剩 {len(left)} 处未知链接）" if left else ""))

    mode = "check" if args.check else ("dry-run" if args.dry_run else "已修")
    print(f"\n{'统计' if args.check else mode}：命中文件 {checked} 个，替换 {total} 处"
          + (f"，已写盘 {hit} 个" if hit else ""))
    if unknown:
        print("映射表里没有的旧链（需人工确认）:")
        for u in sorted(unknown):
            print("   ", u)
    return 0


if __name__ == "__main__":
    sys.exit(main())
