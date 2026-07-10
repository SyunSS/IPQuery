# IPQuery

跨平台 IP 归属地解析工具，支持域名/IP 输入、多 DNS 解析（系统/自定义/DoH）、GeoLite2 + 纯真双数据库查询、CDN 检测。

## 功能特性

- **输入灵活** — 支持域名、IPv4、IPv6、完整 URL（自动剥离协议头/路径/端口）
- **三种 DNS 模式**
  - 系统 DNS — 自动读取系统配置
  - 自定义 DNS — 手动指定 DNS 服务器
  - DoH (DNS over HTTPS) — 内置 Cloudflare / Google / 阿里云 / Quad9 端点，防劫持
- **双数据库查询**
  - GeoLite2 Country + City + ASN — 全球覆盖
  - 纯真 IP 数据库（qqwry.dat）— 中国大陆省市高精度回退
- **CDN 检测** — 基于 ASN 组织名识别 30+ 主流 CDN / 云服务商
- **一键更新数据库** — 从 GitHub 下载最新数据库文件（国内 gh-proxy 加速）
- **导出 CSV** — UTF-8 BOM 编码
- **跨平台** — Windows / macOS 原生支持

## 界面预览

![screenshot](screenshot.png?v=2)

## 安装

### 依赖

```bash
pip install PyQt6 geoip2 dnspython requests qqwry-py3
```

### 数据库文件

首次运行后点击界面中的「更新数据库」按钮，自动下载四个数据库文件：

- `GeoLite2-Country.mmdb`
- `GeoLite2-City.mmdb`
- `GeoLite2-ASN.mmdb`
- `qqwry.dat`

数据来源：
- GeoLite2: [P3TERX/GeoLite.mmdb](https://github.com/P3TERX/GeoLite.mmdb)
- 纯真 IP: [out0fmemory/qqwry.dat](https://github.com/out0fmemory/qqwry.dat)

### 直接运行

```bash
python ip_lookup_gui.py
```

## 打包

### Windows

双击 `build_windows.bat`，自动安装依赖、生成图标、打包为 `dist/IPQuery.exe`。

### macOS

```bash
chmod +x build_macos.sh
./build_macos.sh
```

输出 `dist/IPQuery.app`，拖入 `/Applications` 即可。

## 数据存放路径

| 平台 | 运行方式 | 数据库默认路径 |
|---|---|---|
| Windows | 脚本 / EXE | 程序所在目录 |
| macOS | 脚本 | 脚本所在目录 |
| macOS | .app | `~/Library/Application Support/IPQuery/db/` |

## 技术栈

- Python 3.9+
- PyQt6 — GUI 界面
- geoip2 (maxminddb) — GeoLite2 数据库查询
- dnspython — DNS 解析
- qqwry-py3 — 纯真 IP 数据库解析
- requests — 数据库下载 / DoH 请求
- PyInstaller — 打包

## License

MIT
