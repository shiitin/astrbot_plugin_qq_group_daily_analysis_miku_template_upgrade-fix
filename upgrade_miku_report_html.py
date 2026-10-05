#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""一键把旧的 HatsuneMiku 网页报告升级到新版模板格式。

背景：模板（src/infrastructure/reporting/templates/HatsuneMiku/html_template.html）更新后，
只有新生成的报告才有新版网页交互层；已经落盘的旧 .html 不会自己变化。
本脚本按新版模板「受影响的 HTML 部分」就地升级旧报告：

  1. 图标内联：<i data-lucide="x"> → 内联 <svg>（不再依赖 lucide CDN，断网也不丢图标）
  2. 删除 lucide CDN <script> 与 lucide.createIcons() 运行时调用
  3. 在 </head> 前注入 <style id="miku-web-ui"> 交互层（导航/进度条/回顶/折叠/宽屏栅格）
  4. 在 </body> 前注入 <script id="miku-web-ui-js"> 与 <script id="miku-fit-oneline">
  5. 头部补 <meta name="google" content="notranslate">，字体链补 Noto Sans JP
  6. 基础 CSS 对齐新版：body/container 顶部留白、hover 规则收进 @media (hover: hover)

交互层不是从零写死的：脚本从「新版模板」或「一份已升级的新版报告」里原样提取，
所以以后模板再改，重新跑一次即可，不用改脚本。

用法：
  python3 upgrade_miku_report_html.py 报告目录/            # 就地升级（自动找层来源）
  python3 upgrade_miku_report_html.py 报告目录/ --dry-run  # 只列清单，不写文件
  python3 upgrade_miku_report_html.py a.html b.html --lang zh-Hant
  python3 upgrade_miku_report_html.py 报告目录/ --template .../HatsuneMiku/html_template.html

