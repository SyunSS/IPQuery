#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
IP 归属地解析工具 — 带 GUI
支持：域名（系统 DNS / 自定义 DNS）→ IP 解析 → GeoLite2 归属地查询 → CDN 检测
数据库更新来源：
  - GeoLite2: https://github.com/P3TERX/GeoLite.mmdb
  - 纯真IP:   https://github.com/out0fmemory/qqwry.dat
兼容：macOS / Windows
"""

import os
import sys
import csv
import socket
import time
import traceback
from typing import Optional
from urllib.parse import urlparse
from datetime import datetime

# ---------- PyQt6 ----------
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QGroupBox, QLabel, QTextEdit, QLineEdit, QPushButton, QTableWidget,
    QTableWidgetItem, QProgressBar, QFileDialog, QMessageBox, QCheckBox,
    QRadioButton, QButtonGroup, QHeaderView, QStatusBar, QDialog,
    QDialogButtonBox, QComboBox
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QFont, QColor

# ---------- 第三方库 ----------
try:
    import geoip2.database
except ImportError:
    geoip2 = None

try:
    import dns.resolver
except ImportError:
    dns = None

try:
    import requests
except ImportError:
    requests = None

try:
    from qqwry import QQwry as QQwryReader
except ImportError:
    QQwryReader = None

# ============================================================================
# 常量
# ============================================================================

# 数据库文件配置: (显示名, 文件名, 下载URL) — 使用 gh-proxy.org 国内加速
DB_FILES_CONFIG = [
    ("Country",  "GeoLite2-Country.mmdb",
     "https://gh-proxy.org/https://github.com/P3TERX/GeoLite.mmdb/raw/download/GeoLite2-Country.mmdb"),
    ("City",     "GeoLite2-City.mmdb",
     "https://gh-proxy.org/https://github.com/P3TERX/GeoLite.mmdb/raw/download/GeoLite2-City.mmdb"),
    ("ASN",      "GeoLite2-ASN.mmdb",
     "https://gh-proxy.org/https://github.com/P3TERX/GeoLite.mmdb/raw/download/GeoLite2-ASN.mmdb"),
    ("纯真IP",   "qqwry.dat",
     "https://raw.githubusercontent.com/out0fmemory/qqwry.dat/master/qqwry_lastest.dat"),
]

CDN_ASN_KEYWORDS = [
    "Cloudflare", "Akamai", "Fastly", "Amazon", "AWS", "CloudFront",
    "Alibaba", "Alibaba Cloud", "Tencent", "Tencent Cloud",
    "EdgeCast", "Limelight", "CDNetworks", "KeyCDN", "StackPath",
    "Imperva", "Incapsula", "Sucuri", "Azure", "Microsoft",
    "Google", "Google Cloud", "BunnyCDN", "CacheFly", "CDN77",
    "Kingsoft", "Wangsu", "ChinaCache", "Qiniu", "Qiniu CDN",
    "UCloud", "Baidu", "Baidu Cloud", "Huawei Cloud", "JD Cloud",
    "NetEase", "YUNDUN", "DDoS-Guard", "OVH", "Voxility",
]

DEFAULT_CUSTOM_DNS = ["8.8.8.8", "223.5.5.5", "114.114.114.114"]

# DNS 并发控制参数
DNS_DELAY_SEC = 0.15          # 每条域名解析间隔（秒）
DNS_RETRY_MAX = 3             # 最大重试次数
DNS_RETRY_BASE_DELAY = 0.8    # 重试基础延迟（秒），指数递增

# ============================================================================
# 样式表
# ============================================================================
STYLE_QSS = """
QMainWindow {
    background-color: #f5f6fa;
}
QGroupBox {
    font-size: 13px;
    font-weight: bold;
    color: #2c3e50;
    border: 1px solid #dcdde1;
    border-radius: 8px;
    margin-top: 14px;
    padding-top: 18px;
    background-color: #ffffff;
}
QGroupBox::title {
    subcontrol-origin: margin;
    left: 14px;
    padding: 4px 12px;
    background-color: #ffffff;
    border: 1px solid #dcdde1;
    border-radius: 6px;
}
QTextEdit, QLineEdit {
    border: 1px solid #dcdde1;
    border-radius: 6px;
    padding: 8px;
    font-size: 13px;
    background-color: #ffffff;
    color: #2d3436;
}
QTextEdit:focus, QLineEdit:focus {
    border-color: #3498db;
}
QPushButton {
    border-radius: 6px;
    padding: 8px 20px;
    font-size: 13px;
    font-weight: 500;
    border: none;
}
QPushButton#btnQuery {
    background-color: #3498db;
    color: white;
}
QPushButton#btnQuery:hover {
    background-color: #2980b9;
}
QPushButton#btnQuery:pressed {
    background-color: #2471a3;
}
QPushButton#btnClear {
    background-color: #95a5a6;
    color: white;
}
QPushButton#btnClear:hover {
    background-color: #7f8c8d;
}
QPushButton#btnExport {
    background-color: #27ae60;
    color: white;
}
QPushButton#btnExport:hover {
    background-color: #219a52;
}
QPushButton#btnUpdateDb {
    background-color: #e67e22;
    color: white;
}
QPushButton#btnUpdateDb:hover {
    background-color: #d35400;
}
QPushButton#btnBrowseDb {
    background-color: #ecf0f1;
    color: #2c3e50;
    border: 1px solid #bdc3c7;
}
QPushButton#btnBrowseDb:hover {
    background-color: #d5dbdb;
}
QTableWidget {
    border: 1px solid #dcdde1;
    border-radius: 6px;
    background-color: #ffffff;
    gridline-color: #ecf0f1;
    font-size: 12px;
    alternate-background-color: #f8f9fa;
}
QTableWidget::item {
    padding: 6px;
}
QHeaderView::section {
    background-color: #2c3e50;
    color: white;
    padding: 8px;
    border: none;
    font-weight: bold;
    font-size: 12px;
}
QProgressBar {
    border: none;
    border-radius: 4px;
    background-color: #ecf0f1;
    text-align: center;
    font-size: 11px;
    height: 20px;
}
QProgressBar::chunk {
    background-color: #3498db;
    border-radius: 4px;
}
QStatusBar {
    font-size: 12px;
    color: #636e72;
}
QTabWidget::pane {
    border: 1px solid #dcdde1;
    border-radius: 6px;
    background-color: #ffffff;
}
QTabBar::tab {
    padding: 8px 20px;
    font-size: 13px;
    border: 1px solid #dcdde1;
    border-bottom: none;
    border-radius: 6px 6px 0 0;
    background-color: #ecf0f1;
    margin-right: 2px;
}
QTabBar::tab:selected {
    background-color: #ffffff;
    font-weight: bold;
    color: #3498db;
}
QRadioButton, QCheckBox {
    font-size: 13px;
    color: #2d3436;
    spacing: 6px;
}
QLabel {
    color: #2c3e50;
}
"""


# ============================================================================
# 内嵌图标（运行时用 QPainter 绘制，PyInstaller 打包无需 PNG 插件）
# ============================================================================
# ============================================================================

def _get_embedded_icon():
    """返回内嵌的窗口图标，运行时用 QPainter 绘制，PyInstaller 打包兼容"""
    from PyQt6.QtGui import QIcon, QPixmap, QPainter, QColor, QFont
    from PyQt6.QtCore import Qt, QRectF
    px = QPixmap(128, 128)
    px.fill(Qt.GlobalColor.transparent)
    p = QPainter(px)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    p.setBrush(QColor("#3498db"))
    p.setPen(Qt.PenStyle.NoPen)
    p.drawEllipse(4, 4, 120, 120)
    p.setBrush(QColor("#ffffff"))
    p.drawEllipse(20, 20, 88, 88)
    p.setFont(QFont("Arial", 28, QFont.Weight.Bold))
    p.setPen(QColor("#2c3e50"))
    p.drawText(QRectF(0, 38, 128, 50), Qt.AlignmentFlag.AlignCenter, "IPQ")
    p.end()
    return QIcon(px)


# ============================================================================
# GeoIP 查询引擎（GeoLite2 + 纯真 IP 回退）
# ============================================================================


# ============================================================================
# 输入规范化：提取域名 / IP
# ============================================================================
def normalize_input(raw: str) -> str:
    """
    将用户输入的任意形式转换为可解析的 hostname 或 IP:
      http://www.baidu.com       → www.baidu.com
      https://www.baidu.com/path → www.baidu.com
      baidu.com:443              → baidu.com
      [::1]:8080                 → ::1
      www.baidu.com              → www.baidu.com
      1.1.1.1                    → 1.1.1.1
      2606:4700:4700::1111       → 2606:4700:4700::1111
    """
    text = raw.strip()

    # 已经是合法 IP（v4 / v6），直接返回
    if is_ip_address(text):
        return text

    # 1) urlparse 处理含 scheme 的完整 URL
    if "://" in text:
        p = urlparse(text)
        if p.hostname:
            text = p.hostname
            if is_ip_address(text):
                return text
            return text

    # 2) 去掉路径部分
    if "/" in text:
        text = text.split("/", 1)[0]

    # 再次检查去掉路径后是否为合法 IP
    if is_ip_address(text):
        return text

    # 3) 去掉端口号
    # IPv6 方括号形式: [::1]:443 → ::1
    if text.startswith("[") and "]" in text:
        text = text.split("]", 1)[0].strip("[]")

    # 再次检查是否为合法 IP
    if is_ip_address(text):
        return text

    # 普通格式去掉端口（域名:443 或 IPv4:443）
    if ":" in text:
        parts = text.rsplit(":", 1)
        if len(parts) == 2 and parts[-1].isdigit():
            text = parts[0]

    return text.strip()


# ============================================================================
# IP 地址判断
# ============================================================================
def is_ip_address(s: str) -> bool:
    """判断字符串是否为合法 IPv4 或 IPv6 地址"""
    if not s:
        return False
    try:
        socket.inet_pton(socket.AF_INET, s)
        return True
    except (OSError, ValueError):
        pass
    try:
        socket.inet_pton(socket.AF_INET6, s)
        return True
    except (OSError, ValueError):
        pass
    return False


# ============================================================================
# DNS 解析引擎 — 系统 DNS / 自定义 DNS / DoH
# ============================================================================
class DnsResolver:
    """
    支持三种解析模式：
      - 系统 DNS:   Resolver(configure=True)，禁用缓存
      - 自定义 DNS: Resolver(configure=False) + 手动 nameservers，禁用缓存
      - DoH:        DNS over HTTPS，通过 HTTP POST 发送 wire-format 查询
    """
    MODE_SYSTEM = "system"
    MODE_CUSTOM = "custom"
    MODE_DOH = "doh"

    DEFAULT_DOH_URLS = [
        "https://cloudflare-dns.com/dns-query",
        "https://dns.google/dns-query",
        "https://dns.alidns.com/dns-query",
        "https://dns.quad9.net/dns-query",
    ]

    def __init__(self, mode: str = "system",
                 custom_servers: Optional[list[str]] = None,
                 doh_url: Optional[str] = None):
        self.mode = mode
        self.custom_servers = custom_servers or []
        self.doh_url = doh_url or self.DEFAULT_DOH_URLS[0]
        self._resolver = None

        if mode == self.MODE_CUSTOM and self.custom_servers:
            self._resolver = dns.resolver.Resolver(configure=False)
            self._resolver.nameservers = self.custom_servers
            self._resolver.cache = dns.resolver.LRUCache(0)  # 禁用缓存
            self._resolver.timeout = 5
            self._resolver.lifetime = 5
        elif mode == self.MODE_SYSTEM:
            self._resolver = dns.resolver.Resolver()
            self._resolver.cache = dns.resolver.LRUCache(0)  # 禁用缓存
            self._resolver.timeout = 5
            self._resolver.lifetime = 5
        # DoH 模式不需要传统 resolver

    def resolve(self, domain: str) -> set[str]:
        if self.mode == self.MODE_DOH:
            return self._resolve_doh(domain)
        return self._resolve_standard(domain)

    def _resolve_standard(self, domain: str) -> set[str]:
        """标准 DNS 解析 (UDP)"""
        ips: set[str] = set()
        for record_type in ("A", "AAAA"):
            try:
                answers = self._resolver.resolve(domain, record_type)
                for rdata in answers:
                    ips.add(rdata.to_text())
            except Exception:
                pass
        return ips

    def _resolve_doh(self, domain: str) -> set[str]:
        """DNS over HTTPS 解析"""
        import dns.message
        import dns.rdatatype

        ips: set[str] = set()
        for rdtype in (dns.rdatatype.A, dns.rdatatype.AAAA):
            try:
                query = dns.message.make_query(domain, rdtype)
                resp = requests.post(
                    self.doh_url,
                    data=query.to_wire(),
                    headers={"Content-Type": "application/dns-message"},
                    timeout=5,
                )
                resp.raise_for_status()
                answer = dns.message.from_wire(resp.content)
                for rrset in answer.answer:
                    if rrset.rdtype in (dns.rdatatype.A, dns.rdatatype.AAAA):
                        for rdata in rrset:
                            ips.add(rdata.to_text())
            except Exception:
                pass
        return ips

    @staticmethod
    def resolve_with_retry(domain: str, resolver, retries: int = DNS_RETRY_MAX) -> set[str]:
        """带重试的域名解析"""
        for attempt in range(1, retries + 1):
            ips = resolver.resolve(domain)
            if ips:
                return ips
            if attempt < retries:
                delay = DNS_RETRY_BASE_DELAY * attempt
                time.sleep(delay)
        return set()


# ============================================================================
# Windows 路径兼容：geoip2 C 扩展的 fopen() 不认 UTF-8 路径（中文 Win 只认 GBK），
# 将含中文的 mmdb 文件复制到 %TEMP%\IPQuery_db（纯 ASCII 路径）再打开
# ============================================================================
def _ensure_ascii_path(filepath: str) -> str:
    """确保传给 C 扩展的路径是纯 ASCII。Windows 上必要时复制到临时目录。"""
    if sys.platform != "win32":
        return filepath
    try:
        filepath.encode("ascii")
        return filepath  # 已是纯 ASCII，无需处理
    except UnicodeEncodeError:
        pass
    import shutil
    cache_dir = os.path.join(os.environ.get("TEMP", os.path.expanduser("~")), "IPQuery_db")
    os.makedirs(cache_dir, exist_ok=True)
    cached = os.path.join(cache_dir, os.path.basename(filepath))
    # 原始文件更新时刷新缓存
    if not os.path.exists(cached) or os.path.getmtime(filepath) > os.path.getmtime(cached):
        shutil.copy2(filepath, cached)
    return cached


# ============================================================================
# GeoIP 查询引擎（GeoLite2 + 纯真 IP 回退）
# ============================================================================
class GeoIPEngine:
    """
    封装 GeoLite2 三库查询 + 纯真 IP 数据库回退。
    当 GeoLite2 City 库无法提供省份/城市时，自动使用纯真数据库补充。
    """

    LOCALE_FALLBACK = ["zh-CN", "en"]

    def __init__(self, country_db: str, city_db: str, asn_db: str,
                 qqwry_path: Optional[str] = None,
                 detect_cdn: bool = True):
        self.detect_cdn = detect_cdn
        # Windows: geoip2 C 扩展 fopen() 不认 UTF-8 中文路径,
        # 将 mmdb 文件复制到 %TEMP%\IPQuery_db (纯 ASCII) 再打开
        self._reader_country = geoip2.database.Reader(_ensure_ascii_path(country_db))
        self._reader_city = geoip2.database.Reader(_ensure_ascii_path(city_db))
        self._reader_asn = geoip2.database.Reader(_ensure_ascii_path(asn_db))

        # 加载纯真数据库
        self._qqwry = None
        if QQwryReader is not None and qqwry_path and os.path.exists(qqwry_path):
            try:
                qq = QQwryReader()
                if qq.load_file(qqwry_path):
                    self._qqwry = qq
            except Exception:
                pass

    def close(self):
        self._reader_country.close()
        self._reader_city.close()
        self._reader_asn.close()

    @staticmethod
    def _safe_name(names: dict, locales: list[str]) -> str:
        """从 names 字典中按 locale 优先级取第一个非空值"""
        for loc in locales:
            val = names.get(loc, "")
            if val:
                return val
        return ""

    def _qqwry_lookup(self, ip: str) -> tuple[str, str]:
        """
        用纯真数据库查询省份和城市。
        返回: (province, city)
        注: 纯真数据库仅支持 IPv4，不支持 IPv6。
        """
        if not self._qqwry or not self._qqwry.is_loaded():
            return "", ""
        if ":" in ip:
            return "", ""

        try:
            field1, field2 = self._qqwry.lookup(ip)
            if not field1:
                return "", ""

            f1 = field1.strip()

            # 模式 1: "浙江省杭州市" → 省+市
            if "省" in f1:
                idx = f1.index("省")
                province = f1[:idx + 1]    # "浙江省"
                rest = f1[idx + 1:]        # "杭州市"
                city = rest if rest.endswith("市") else ""
                return province, city

            # 模式 2: "北京市" / "天津市" / "上海市" / "重庆市" (直辖市)
            if f1.endswith("市"):
                return f1, f1  # province = city

            # 模式 3: "河北省" → 纯省份名
            if f1.endswith("省"):
                return f1, ""

            # 非中国 IP 不处理（GeoLite2 已有国家信息）
            return "", ""
        except Exception:
            return "", ""

    def lookup(self, ip: str) -> tuple:
        """
        返回: (country, province, city, lat, lon, asn_org, is_cdn)
        规则:
          1) City 库优先查询 country / subdivision / city / latlon
          2) subdivisions 可能为空，安全兜底
          3) zh-CN 缺失时回退 en
          4) City 库完全失败 → 回退 Country 库取国名
          5) 省份/城市为空时 → 尝试纯真数据库补充
        """
        country = province = city_name = ""
        lat = lon = ""

        # --- City 库 ---
        try:
            city_resp = self._reader_city.city(ip)
            country = self._safe_name(city_resp.country.names or {}, self.LOCALE_FALLBACK)

            subs = city_resp.subdivisions
            if subs and len(subs) > 0:
                most = subs.most_specific
                province = self._safe_name(most.names or {}, self.LOCALE_FALLBACK)

            city_name = self._safe_name(city_resp.city.names or {}, self.LOCALE_FALLBACK)

            if city_resp.location.latitude is not None:
                lat = str(city_resp.location.latitude)
            if city_resp.location.longitude is not None:
                lon = str(city_resp.location.longitude)

        except geoip2.errors.AddressNotFoundError:
            try:
                country = self._safe_name(
                    self._reader_country.country(ip).country.names or {},
                    self.LOCALE_FALLBACK
                )
            except geoip2.errors.AddressNotFoundError:
                country = ""
        except Exception:
            try:
                country = self._safe_name(
                    self._reader_country.country(ip).country.names or {},
                    self.LOCALE_FALLBACK
                )
            except Exception:
                country = ""

        # --- 纯真数据库回退：当省份/城市为空时补充 ---
        if (not province or not city_name) and self._qqwry is not None:
            qq_province, qq_city = self._qqwry_lookup(ip)
            if not province and qq_province:
                province = qq_province
            if not city_name and qq_city:
                city_name = qq_city
            # 纯真查到的是中国 IP 但 GeoLite2 没国家名，补中国
            if (province or city_name) and not country:
                country = "中国"

        # --- ASN ---
        asn_org = ""
        try:
            asn_info = self._reader_asn.asn(ip)
            asn_org = asn_info.autonomous_system_organization or ""
        except Exception:
            pass

        # --- CDN 检测 ---
        is_cdn = False
        if self.detect_cdn:
            asn_lower = asn_org.lower()
            is_cdn = any(k.lower() in asn_lower for k in CDN_ASN_KEYWORDS)
            if is_cdn and not country:
                country = "CDN"

        return (country, province, city_name, lat, lon, asn_org, "是" if is_cdn else "否")


# ============================================================================
# 后台工作线程
# ============================================================================
class WorkerThread(QThread):
    progress = pyqtSignal(int, int)
    status = pyqtSignal(str)
    result = pyqtSignal(list)
    error = pyqtSignal(str)
    finished = pyqtSignal()

    def __init__(self, inputs: list[str], dns_mode: str, custom_dns: list[str],
                 doh_url: str,
                 country_db: str, city_db: str, asn_db: str,
                 qqwry_path: Optional[str] = None,
                 detect_cdn: bool = True):
        super().__init__()
        self.inputs = inputs
        self.dns_mode = dns_mode
        self.custom_dns = custom_dns
        self.doh_url = doh_url
        self.country_db = country_db
        self.city_db = city_db
        self.asn_db = asn_db
        self.qqwry_path = qqwry_path
        self.detect_cdn = detect_cdn
        self._cancelled = False

    def cancel(self):
        self._cancelled = True

    def run(self):
        try:
            self._do_run()
        except Exception as e:
            tb = traceback.format_exc()
            print(f"[IPQuery FATAL] {e}\n{tb}", file=sys.stderr, flush=True)
            self.error.emit(f"查询异常:\n{tb}")

    def _do_run(self):
        # --- 阶段 0: 预处理输入 ---
        self.status.emit("阶段 1/3: 预处理输入...")
        hosts: list[tuple[str, str]] = []
        for item in self.inputs:
            norm = normalize_input(item)
            hosts.append((item, norm))

        if not hosts:
            self.status.emit("无有效输入")
            self.finished.emit()
            return
        self.status.emit(f"预处理完成，共 {len(hosts)} 条")

        # --- 阶段 1: DNS 解析 ---
        self.status.emit("阶段 2/3: DNS 解析...")
        dns_resolver = DnsResolver(
            mode=self.dns_mode,
            custom_servers=self.custom_dns if self.dns_mode == DnsResolver.MODE_CUSTOM else None,
            doh_url=self.doh_url if self.dns_mode == DnsResolver.MODE_DOH else None,
        )

        all_ips: list[tuple[str, str]] = []
        total_hosts = len(hosts)
        for i, (raw_src, host) in enumerate(hosts):
            if self._cancelled:
                self.finished.emit()
                return
            self.progress.emit(i + 1, total_hosts)

            if is_ip_address(host):
                all_ips.append((raw_src, host))
                continue

            ips = DnsResolver.resolve_with_retry(host, dns_resolver)
            if ips:
                for ip in sorted(ips):
                    all_ips.append((raw_src, ip))
            else:
                all_ips.append((raw_src, "解析失败"))

            if i < total_hosts - 1:
                time.sleep(DNS_DELAY_SEC)

        resolved_count = sum(1 for _, ip in all_ips if ip != "解析失败")
        self.status.emit(f"解析完成: {resolved_count}/{len(all_ips)} 个 IP")

        # --- 去重 ---
        seen: set[str] = set()
        deduped: list[tuple[str, str]] = []
        for src, ip in all_ips:
            if ip == "解析失败":
                deduped.append((src, ip))
            elif ip not in seen:
                seen.add(ip)
                deduped.append((src, ip))

        self.status.emit(f"去重后 {len(deduped)} 条")

        # --- 阶段 2: GeoIP 查询 ---
        if self._cancelled:
            self.finished.emit()
            return

        self.status.emit("阶段 3/3: 归属地查询...")
        engine = None
        try:
            engine = GeoIPEngine(
                country_db=self.country_db,
                city_db=self.city_db,
                asn_db=self.asn_db,
                qqwry_path=self.qqwry_path,
                detect_cdn=self.detect_cdn,
            )
        except Exception as e:
            self.status.emit(f"打开数据库失败: {e}")
            print(f"[IPQuery ERROR] 数据库打开失败: {e}", file=sys.stderr)
            self.finished.emit()
            return

        ip_entries = [(src, ip) for src, ip in deduped if ip != "解析失败"]
        total_ips = len(ip_entries)

        for idx, (src, ip) in enumerate(deduped):
            if self._cancelled:
                break

            if ip == "解析失败":
                row = [src, ip, "解析失败", "", "", "", "", "", "否"]
                self.result.emit(row)
                total_ips = max(total_ips, 1)
                self.progress.emit(idx + 1, total_ips)
                continue

            geo_result = engine.lookup(ip)
            row = [src, ip] + list(geo_result)
            self.result.emit(row)
            self.progress.emit(idx + 1, total_ips)

        if engine:
            engine.close()

        self.status.emit("查询完成")
        self.finished.emit()


# ============================================================================
# 数据库更新线程
# ============================================================================
class DbUpdateThread(QThread):
    progress_text = pyqtSignal(str)
    progress_percent = pyqtSignal(int)
    finished = pyqtSignal(bool, str)

    def __init__(self, db_dir: str):
        super().__init__()
        self.db_dir = db_dir

    def run(self):
        if requests is None:
            self.finished.emit(False, "缺少 requests 库，请执行: pip install requests")
            return

        total = len(DB_FILES_CONFIG)
        for idx, (name, filename, url) in enumerate(DB_FILES_CONFIG):
            filepath = os.path.join(self.db_dir, filename)

            self.progress_text.emit(f"正在下载 {filename} ({name})...")
            try:
                resp = requests.get(url, timeout=120, stream=True)
                resp.raise_for_status()
                total_size = int(resp.headers.get("content-length", 0))
                downloaded = 0
                with open(filepath, "wb") as f:
                    for chunk in resp.iter_content(chunk_size=8192):
                        f.write(chunk)
                        downloaded += len(chunk)
                        if total_size > 0:
                            self.progress_percent.emit(int(downloaded / total_size * 100))
                self.progress_text.emit(f"{filename} 下载完成")
                self.progress_percent.emit(int((idx + 1) / total * 100))
            except Exception as e:
                self.finished.emit(False, f"下载 {filename} 失败: {e}")
                return
        self.finished.emit(True, "全部 4 个数据库更新完成！")


# ============================================================================
# 主窗口
# ============================================================================
class IPLookupWindow(QMainWindow):
    COLUMNS = ["来源", "IP 地址", "国家", "省份", "城市", "经/纬度", "ASN / 云服务", "CDN"]

    def __init__(self):
        super().__init__()
        self.setWindowTitle("IPQuery")
        self.setWindowIcon(_get_embedded_icon())
        self.resize(1120, 780)
        self.setMinimumSize(920, 600)

        # 数据库默认路径:
        #   macOS .app 打包 → ~/Library/Application Support/IPQuery/db/
        #   其他情况 → 脚本所在目录
        _script_dir = os.path.dirname(os.path.abspath(sys.argv[0]))
        if sys.platform == "darwin" and _script_dir.endswith(".app/Contents/MacOS"):
            self.default_db_dir = os.path.join(
                os.path.expanduser("~/Library/Application Support"),
                "IPQuery", "db"
            )
        else:
            self.default_db_dir = _script_dir

        self.worker: Optional[WorkerThread] = None
        self.db_thread: Optional[DbUpdateThread] = None
        self.all_results: list[list] = []

        self._check_dependencies()
        self._init_ui()
        self._check_databases()

    # ==================== UI ====================

    def _init_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(16, 12, 16, 12)
        main_layout.setSpacing(12)

        # ---- 输入区 ----
        input_group = QGroupBox("📥 输入（每行一个域名或 IP，支持带协议头的 URL）")
        input_layout = QVBoxLayout(input_group)

        self.input_text = QTextEdit()
        self.input_text.setPlaceholderText(
            "每行一个，支持以下格式：\n"
            "  · 域名      www.example.com\n"
            "  · 完整 URL  http://www.example.com/path\n"
            "  · IPv4      1.1.1.1\n"
            "  · IPv6      2606:4700:4700::1111"
        )
        self.input_text.setMaximumHeight(130)
        input_layout.addWidget(self.input_text)
        main_layout.addWidget(input_group)

        # ---- 设置行 ----
        mid_row = QHBoxLayout()
        mid_row.setSpacing(12)

        # DNS
        dns_group = QGroupBox("🔍 DNS 解析设置")
        dns_layout = QVBoxLayout(dns_group)

        self.btn_system_dns = QRadioButton("系统 DNS")
        self.btn_custom_dns = QRadioButton("自定义 DNS")
        self.btn_doh_dns = QRadioButton("DoH (DNS over HTTPS)")
        self.btn_system_dns.setChecked(True)

        dns_mode_group = QButtonGroup(self)
        dns_mode_group.addButton(self.btn_system_dns, 0)
        dns_mode_group.addButton(self.btn_custom_dns, 1)
        dns_mode_group.addButton(self.btn_doh_dns, 2)
        dns_mode_group.buttonClicked.connect(self._on_dns_mode_changed)

        dns_layout.addWidget(self.btn_system_dns)
        dns_layout.addWidget(self.btn_custom_dns)
        dns_layout.addWidget(self.btn_doh_dns)

        self.custom_dns_input = QLineEdit()
        self.custom_dns_input.setPlaceholderText("用逗号分隔，例如: 8.8.8.8, 223.5.5.5")
        self.custom_dns_input.setText(", ".join(DEFAULT_CUSTOM_DNS))
        self.custom_dns_input.setEnabled(False)
        dns_layout.addWidget(self.custom_dns_input)

        self.doh_url_input = QLineEdit()
        self.doh_url_input.setPlaceholderText("DoH 接口地址")
        self.doh_url_input.setText(DnsResolver.DEFAULT_DOH_URLS[0])
        self.doh_url_input.setEnabled(False)

        self.doh_preset = QComboBox()
        self.doh_preset.addItems(DnsResolver.DEFAULT_DOH_URLS)
        self.doh_preset.setCurrentIndex(0)
        self.doh_preset.setEnabled(False)
        self.doh_preset.currentTextChanged.connect(
            lambda url: self.doh_url_input.setText(url)
        )

        doh_row = QHBoxLayout()
        doh_row.addWidget(self.doh_url_input, 1)
        doh_row.addWidget(self.doh_preset)
        dns_layout.addLayout(doh_row)

        mid_row.addWidget(dns_group, 2)

        # 数据库
        db_group = QGroupBox("🗄️ 数据库路径（需包含 4 个文件）")
        db_layout = QVBoxLayout(db_group)

        db_row = QHBoxLayout()
        self.db_path_input = QLineEdit()
        self.db_path_input.setText(self.default_db_dir)
        self.db_path_input.setPlaceholderText("数据库文件所在目录（需包含 GeoLite2 三件套 + qqwry.dat）")
        db_row.addWidget(self.db_path_input)

        btn_browse = QPushButton("浏览...")
        btn_browse.setObjectName("btnBrowseDb")
        btn_browse.clicked.connect(self._browse_db_dir)
        btn_browse.setFixedWidth(90)
        db_row.addWidget(btn_browse)
        db_layout.addLayout(db_row)

        self.cdn_check = QCheckBox("启用 CDN 检测")
        self.cdn_check.setChecked(True)
        db_layout.addWidget(self.cdn_check)

        # 数据库状态标签
        self.db_status_label = QLabel("")
        self.db_status_label.setStyleSheet("font-size: 11px;")
        db_layout.addWidget(self.db_status_label)

        mid_row.addWidget(db_group, 3)
        main_layout.addLayout(mid_row)

        # ---- 按钮 ----
        btn_row = QHBoxLayout()
        btn_row.setSpacing(10)

        self.btn_query = QPushButton("🔎 开始查询")
        self.btn_query.setObjectName("btnQuery")
        self.btn_query.clicked.connect(self._start_query)
        self.btn_query.setMinimumHeight(36)
        btn_row.addWidget(self.btn_query)

        self.btn_stop = QPushButton("⏹ 停止")
        self.btn_stop.clicked.connect(self._stop_query)
        self.btn_stop.setMinimumHeight(36)
        self.btn_stop.setEnabled(False)
        self.btn_stop.setStyleSheet(
            "QPushButton { background-color: #e74c3c; color: white; border-radius: 6px;"
            " padding: 8px 20px; font-size: 13px; border: none; }"
            "QPushButton:hover { background-color: #c0392b; }"
        )
        btn_row.addWidget(self.btn_stop)
        btn_row.addStretch()

        self.btn_update_db = QPushButton("🔄 更新数据库")
        self.btn_update_db.setObjectName("btnUpdateDb")
        self.btn_update_db.clicked.connect(self._update_database)
        self.btn_update_db.setMinimumHeight(36)
        btn_row.addWidget(self.btn_update_db)

        self.btn_clear = QPushButton("清空输出")
        self.btn_clear.setObjectName("btnClear")
        self.btn_clear.clicked.connect(self._clear_output)
        self.btn_clear.setMinimumHeight(36)
        btn_row.addWidget(self.btn_clear)

        self.btn_export = QPushButton("📤 导出 CSV")
        self.btn_export.setObjectName("btnExport")
        self.btn_export.clicked.connect(self._export_csv)
        self.btn_export.setMinimumHeight(36)
        btn_row.addWidget(self.btn_export)

        main_layout.addLayout(btn_row)

        # ---- 进度 ----
        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
        main_layout.addWidget(self.progress_bar)

        self.status_label = QLabel("就绪")
        self.status_label.setStyleSheet("font-size: 12px; color: #636e72;")
        main_layout.addWidget(self.status_label)

        # ---- 结果表格 ----
        result_group = QGroupBox("📊 查询结果")
        result_layout = QVBoxLayout(result_group)

        self.result_table = QTableWidget()
        self.result_table.setColumnCount(len(self.COLUMNS))
        self.result_table.setHorizontalHeaderLabels(self.COLUMNS)
        self.result_table.setAlternatingRowColors(True)
        self.result_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.result_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)

        header = self.result_table.horizontalHeader()
        for col in (2, 3, 4, 7):
            header.setSectionResizeMode(col, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(6, QHeaderView.ResizeMode.Stretch)
        for col in (0, 1):
            header.setSectionResizeMode(col, QHeaderView.ResizeMode.Interactive)

        self.result_table.setColumnWidth(0, 180)
        self.result_table.setColumnWidth(1, 200)

        result_layout.addWidget(self.result_table)
        main_layout.addWidget(result_group, 1)

        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("就绪 — 请输入域名或 IP 后点击「开始查询」")

    # ==================== 槽函数 ====================

    def _on_dns_mode_changed(self, btn):
        self.custom_dns_input.setEnabled(btn == self.btn_custom_dns)
        self.doh_url_input.setEnabled(btn == self.btn_doh_dns)
        self.doh_preset.setEnabled(btn == self.btn_doh_dns)

    def _browse_db_dir(self):
        path = QFileDialog.getExistingDirectory(
            self, "选择数据库目录", self.db_path_input.text()
        )
        if path:
            self.db_path_input.setText(path)
            self._check_databases()

    def _check_dependencies(self):
        """检查第三方依赖是否齐全，缺少时弹出带复制按钮的提示框"""
        missing_pkgs = []
        if geoip2 is None:
            missing_pkgs.append("geoip2")
        if dns is None:
            missing_pkgs.append("dnspython")
        if requests is None:
            missing_pkgs.append("requests")
        if QQwryReader is None:
            missing_pkgs.append("qqwry-py3")

        if not missing_pkgs:
            return

        pip_cmd = f"pip install {' '.join(missing_pkgs)}"

        dialog = QDialog(self)
        dialog.setWindowTitle("缺少依赖")
        dialog.setMinimumWidth(480)
        dialog.setModal(True)

        layout = QVBoxLayout(dialog)
        layout.setSpacing(12)

        msg = QLabel(
            f"检测到以下 Python 依赖库未安装：\n"
            + "\n".join(f"  · {pkg}" for pkg in missing_pkgs)
            + "\n\n请打开终端（CMD）执行以下命令安装："
        )
        msg.setWordWrap(True)
        msg.setStyleSheet("font-size: 13px; color: #2d3436;")
        layout.addWidget(msg)

        cmd_label = QLabel(pip_cmd)
        cmd_label.setStyleSheet(
            "font-size: 13px; font-family: monospace; background-color: #ecf0f1;"
            " padding: 10px; border-radius: 4px; color: #2c3e50;"
        )
        cmd_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        layout.addWidget(cmd_label)

        btn_row = QHBoxLayout()
        btn_copy = QPushButton("📋 复制命令")
        btn_copy.setStyleSheet(
            "QPushButton { background-color: #3498db; color: white; border-radius: 6px;"
            " padding: 8px 20px; font-size: 13px; border: none; }"
            "QPushButton:hover { background-color: #2980b9; }"
        )
        btn_copy.clicked.connect(lambda: self._copy_pip_cmd(pip_cmd, dialog))

        btn_exit = QPushButton("退出程序")
        btn_exit.setStyleSheet(
            "QPushButton { background-color: #95a5a6; color: white; border-radius: 6px;"
            " padding: 8px 20px; font-size: 13px; border: none; }"
            "QPushButton:hover { background-color: #7f8c8d; }"
        )
        btn_exit.clicked.connect(sys.exit)

        btn_row.addWidget(btn_copy)
        btn_row.addStretch()
        btn_row.addWidget(btn_exit)
        layout.addLayout(btn_row)

        dialog.exec()

    @staticmethod
    def _copy_pip_cmd(cmd: str, dialog: QDialog):
        clip = QApplication.clipboard()
        clip.setText(cmd)
        # 给"复制"按钮添加短暂反馈
        for btn in dialog.findChildren(QPushButton):
            if btn.text() == "📋 复制命令":
                btn.setText("✅ 已复制")
                btn.setStyleSheet(
                    "QPushButton { background-color: #27ae60; color: white;"
                    " border-radius: 6px; padding: 8px 20px; font-size: 13px; border: none; }"
                )
                break

    def _check_databases(self):
        """检查全部 4 个数据库文件是否存在，并更新状态标签"""
        db_dir = self.db_path_input.text()
        os.makedirs(db_dir, exist_ok=True)  # 首次运行时自动创建目录
        present = []
        missing = []
        for name, filename, _ in DB_FILES_CONFIG:
            filepath = os.path.join(db_dir, filename)
            exists = os.path.exists(filepath)
            if exists:
                size_mb = os.path.getsize(filepath) / 1024 / 1024
                present.append(f"{name} ({size_mb:.1f} MB)")
            else:
                missing.append(name)

        if not missing:
            self.status_label.setText(f"✅ 全部 {len(DB_FILES_CONFIG)} 个数据库文件完整")
            self.status_label.setStyleSheet("font-size: 12px; color: #27ae60;")
            self.db_status_label.setText(" | ".join(present))
            self.db_status_label.setStyleSheet("font-size: 11px; color: #27ae60;")
        else:
            missing_names = [m for m, _, _ in DB_FILES_CONFIG if m in missing]
            self.status_label.setText(
                f"⚠ 缺少数据库: {' / '.join(missing)} — 请点击「更新数据库」下载"
            )
            self.status_label.setStyleSheet("font-size: 12px; color: #e67e22;")
            self.db_status_label.setText(
                f"✅ {' | '.join(present)}  ⚠ 缺少: {' / '.join(missing)}"
            )
            self.db_status_label.setStyleSheet("font-size: 11px; color: #e67e22;")

    def _start_query(self):
        text = self.input_text.toPlainText().strip()
        if not text:
            QMessageBox.warning(self, "提示", "请先输入域名或 IP 地址。")
            return

        db_dir = self.db_path_input.text()

        # 构建文件路径并检查完整性
        db_paths = {}
        missing = []
        for name, filename, _ in DB_FILES_CONFIG:
            filepath = os.path.join(db_dir, filename)
            db_paths[name] = filepath
            if not os.path.exists(filepath):
                missing.append(name)

        if missing:
            QMessageBox.critical(
                self, "数据库缺失",
                f"以下数据库文件不存在：\n  " + "\n  ".join(missing) +
                "\n\n请点击「更新数据库」按钮自动下载全部 4 个文件。"
            )
            return

        if geoip2 is None:
            QMessageBox.critical(self, "缺少依赖", "请安装 geoip2: pip install geoip2")
            return
        if dns is None:
            QMessageBox.critical(self, "缺少依赖", "请安装 dnspython: pip install dnspython")
            return

        inputs = [line.strip() for line in text.split("\n") if line.strip()]

        dns_mode = "custom" if self.btn_custom_dns.isChecked() else \
                   "doh" if self.btn_doh_dns.isChecked() else "system"
        custom_dns_list = [
            s.strip() for s in self.custom_dns_input.text().split(",") if s.strip()
        ]
        doh_url = self.doh_url_input.text().strip() or DnsResolver.DEFAULT_DOH_URLS[0]

        self.result_table.setRowCount(0)
        self.all_results = []

        self.btn_query.setEnabled(False)
        self.btn_stop.setEnabled(True)
        self.input_text.setEnabled(False)
        self.progress_bar.setValue(0)

        self.worker = WorkerThread(
            inputs=inputs,
            dns_mode=dns_mode,
            custom_dns=custom_dns_list,
            doh_url=doh_url,
            country_db=db_paths["Country"],
            city_db=db_paths["City"],
            asn_db=db_paths["ASN"],
            qqwry_path=db_paths["纯真IP"],
            detect_cdn=self.cdn_check.isChecked(),
        )
        self.worker.progress.connect(self._on_progress)
        self.worker.status.connect(self._on_status)
        self.worker.result.connect(self._on_result)
        self.worker.error.connect(self._on_worker_error)
        self.worker.finished.connect(self._on_finished)
        self.worker.start()

    def _stop_query(self):
        if self.worker and self.worker.isRunning():
            self.worker.cancel()
            self.status_label.setText("正在停止...")
            self.status_label.setStyleSheet("font-size: 12px; color: #e74c3c;")

    def _on_progress(self, current, total):
        self.progress_bar.setMaximum(total)
        self.progress_bar.setValue(current)
        self.status_bar.showMessage(f"处理中... {current}/{total}")

    def _on_status(self, msg):
        self.status_label.setText(msg)

    def _on_worker_error(self, msg):
        QMessageBox.critical(self, "查询异常", msg)
        self.btn_query.setEnabled(True)
        self.btn_stop.setEnabled(False)
        self.input_text.setEnabled(True)
        self.status_label.setText(f"❌ {msg.split(chr(10))[0]}")
        self.status_label.setStyleSheet("font-size: 12px; color: #e74c3c;")

    def _on_result(self, row: list):
        """
        row = [来源, IP, 国家, 省份, 城市, lat, lon, asn_org, is_cdn]
        表格显示 = [来源, IP, 国家, 省份, 城市, 经/纬度, asn_org, is_cdn]
        """
        self.all_results.append(row)

        table_row = self.result_table.rowCount()
        self.result_table.insertRow(table_row)

        lat_lon = ""
        if len(row) > 6 and row[5] and row[6]:
            lat_lon = f"{row[5]}, {row[6]}"

        display = [
            row[0],
            row[1],
            row[2],
            row[3],
            row[4],
            lat_lon,
            row[7] if len(row) > 7 else "",
            row[8] if len(row) > 8 else "",
        ]

        for col, val in enumerate(display):
            item = QTableWidgetItem(str(val))
            if col >= 2:
                item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            else:
                item.setTextAlignment(
                    Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter
                )

            if col == 7 and val == "是":
                item.setForeground(QColor("#e67e22"))
                item.setFont(QFont(self.font().family(), -1, QFont.Weight.Bold))
            if col == 1 and (val == "解析失败" or val == ""):
                item.setForeground(QColor("#e74c3c"))

            self.result_table.setItem(table_row, col, item)

        self.result_table.scrollToBottom()

    def _on_finished(self):
        self.btn_query.setEnabled(True)
        self.btn_stop.setEnabled(False)
        self.input_text.setEnabled(True)
        self.progress_bar.setValue(self.progress_bar.maximum())

        count = self.result_table.rowCount()
        if count == 0 and self.worker is not None:
            # 线程正常结束但零条结果 → 静默失败，提示用户
            self.status_label.setText("⚠ 查询结束但无结果，请检查控制台输出或重试")
            self.status_label.setStyleSheet("font-size: 12px; color: #e67e22;")
            self.status_bar.showMessage("无结果 — 可能 DNS 解析全部失败或数据库路径异常")
        else:
            success = sum(1 for r in self.all_results if r[1] != "解析失败")
            self.status_bar.showMessage(
                f"完成 — 共 {count} 条结果，其中 {success} 条查询成功"
            )
            self.status_label.setText(f"✅ 查询完成 — {count} 条记录")
            self.status_label.setStyleSheet("font-size: 12px; color: #27ae60;")
        self.worker = None

    def _clear_output(self):
        self.result_table.setRowCount(0)
        self.all_results = []
        self.progress_bar.setValue(0)
        self.status_bar.showMessage("就绪")
        self.status_label.setText("就绪")
        self.status_label.setStyleSheet("font-size: 12px; color: #636e72;")
        self._check_databases()

    def _export_csv(self):
        if not self.all_results:
            QMessageBox.information(self, "提示", "没有可导出的数据。")
            return

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        default_name = f"ips_result_{timestamp}.csv"

        path, _ = QFileDialog.getSaveFileName(
            self, "导出 CSV", default_name, "CSV 文件 (*.csv)"
        )
        if not path:
            return

        try:
            with open(path, "w", newline="", encoding="utf-8-sig") as f:
                writer = csv.writer(f)
                writer.writerow([
                    "来源", "IP地址", "国家", "省份", "城市",
                    "纬度", "经度", "ASN/云服务", "是否CDN"
                ])
                for row in self.all_results:
                    writer.writerow(row)
            self.status_bar.showMessage(f"已导出: {os.path.basename(path)}")
            QMessageBox.information(self, "导出完成", f"结果已保存到:\n{path}")
        except Exception as e:
            QMessageBox.critical(self, "导出失败", str(e))

    def _update_database(self):
        if requests is None:
            QMessageBox.critical(
                self, "缺少依赖", "请安装 requests: pip install requests"
            )
            return

        db_dir = self.db_path_input.text()
        if not os.path.isdir(db_dir):
            QMessageBox.critical(self, "路径无效", f"目录不存在:\n{db_dir}")
            return

        reply = QMessageBox.question(
            self, "确认更新",
            f"将从以下源下载全部 4 个数据库文件到:\n{db_dir}\n\n"
            + "\n".join(f"  · {name}: {filename}" for name, filename, _ in DB_FILES_CONFIG)
            + "\n\n是否继续？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        self.btn_update_db.setEnabled(False)
        self.btn_query.setEnabled(False)
        self.progress_bar.setValue(0)

        self.db_thread = DbUpdateThread(db_dir)
        self.db_thread.progress_text.connect(self._on_db_progress_text)
        self.db_thread.progress_percent.connect(self._on_db_progress_pct)
        self.db_thread.finished.connect(self._on_db_finished)
        self.db_thread.start()

    def _on_db_progress_text(self, msg):
        self.status_label.setText(msg)

    def _on_db_progress_pct(self, pct):
        self.progress_bar.setValue(pct)

    def _on_db_finished(self, success, message):
        self.btn_update_db.setEnabled(True)
        self.btn_query.setEnabled(True)
        self.progress_bar.setValue(100 if success else 0)
        if success:
            self.status_label.setText(f"✅ {message}")
            self.status_label.setStyleSheet("font-size: 12px; color: #27ae60;")
            self._check_databases()
        else:
            self.status_label.setText(f"❌ {message}")
            self.status_label.setStyleSheet("font-size: 12px; color: #e74c3c;")
        QMessageBox.information(
            self, "更新结果" if success else "更新失败", message
        )
        self.db_thread = None


# ============================================================================
# 入口
# ============================================================================
def main():
    app = QApplication(sys.argv)
    app.setStyleSheet(STYLE_QSS)

    if sys.platform == "darwin":
        app.setAttribute(Qt.ApplicationAttribute.AA_DontShowIconsInMenus, False)

    window = IPLookupWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
