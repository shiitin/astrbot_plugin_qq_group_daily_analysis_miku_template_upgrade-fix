# 初音未来模板装饰图 404 修复工具

一键替换 [astrbot_plugin_qq_group_daily_analysis](https://github.com/SXP-Simon/astrbot_plugin_qq_group_daily_analysis) 初音未来（HatsuneMiku）模板里失效的装饰图链接。

## 问题

初音未来模板的 7 张装饰图原本指向第三方图床 img.heliar.top，该域名 DNS 已失效，导致报告里的装饰图全部显示为破图（404）。

## 谁需要用

- 本地部署了该插件、初音模板报告出现破图的用户
- 通过网页查看日报、初音模板装饰图显示不出来的用户

> 如果你是从 AstrBot 插件市场新安装的（v5.0.11 之后），模板已自带修复，无需使用本脚本。

## 用法

把本仓库的脚本放到插件的模板目录：

```
.../src/infrastructure/reporting/templates/HatsuneMiku/
```

然后运行：

- Windows：双击 `replace_miku_image_url.bat`
- Linux / macOS：`bash replace_miku_image_url.sh`

脚本会自动扫描该目录（含子目录）下所有 .html 文件，把失效的 img.heliar.top 链接替换为 jsDelivr 直链，替换完会列出改了哪些文件。

## 效果

替换后装饰图改由 jsDelivr CDN 托管（与插件 README 其它资源一致），报告恢复显示。

## 文件

| 文件 | 用途 |
|------|------|
| replace_miku_image_url.sh | Linux / macOS 用（依赖 python3） |
| replace_miku_image_url.bat | Windows 用（依赖自带 PowerShell） |