无第三方依赖，Python 3.8+。
"""

from __future__ import annotations

import argparse
import ast
import datetime
import json
import os
import re
import shutil
import sys

# ---------------------------------------------------------------- 常量与锚点

CSS_BEGIN = "<!-- ================= 网页版交互层（仅 html_template 使用；长图模板不含此段） ================= -->"
CSS_END = "<!-- ================= 网页版交互层 END ================= -->"
JS_CALL_COMMENT = "<!-- lucide.createIcons() 已移除"
FIT_OPEN = '<script id="miku-fit-oneline">'
CSS_OPEN = '<style id="miku-web-ui">'
JS_ID = '<script id="miku-web-ui-js">'
CDN_COMMENT = "    <!-- 图标已内联为 SVG（11 个），不再依赖 lucide CDN -->"

RE_I = re.compile(r'<i\b([^>]*?)\bdata-lucide="([^"]+)"([^>]*?)>\s*</i>', re.S)
RE_CDN = re.compile(r'[ \t]*<script src="[^"]*lucide[^"]*"[^>]*></script>[ \t]*\n')
RE_CALL = re.compile(r'[ \t]*<script>[ \t]*\r?\n[ \t]*lucide\.createIcons\(\);[ \t]*\r?\n[ \t]*</script>[ \t]*\n')
RE_ICON_SVG = re.compile(r'<svg\b[^>]*\bdata-lucide="([^"]+)"[^>]*>(.*?)</svg>', re.S)
RE_TOJSON = re.compile(r'\{\{\s*T\.([A-Za-z_]\w*)\s*\[\s*REPORT_LANG\s*\]\s*\|\s*tojson\s*\}\}')
RE_IF_TC = re.compile(r'\{%\s*if _TC_FIRST\s*%\}(.*?)\{%\s*else\s*%\}(.*?)\{%\s*endif\s*%\}', re.S)

LAYERS = ("miku-web-ui", "miku-web-ui-js", "miku-fit-oneline")


class Layer:
    """从新版模板 / 新版报告里提取出来的静态层。"""

    def __init__(self, css: str, tail: str, icons: dict, source: str, lang: str):
        self.css = css            # 交互层 <style> + 前后标记注释
        self.tail = tail          # createIcons 注释 + 两个 <script>
        self.icons = icons        # {图标名: 内联路径}
        self.source = source
        self.lang = lang


# ---------------------------------------------------------------- 提取层

def _tojson(value: str) -> str:
    """和 Jinja 的 | tojson 逐字节一致（非 ASCII 转义 + HTML 安全字符转义）。"""
    return (json.dumps(value, ensure_ascii=True)
            .replace("<", "\\u003c").replace(">", "\\u003e")
            .replace("&", "\\u0026").replace("'", "\\u0027"))


def _slice(text: str, start_mark: str, end_mark: str, where: str) -> str:
    i = text.find(start_mark)
    if i < 0:
        raise SystemExit(f"[错误] {where} 里找不到起始标记：{start_mark[:60]}")
    j = text.find(end_mark, i)
    if j < 0:
        raise SystemExit(f"[错误] {where} 里找不到结束标记：{end_mark[:60]}")
    return text[i:j + len(end_mark)]


def _tail_block(text: str, where: str) -> str:
    """尾部层：从 createIcons 注释起，一直取到 miku-fit-oneline 脚本的闭合标签。

    注意不能只取到「第一个 </script>」——那是 miku-web-ui-js 的结尾，会把
    miku-fit-oneline 整块漏掉（曾因此在自动找参照的路径上全部失败）。
    """
    start = text.find(JS_CALL_COMMENT)
    if start < 0:
        raise SystemExit(f"[错误] {where} 里没有 createIcons 注释，不是新版模板/报告")
    fit = text.find(FIT_OPEN)
    if fit < 0:
        raise SystemExit(f"[错误] {where} 里找不到 {FIT_OPEN}")
    end = text.find("</script>", fit)
    if end < 0:
        raise SystemExit(f"[错误] {where} 里 miku-fit-oneline 脚本没有闭合标签")
    return text[start:end + len("</script>")]


def _parse_icons(text: str) -> dict:
    icons: dict = {}
    for name, inner in RE_ICON_SVG.findall(text):
        inner = inner.strip()
        if name in icons and icons[name] != inner:
            print(f"[警告] 图标 {name} 有多个不同版本的路径，取第一个")
            continue
        icons[name] = inner
    return icons


def layer_from_template(path: str, lang: str) -> Layer:
    """从 Jinja 模板提取（渲染掉报告语言相关的少量表达式）。"""
    t = open(path, encoding="utf-8").read()
    if CSS_OPEN not in t:
        raise SystemExit(f"[错误] {path} 看起来不是新版模板（没有 {CSS_OPEN}）")

    m = re.search(r'\{%\s*set T = (\{.*?\})\s*%\}', t, re.S)
    if not m:
        raise SystemExit("[错误] 模板里找不到语言字典 T")
    try:
        tdict = ast.literal_eval(m.group(1))
    except Exception as exc:  # noqa: BLE001
        raise SystemExit(f"[错误] 解析模板语言字典失败：{exc}")

    def render_js(block: str) -> str:
        def sub(mm):
            key = mm.group(1)
            if key not in tdict or lang not in tdict[key]:
                raise SystemExit(f"[错误] 语言字典缺少 {key}[{lang}]")
            return _tojson(tdict[key][lang])
        out = RE_TOJSON.sub(sub, block)
        if "{{" in out or "{%" in out:
            raise SystemExit("[错误] 交互层脚本里还有未渲染的模板表达式")
        return out

    def render_css(block: str, tc_first: bool) -> str:
        out = RE_IF_TC.sub(lambda mm: mm.group(1) if tc_first else mm.group(2), block)
        if "{{" in out or "{%" in out:
            raise SystemExit("[错误] 交互层样式里还有未渲染的模板表达式")
        return out

    css = render_css(_slice(t, CSS_BEGIN, CSS_END, path), lang == "zh-Hant")
    tail = render_js(_tail_block(t, path))
    return Layer(css, tail, _parse_icons(t), path, lang)


def layer_from_report(path: str) -> Layer:
    """从一份已经升级过的新版报告里提取（已经是渲染好的成品）。"""
    t = open(path, encoding="utf-8").read()
    if CSS_OPEN not in t or JS_ID not in t:
        raise SystemExit(f"[错误] {path} 不是新版报告（缺少交互层）")
    lang = "zh-Hans"
    m = re.search(r'<html lang="([^"]+)"', t)
    if m and m.group(1) in ("zh-Hant", "en", "ja", "zh-Hans"):
        lang = m.group(1)
    css, tail = _slice(t, CSS_BEGIN, CSS_END, path), _tail_block(t, path)
    if "#miku-nav" not in css or JS_ID not in tail or FIT_OPEN not in tail:
        raise SystemExit(f"[错误] {path} 提取到的层不完整（缺 导航样式 / 脚本 / 单行自适应）")
    return Layer(css, tail, _parse_icons(t), path, lang)


def find_layer(args_layer) -> Layer:
    """决定从哪儿取交互层：显式参数 > 自动探测新版模板 > 自动探测新版报告。"""
    if args_layer.template:
        return layer_from_template(args_layer.template, args_layer.lang)
    if args_layer.reference:
        return layer_from_report(args_layer.reference)

    for cand in _template_candidates():
        if not os.path.isfile(cand):
            continue
        head = _head(cand)
        if CSS_OPEN not in head:
            print(f"[跳过] {cand}（是旧版模板，没有交互层）")
            continue
        print(f"[信息] 自动使用新版模板：{cand}")
        return layer_from_template(cand, args_layer.lang)

    ref = _find_new_report(args_layer.paths, args_layer.lang)
    if ref:
        print(f"[信息] 自动使用新版报告作参照：{ref}")
        return layer_from_report(ref)

    raise SystemExit(
        "[错误] 找不到交互层来源。请用 --template 指定新版 html_template.html，"
        "或用 --reference 指定一份已经升级过的报告。")


def _head(path: str, limit: int = 0) -> str:
    """读文件内容；limit>0 时只读前 limit 个字符。"""
    try:
        with open(path, encoding="utf-8", errors="replace") as fh:
            return fh.read(limit) if limit > 0 else fh.read()
    except OSError:
        return ""


def _find_new_report(paths, want_lang="zh-Hans"):
    """在目标目录树里找一份已经升级过的新版报告当参照。

    先按语言筛（zh-Hant/zh-CN 的报告别拿 en/ja 变体当参照，字体分支会串），
    同语言里取 mtime 最新的一份。
    """
    cands = []
    for p in paths:
        root_dir = p if os.path.isdir(p) else (os.path.dirname(p) or ".")
        for root, _dirs, files in os.walk(root_dir):
            for f in files:
                if not f.endswith(".html"):
                    continue
                fp = os.path.join(root, f)
                text = _head(fp)
                if CSS_OPEN not in text or JS_ID not in text:
                    continue
                m = re.search(r'<html[^>]*\blang="([^"]*)"', text)
                rl = m.group(1) if m else ""
                same = rl == want_lang or (want_lang == "zh-Hans" and rl in ("zh-CN", "zh-Hans"))
                try:
                    cands.append((same, os.path.getmtime(fp), fp, rl))
                except OSError:
                    cands.append((same, 0.0, fp, rl))
    if not cands:
        return None
    cands.sort(key=lambda c: (c[0], c[1]), reverse=True)
    if not cands[0][0]:
        print(f"[提示] 目标目录里没有 {want_lang} 的新版报告，改用 {cands[0][3] or '未知语言'} 的那份做参照")
    return cands[0][2]


def _template_candidates():
    here = os.path.dirname(os.path.abspath(__file__))
    rel = os.path.join("src", "infrastructure", "reporting", "templates", "HatsuneMiku", "html_template.html")
    roots = [os.getcwd(), here, os.path.dirname(here), os.path.expanduser("~")]
    out = [os.path.join(r, rel) for r in roots]
    # AstrBot 常见安装位置
    out += [os.path.join(os.path.expanduser("~"), d, "data", "plugins",
                         "astrbot_plugin_qq_group_daily_analysis", rel)
            for d in ("tgtest", "astrbot", "AstrBot")]
    return out


# ---------------------------------------------------------------- 升级单个文件

RE_LANG_EN = re.compile(r':lang\(en\)\s*\{[^}]*\}')
SC_THEN_TC = "'Noto Sans SC', 'Noto Sans TC'"
TC_THEN_SC = "'Noto Sans TC', 'Noto Sans SC'"


def _target_tc_first(text: str) -> bool:
    """目标文件该用「繁先」还是「简先」字体分支。

    旧报告里的 lang 就写着答案：zh-Hant 说明当年的字体源在海外（模板的 _TC_FIRST 为真），
    zh-CN 则是大陆（假）。新版模板注入层里只有 :lang(en) 那段随这个分支变化。
    """
    m = re.search(r'<html[^>]*\blang="([^"]*)"', text)
    return bool(m) and m.group(1).lower().replace("_", "-").startswith("zh-hant")


def _normalize_lang_en(css: str, tc_first: bool) -> str:
    """把注入层里 :lang(en) 那段的中文字体顺序调成与目标文件一致（否则与模板产出差两行）。"""
    def fix(m):
        blk = m.group(0)
        if tc_first:
            return blk.replace(SC_THEN_TC, TC_THEN_SC)
        return blk.replace(TC_THEN_SC, SC_THEN_TC)
    return RE_LANG_EN.sub(fix, css)


def _inline_icon(m, icons, warn):
    name = m.group(2)
    inner = icons.get(name)
    if inner is None:
        warn.append(f"未知图标 {name}（保留原样）")
        return m.group(0)
    attrs = m.group(1) + m.group(3)
    cls = re.search(r'class="([^"]*)"', attrs)
    style = re.search(r'style="([^"]*)"', attrs)
    classes = "lucide lucide-" + name + ((" " + cls.group(1)) if cls else "")
    st = ""
    if style:
        st = ' style="%s"' % re.sub(r"\s+", " ", style.group(1)).strip()
    return ('<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" '
            'fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" '
            'stroke-linejoin="round" data-lucide="%s" aria-hidden="true" class="%s"%s>%s</svg>'
            % (name, classes, st, inner))


def _wrap_hover(css_text: str, selector: str, steps: list) -> str:
    """把旧的 :hover 规则收进 @media (hover: hover) and (pointer: fine)。"""
    pat = re.compile(r'([ \t]*)' + re.escape(selector) + r'\s*\{([^}]*)\}\n')
    m = pat.search(css_text)
    if not m:
        return css_text
    if "@media (hover: hover)" in css_text[max(0, m.start() - 200):m.start()]:
        return css_text  # 已经包过
    indent, body = m.group(1), m.group(2)
    inner = "".join(indent + "    " + ln.strip() + "\n"
                    for ln in body.strip().splitlines() if ln.strip())
    new = (f"{indent}@media (hover: hover) and (pointer: fine) {{\n"
           f"{indent}    {selector} {{\n{inner}{indent}    }}\n{indent}}}\n")
    steps.append(f"{selector} 收进 hover 媒体查询")
    return css_text[:m.start()] + new + css_text[m.end():]


def upgrade(text: str, layer: Layer) -> tuple:
    """返回 (新文本, 已做步骤列表, 警告列表)。未改动时新文本与原文一致。"""
    steps, warn = [], []
    n_icon = len(RE_I.findall(text))
    text, n_cdn = RE_CDN.subn(lambda m: CDN_COMMENT + "\n", text, count=1)
    if n_cdn:
        steps.append(f"删除 lucide CDN 引用（{n_icon} 个图标改为内联 SVG）")

    text, n_call = RE_CALL.subn(lambda m: "\n" + layer.tail + "\n", text, count=1)
    if n_call:
        steps.append("注入网页交互层脚本（导航/进度条/回顶/折叠/单行自适应）")
    elif JS_ID not in text:
        warn.append("找不到 lucide.createIcons() 调用，脚本层未注入")

    if CSS_OPEN not in text:
        text = text.replace("</head>",
                            _normalize_lang_en(layer.css, _target_tc_first(text)) + "\n</head>", 1)
        steps.append("注入网页交互层样式（含宽屏栅格与移动端让位）")

    text, n = RE_I.subn(lambda m: _inline_icon(m, layer.icons, warn), text)
    if n:
        steps.append(f"内联 {n} 个图标 SVG")

    if 'name="google"' not in text:
        text = text.replace('<meta charset="UTF-8">',
                            '<meta charset="UTF-8">\n    <meta name="google" content="notranslate">', 1)
        steps.append("补 notranslate（避免浏览器弹繁体翻译提示）")

    if "Noto+Sans+JP" not in text:
        for anchor in ("&family=Noto+Sans+SC:wght@400;500;700",
                       "&family=Noto+Sans+SC:wght@400%3B500%3B700"):
            if anchor in text:
                text = text.replace(anchor, anchor + "&family=Noto+Sans+JP:wght@400;700", 1)
                steps.append("字体链补 Noto Sans JP")
                break

    old_body = "background-attachment: fixed;\n\n            padding: 40px 20px;"
    if old_body in text:
        text = text.replace(old_body, "background-attachment: fixed;\n\n            padding: 74px 20px 40px;", 1)
        steps.append("body 顶部留白 40px → 74px（给悬浮导航让位）")

    old_box = "position: relative;\n            padding: 40px;\n            overflow: hidden;"
    if old_box in text:
        text = text.replace(old_box, "position: relative;\n            padding: 30px 40px 40px;\n            overflow: hidden;", 1)
        steps.append("container 内边距对齐新版")

    i = text.find("</head>")
    if i > 0:
        head, rest = text[:i], text[i:]
        head = _wrap_hover(head, ".stat-box:hover", steps)
        head = _wrap_hover(head, ".card-common:hover", steps)
        text = head + rest
    return text, steps, warn


def is_report(text: str) -> bool:
    """旧版 HatsuneMiku 网页报告：有 .container，且带着模板专属标记。"""
    if 'class="container"' not in text:
        return False
    return "miku-" in text or "data-lucide" in text


def is_upgraded(text: str) -> bool:
    return all(k in text for k in LAYERS)


def verify(text: str, n_icons_expected: int) -> list:
    """写盘后自检：缺一项就算失败。"""
    bad = []
    for key in LAYERS:
        if key not in text:
            bad.append(f"缺少 {key}")
    left = len(RE_I.findall(text))
    if left:
        bad.append(f"仍有 {left} 个未内联的 <i data-lucide>")
    if "lucide.createIcons();" in text:
        bad.append("仍残留 lucide.createIcons()")
    got = len(RE_ICON_SVG.findall(text))
    if n_icons_expected and got < n_icons_expected:
        bad.append(f"内联 SVG 数量不足（{got} < {n_icons_expected}）")
    if "</html>" not in text:
        bad.append("文件结尾被破坏")
    if "</head>" not in text or "<body" not in text:
        bad.append("head/body 结构被破坏")
    return bad


# ---------------------------------------------------------------- 主流程

def _bak_path(fp: str, backup_dir) -> str:
    """备份路径：默认同目录 .bak；给了 --backup-dir 就按绝对路径镜像放进去。"""
    if not backup_dir:
        return fp + ".bak"
    return os.path.join(backup_dir, os.path.abspath(fp).lstrip("/")) + ".bak"


def collect(paths, recursive=True):
    out = []
    for p in paths:
        if os.path.isfile(p):
            out.append(p)
        elif os.path.isdir(p):
            if recursive:
                for root, _d, files in os.walk(p):
                    out += [os.path.join(root, f) for f in sorted(files) if f.endswith(".html")]
            else:
                out += [os.path.join(p, f) for f in sorted(os.listdir(p)) if f.endswith(".html")]
        else:
            print(f"[警告] 路径不存在：{p}")
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(
        description="一键把旧的 HatsuneMiku 网页报告升级到新版模板格式（就地替换，自动备份 .bak）")
    ap.add_argument("paths", nargs="*", default=["."], help="报告文件或目录，可多个（默认当前目录）")
    ap.add_argument("--template", help="新版 html_template.html（首选来源）")
    ap.add_argument("--reference", help="一份已经升级过的报告，从它里面提取交互层")
    ap.add_argument("--lang", default="zh-Hans", choices=["zh-Hans", "zh-Hant", "en", "ja"],
                    help="交互层界面文案语言（默认 zh-Hans，与旧报告正文一致）")
    ap.add_argument("--dry-run", action="store_true", help="只列需要升级的文件，不写盘")
    ap.add_argument("--no-backup", action="store_true", help="不生成 .bak 备份")
    ap.add_argument("--backup-dir", help="把备份集中放到这个目录（按绝对路径镜像，适合网页根目录）")
    ap.add_argument("--revert", action="store_true", help="从备份还原，撤销升级")
    ap.add_argument("--no-recursive", action="store_true", help="不递归子目录")
    ap.add_argument("-q", "--quiet", action="store_true", help="只打印结果，不逐条列改动")
    args = ap.parse_args(argv)
    args.paths = args.paths or ["."]

    files = collect(args.paths, recursive=not args.no_recursive)
    if not files:
        print("[信息] 没找到 .html 文件")
        return 0

    if args.revert:
        n = 0
        for fp in files:
            bak = _bak_path(fp, args.backup_dir)
            if not os.path.isfile(bak):
                continue
            shutil.copy2(bak, fp)
            n += 1
            if not args.quiet:
                print(f"[已还原] {fp}")
        print(f"\n已从备份还原 {n} 个文件")
        return 0

    layer = find_layer(args)
    print(f"[信息] 交互层来源：{layer.source}（界面语言 {layer.lang}，图标 {len(layer.icons)} 个）\n")

    done = skipped = failed = 0
    for fp in files:
        try:
            text = open(fp, encoding="utf-8").read()
        except (OSError, UnicodeDecodeError) as exc:
            print(f"[跳过] {fp}：读取失败 {exc}")
            skipped += 1
            continue
        if is_upgraded(text):
            skipped += 1
            continue
        if not is_report(text):
            skipped += 1
            continue
        n_icons = len(RE_I.findall(text))
        if args.dry_run:
            print(f"[待升级] {fp}（{n_icons} 个图标）")
            done += 1
            continue
        new_text, steps, warn = upgrade(text, layer)
        bad = verify(new_text, n_icons)
        if bad:
            print(f"[失败] {fp}：{'；'.join(bad)}")
            failed += 1
            continue
        if not args.no_backup:
            bak = _bak_path(fp, args.backup_dir)
            if not os.path.exists(bak):
                os.makedirs(os.path.dirname(bak) or ".", exist_ok=True)
                shutil.copy2(fp, bak)
        tmp = fp + ".tmp-upgrade"
        with open(tmp, "w", encoding="utf-8") as fh:
            fh.write(new_text)
        os.replace(tmp, fp)
        if not args.no_backup:
            bak = _bak_path(fp, args.backup_dir)
            if os.path.exists(bak):
                try:
                    os.chmod(fp, os.stat(bak).st_mode & 0o7777)
                except OSError:
                    pass
        done += 1
        print(f"[已升级] {fp}")
        if not args.quiet:
            for s in steps:
                print(f"          · {s}")
            for w in warn:
                print(f"          ! {w}")

    stamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    print(f"\n完成（{stamp}）：本次处理 {done} 个"
          f"{'（dry-run 预览，未写盘）' if args.dry_run else ''}，跳过 {skipped} 个，失败 {failed} 个")
    print("跳过 = 已经是新版，或不是 HatsuneMiku 网页报告")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
