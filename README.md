# 初音未来模板装饰图 404 修复工具

一键替换 [astrbot_plugin_qq_group_daily_analysis](https://github.com/SXP-Simon/astrbot_plugin_qq_group_daily_analysis) 历史日报 HTML 文件里失效的初音未来（HatsuneMiku）装饰图链接。

## 问题

初音未来模板的装饰图原本指向第三方图床 img.heliar.top，该域名 DNS 已失效。插件更新后新生成的日报已修复，但**已经生成好的历史日报 HTML 文件**里的链接还是旧的，打开仍是破图（404）。

## 谁需要用

- 已经生成了日报 HTML、历史日报里初音模板装饰图显示破图的用户
- 把日报 HTML 部署到网页上、旧日报装饰图显示不出来的用户

> 新生成的日报已自带修复，本脚本只用于抢救历史日报文件。

## 下载（按你的系统选一个就行）

| 你的系统 | 下载这个文件 | 怎么运行 |
|---------|------------|---------|
| Windows | replace_miku_image_url.bat | 双击 |
| macOS | replace_miku_image_url.command | 双击 |
| Linux | replace_miku_image_url.sh | 双击（选"运行"），或终端执行 |

## 用法

1. 下载对应脚本，放到日报 HTML 文件所在目录（含 report_*.html 的目录，通常在 data/html 下）
2. 双击运行（Windows 直接双击；Linux 双击后选「运行」）
   - macOS 从 zip 解压后若双击提示无权限，先在终端执行一次 chmod +x replace_miku_image_url.command 再双击
3. 脚本会自动扫描该目录（含子目录）下所有 .html，把失效的 img.heliar.top 链接替换为 jsDelivr 直链，替换完会列出改了哪些文件

## 双击没反应的备用方式（命令行）

- Windows：在目录空白处 Shift+右键 → 在此处打开命令窗口 → 输入 replace_miku_image_url.bat
- Linux / macOS：终端里进入该目录，执行 bash replace_miku_image_url.sh

## 效果

替换后历史日报的装饰图改由 jsDelivr CDN 托管，恢复显示。
