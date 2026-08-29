# 初音未来模板装饰图 404 修复工具

一键替换 [astrbot_plugin_qq_group_daily_analysis](https://github.com/SXP-Simon/astrbot_plugin_qq_group_daily_analysis) 历史日报 HTML 文件里失效的初音未来（HatsuneMiku）装饰图链接。

## 问题

初音未来模板的装饰图原本指向第三方图床 img.heliar.top，该域名 DNS 已失效。插件更新后新生成的日报已修复，但**已经生成好的历史日报 HTML 文件**里的链接还是旧的，打开仍是破图（404）。

## 谁需要用

- 已经生成了日报 HTML、历史日报里初音模板装饰图显示破图的用户
- 把日报 HTML 部署到网页上、旧日报装饰图显示不出来的用户

> 新生成的日报已自带修复，本脚本只用于抢救历史日报文件。

## 用法

把本仓库的脚本放到日报 HTML 文件所在目录（含 report_*.html 等日报文件的目录，通常在 data/html 下）：

```
.../data/html/
```

然后运行：

- Windows：双击 replace_miku_image_url.bat
- Linux / macOS：bash replace_miku_image_url.sh

脚本会自动扫描该目录（含子目录）下所有 .html 文件，把失效的 img.heliar.top 链接替换为 jsDelivr 直链，替换完会列出改了哪些文件。

## 效果

替换后历史日报的装饰图改由 jsDelivr CDN 托管，恢复显示。

## 文件

| 文件 | 用途 |
|------|------|
| replace_miku_image_url.sh | Linux / macOS 用（依赖 python3） |
| replace_miku_image_url.bat | Windows 用（依赖自带 PowerShell） |
