# astrbot_plugin_qq_group_daily_analysis 初音未来模板 · 修复与升级工具

给 [astrbot_plugin_qq_group_daily_analysis](https://github.com/SXP-Simon/astrbot_plugin_qq_group_daily_analysis) 的
初音未来（HatsuneMiku）模板收拾**已经生成好的历史日报 HTML**。两个独立工具，按需取用：

| 工具 | 解决什么 | 谁需要 |
|---|---|---|
| 一、破图修复 | 历史日报里指向第三方图床 img.heliar.top 的装饰图链接失效（域名 DNS 没了，图 404） | 历史日报装饰图显示破图的人 |
| 二、模板追平 | 模板更新后，**已生成**的旧报告没有新版网页交互层（顶部导航/阅读进度条/回到顶部/折叠/宽屏栅格、图标内联） | 想让旧报告也变成新样式的人 |

> 两个工具都只处理**已经落盘的历史 HTML**：新生成的日报自带修复与新版模板，不需要跑。

## 文件说明

| 文件 | 用途 |
|---|---|
| replace_miku_image_url.bat | Windows 双击跑（工具一） |
| replace_miku_image_url.command | macOS 双击跑（工具一） |
| replace_miku_image_url.sh | Linux 双击（选“运行”）或终端跑（工具一） |
| fix_miku_image_urls.py | 服务器版（工具一）：可 -check 体检、--dry-run 预演、--backup-dir 集中备份 |
| upgrade_miku_report_html.py | 服务器版（工具二）：旧报告一键追平新版模板 |

## 工具一：历史日报破图修复

装饰图原指向 img.heliar.top（DNS 已失效、源站也没了），插件新版已改用 jsDelivr 直链，
但**已生成的历史日报 HTML 里的链接还是旧的**。

用法（双击版）：
1. 下载对应系统的脚本，放到日报 HTML 所在目录（含 report_*.html 的目录，通常在 data/html 下）
2. 双击运行（macOS 从 zip 解压后若提示无权限，先执行一次 chmod +x replace_miku_image_url.command）
3. 脚本会扫描该目录（含子目录）下所有 .html，把失效链接换成 jsDelivr 直链，并列出改了哪些文件

用法（服务器版）：
    python3 fix_miku_image_urls.py 日报目录 --dry-run              # 只列要改的
    python3 fix_miku_image_urls.py 日报目录 --check                # 只统计还剩多少处
    python3 fix_miku_image_urls.py 日报目录 --backup-dir /var/tmp/bak  # 备份集中存，再写盘

## 工具二：把旧报告追平新版模板

新版网页模板把交互件（顶部导航、阅读进度条、回到顶部、两列折叠、宽屏栅格）与图标
内联进了产物；旧报告没有这些。本脚本按新版模板“受影响的 HTML 部分”就地升级：

1. 图标内联：`<i data-lucide="x">` → 内联 SVG，删掉 lucide CDN 与运行时调用
2. 注入 `<style id="miku-web-ui">` 交互层样式与 `<script id="miku-web-ui-js">`、`<script id="miku-fit-oneline">`
3. 头部补 `notranslate`、字体链补 Noto Sans JP
4. 基础 CSS 对齐：body 顶部留白、容器内边距、hover 规则收进 `@media (hover: hover)`

交互层不是写死的：脚本优先从**新版模板**（html_template.html）现取并渲染对应语言，
取不到就在目标目录里找一份已经升级过的新版报告当参照。语言按每个文件自己的 `<html lang>`
归一化，简体/繁体两个字体分支都能对上。

用法：

    python3 upgrade_miku_report_html.py 报告目录 --dry-run                  # 先看清单
    python3 upgrade_miku_report_html.py 报告目录 --template .../HatsuneMiku/html_template.html
    python3 upgrade_miku_report_html.py 报告目录                            # 自动找参照，就地升级
    python3 upgrade_miku_report_html.py 报告目录 --backup-dir /var/tmp/bak  # 备份集中存
    python3 upgrade_miku_report_html.py 报告目录 --lang zh-Hant             # 界面文案语言
    python3 upgrade_miku_report_html.py 报告目录 --revert                   # 从备份还原

已升级的文件再跑会全部跳过（幂等）；写盘后脚本会自检（三块 id 齐、无残留旧图标、
无残留 CDN 调用、head/body 结构完好），任一不过就不写盘。

## 常见问题

- **替换后会再破吗？** 生成端插件升级后就正常了；若生成端仍是旧版，新生成的日报会再次
  带上旧链。可把 `fix_miku_image_urls.py --check` 挂成每日任务，命中才动手。
- **工具二会不会动正文/数据？** 不会：只做上面四类替换与两段注入，正文与内嵌 JSON 不动。
  建议先 `--dry-run`，正式跑时留 `--backup-dir`。
- **本仓库改过名**：原 `miku-template-image-fix` 已改名为
  `astrbot_plugin_qq_group_daily_analysis_miku_template_upgrade-fix`，旧地址与旧 release
  下载链接都会自动 301 跳转。
