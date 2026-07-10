#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
IPQuery — Cross-platform IP geolocation tool with GUI
DNS: system / custom / DoH  |  DB: GeoLite2 + QQWry  |  CDN detection
Downloads: P3TERX/GeoLite.mmdb + out0fmemory/qqwry.dat
"""

import os
import sys
import csv
import socket
import time
import traceback
import subprocess
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

try: import geoip2.database
except ImportError: geoip2 = None

try: import dns.resolver
except ImportError: dns = None

try: import requests
except ImportError: requests = None

try: from qqwry import QQwry as QQwryReader
except ImportError: QQwryReader = None

# ============================================================================
# Constants
# ============================================================================
DB_FILES_CONFIG = [
    ("Country", "GeoLite2-Country.mmdb",
     "https://gh-proxy.org/https://github.com/P3TERX/GeoLite.mmdb/raw/download/GeoLite2-Country.mmdb"),
    ("City", "GeoLite2-City.mmdb",
     "https://gh-proxy.org/https://github.com/P3TERX/GeoLite.mmdb/raw/download/GeoLite2-City.mmdb"),
    ("ASN", "GeoLite2-ASN.mmdb",
     "https://gh-proxy.org/https://github.com/P3TERX/GeoLite.mmdb/raw/download/GeoLite2-ASN.mmdb"),
    ("纯真IP", "qqwry.dat",
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
DNS_DELAY_SEC = 0.15
DNS_RETRY_MAX = 3
DNS_RETRY_BASE_DELAY = 0.8

# ============================================================================
# Stylesheet
# ============================================================================
STYLE_QSS = """
QMainWindow { background-color: #f5f6fa; }
QGroupBox { font-size: 13px; font-weight: bold; color: #2c3e50; border: 1px solid #dcdde1; border-radius: 8px; margin-top: 14px; padding-top: 18px; background-color: #ffffff; }
QGroupBox::title { subcontrol-origin: margin; left: 14px; padding: 4px 12px; background-color: #ffffff; border: 1px solid #dcdde1; border-radius: 6px; }
QTextEdit, QLineEdit { border: 1px solid #dcdde1; border-radius: 6px; padding: 8px; font-size: 13px; background-color: #ffffff; color: #2d3436; }
QTextEdit:focus, QLineEdit:focus { border-color: #3498db; }
QPushButton { border-radius: 6px; padding: 8px 20px; font-size: 13px; font-weight: 500; border: none; }
QPushButton#btnQuery { background-color: #3498db; color: white; }
QPushButton#btnQuery:hover { background-color: #2980b9; }
QPushButton#btnClear { background-color: #95a5a6; color: white; }
QPushButton#btnClear:hover { background-color: #7f8c8d; }
QPushButton#btnExport { background-color: #27ae60; color: white; }
QPushButton#btnExport:hover { background-color: #219a52; }
QPushButton#btnUpdateDb { background-color: #e67e22; color: white; }
QPushButton#btnUpdateDb:hover { background-color: #d35400; }
QPushButton#btnBrowseDb { background-color: #ecf0f1; color: #2c3e50; border: 1px solid #bdc3c7; }
QPushButton#btnBrowseDb:hover { background-color: #d5dbdb; }
QTableWidget { border: 1px solid #dcdde1; border-radius: 6px; background-color: #ffffff; gridline-color: #ecf0f1; font-size: 12px; alternate-background-color: #f8f9fa; }
QTableWidget::item { padding: 6px; }
QHeaderView::section { background-color: #2c3e50; color: white; padding: 8px; border: none; font-weight: bold; font-size: 12px; }
QProgressBar { border: none; border-radius: 4px; background-color: #ecf0f1; text-align: center; font-size: 11px; height: 20px; }
QProgressBar::chunk { background-color: #3498db; border-radius: 4px; }
QStatusBar { font-size: 12px; color: #636e72; }
QRadioButton, QCheckBox { font-size: 13px; color: #2d3436; spacing: 6px; }
QLabel { color: #2c3e50; }
"""


# ============================================================================
# Embedded icon
# ============================================================================
def _get_embedded_icon():
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
# Input normalization
# ============================================================================
def normalize_input(raw: str) -> str:
    text = raw.strip()
    if is_ip_address(text):
        return text
    if "://" in text:
        p = urlparse(text)
        if p.hostname:
            text = p.hostname
            if is_ip_address(text): return text
            return text
    if "/" in text:
        text = text.split("/", 1)[0]
    if is_ip_address(text):
        return text
    if text.startswith("[") and "]" in text:
        text = text.split("]", 1)[0].strip("[]")
    if is_ip_address(text):
        return text
    if ":" in text:
        parts = text.rsplit(":", 1)
        if len(parts) == 2 and parts[-1].isdigit():
            text = parts[0]
    return text.strip()


def is_ip_address(s: str) -> bool:
    if not s: return False
    try: socket.inet_pton(socket.AF_INET, s); return True
    except: pass
    try: socket.inet_pton(socket.AF_INET6, s); return True
    except: pass
    return False


# ============================================================================
# Ping / tcping fallback
# ============================================================================
def resolve_via_ping(domain: str) -> set[str]:
    """Try to get IP via system ping, gethostbyname, and TCP connect."""
    ips: set[str] = set()

    # 1) socket.gethostbyname (system resolver)
    try:
        ips.add(socket.gethostbyname(domain))
    except Exception:
        pass

    # 2) system ping command
    try:
        if sys.platform == "win32":
            r = subprocess.run(
                ["ping", "-n", "1", "-w", "2000", domain],
                capture_output=True, text=True, timeout=4
            )
        else:
            r = subprocess.run(
                ["ping", "-c", "1", "-W", "1", domain],
                capture_output=True, text=True, timeout=4
            )
        import re
        for match in re.finditer(r"\b(?:\d{1,3}\.){3}\d{1,3}\b", r.stdout):
            try:
                socket.inet_pton(socket.AF_INET, match.group())
                ips.add(match.group())
            except Exception:
                pass
    except Exception:
        pass

    # 3) TCP connect to port 80 / 443
    for port in (80, 443):
        try:
            addr = socket.getaddrinfo(domain, port, socket.AF_INET, socket.SOCK_STREAM)
            for _, _, _, _, sockaddr in addr:
                s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                s.settimeout(2)
                if s.connect_ex(sockaddr) == 0:
                    ips.add(sockaddr[0])
                s.close()
        except Exception:
            pass

    return ips


# ============================================================================
# DNS resolver
# ============================================================================
class DnsResolver:
    MODE_SYSTEM = "system"
    MODE_CUSTOM = "custom"
    MODE_DOH = "doh"

    DEFAULT_DOH_URLS = [
        "https://cloudflare-dns.com/dns-query",
        "https://dns.google/dns-query",
        "https://dns.alidns.com/dns-query",
        "https://dns.quad9.net/dns-query",
    ]

    def __init__(self, mode="system", custom_servers=None, doh_url=None):
        self.mode = mode
        self.custom_servers = custom_servers or []
        self.doh_url = doh_url or self.DEFAULT_DOH_URLS[0]
        self._resolver = None
        if mode == self.MODE_CUSTOM and self.custom_servers:
            self._resolver = dns.resolver.Resolver(configure=False)
            self._resolver.nameservers = self.custom_servers
            self._resolver.cache = dns.resolver.LRUCache(0)
            self._resolver.timeout = 5
            self._resolver.lifetime = 5
        elif mode == self.MODE_SYSTEM:
            self._resolver = dns.resolver.Resolver()
            self._resolver.cache = dns.resolver.LRUCache(0)
            self._resolver.timeout = 5
            self._resolver.lifetime = 5

    def resolve(self, domain: str) -> set[str]:
        if self.mode == self.MODE_DOH:
            return self._resolve_doh(domain)
        return self._resolve_standard(domain)

    def _resolve_standard(self, domain: str) -> set[str]:
        ips: set[str] = set()
        for rt in ("A", "AAAA"):
            try:
                for rdata in self._resolver.resolve(domain, rt):
                    ips.add(rdata.to_text())
            except Exception:
                pass
        return ips

    def _resolve_doh(self, domain: str) -> set[str]:
        import dns.message, dns.rdatatype
        ips: set[str] = set()
        for rdtype in (dns.rdatatype.A, dns.rdatatype.AAAA):
            try:
                q = dns.message.make_query(domain, rdtype)
                r = requests.post(self.doh_url, data=q.to_wire(),
                                  headers={"Content-Type": "application/dns-message"}, timeout=5)
                r.raise_for_status()
                ans = dns.message.from_wire(r.content)
                for rrset in ans.answer:
                    if rrset.rdtype in (dns.rdatatype.A, dns.rdatatype.AAAA):
                        for rd in rrset: ips.add(rd.to_text())
            except Exception:
                pass
        return ips

    @staticmethod
    def resolve_with_retry(domain, resolver, retries=DNS_RETRY_MAX):
        for attempt in range(1, retries + 1):
            ips = resolver.resolve(domain)
            if ips: return ips
            if attempt < retries: time.sleep(DNS_RETRY_BASE_DELAY * attempt)
        return set()


# ============================================================================
# Windows path compat
# ============================================================================
def _ensure_ascii_path(filepath: str) -> str:
    if sys.platform != "win32":
        return filepath
    try:
        filepath.encode("ascii")
        return filepath
    except UnicodeEncodeError:
        pass
    import shutil
    cache_dir = os.path.join(os.environ.get("TEMP", os.path.expanduser("~")), "IPQuery_db")
    os.makedirs(cache_dir, exist_ok=True)
    cached = os.path.join(cache_dir, os.path.basename(filepath))
    if not os.path.exists(cached) or os.path.getmtime(filepath) > os.path.getmtime(cached):
        shutil.copy2(filepath, cached)
    return cached


# ============================================================================
# GeoIP Engine
# ============================================================================
class GeoIPEngine:
    LOCALE_FALLBACK = ["zh-CN", "en"]

    def __init__(self, country_db, city_db, asn_db, qqwry_path=None, detect_cdn=True):
        self.detect_cdn = detect_cdn
        self._reader_country = geoip2.database.Reader(_ensure_ascii_path(country_db))
        self._reader_city = geoip2.database.Reader(_ensure_ascii_path(city_db))
        self._reader_asn = geoip2.database.Reader(_ensure_ascii_path(asn_db))
        self._qqwry = None
        if QQwryReader is not None and qqwry_path and os.path.exists(qqwry_path):
            try:
                qq = QQwryReader()
                if qq.load_file(qqwry_path): self._qqwry = qq
            except Exception: pass

    def close(self):
        self._reader_country.close(); self._reader_city.close(); self._reader_asn.close()

    @staticmethod
    def _safe_name(names, locales):
        for loc in locales:
            v = names.get(loc, "")
            if v: return v
        return ""

    def _qqwry_lookup(self, ip):
        if not self._qqwry or not self._qqwry.is_loaded(): return "", ""
        if ":" in ip: return "", ""
        try:
            f1, f2 = self._qqwry.lookup(ip)
            if not f1: return "", ""
            f1 = f1.strip()
            if "省" in f1:
                idx = f1.index("省")
                p = f1[:idx + 1]; r = f1[idx + 1:]
                c = r if r.endswith("市") else ""
                return p, c
            if f1.endswith("市"): return f1, f1
            if f1.endswith("省"): return f1, ""
            return "", ""
        except Exception: return "", ""

    def lookup(self, ip):
        country = province = city_name = lat = lon = ""
        try:
            cr = self._reader_city.city(ip)
            country = self._safe_name(cr.country.names or {}, self.LOCALE_FALLBACK)
            subs = cr.subdivisions
            if subs and len(subs) > 0:
                province = self._safe_name(subs.most_specific.names or {}, self.LOCALE_FALLBACK)
            city_name = self._safe_name(cr.city.names or {}, self.LOCALE_FALLBACK)
            if cr.location.latitude is not None: lat = str(cr.location.latitude)
            if cr.location.longitude is not None: lon = str(cr.location.longitude)
        except geoip2.errors.AddressNotFoundError:
            try: country = self._safe_name(self._reader_country.country(ip).country.names or {}, self.LOCALE_FALLBACK)
            except Exception: pass
        except Exception:
            try: country = self._safe_name(self._reader_country.country(ip).country.names or {}, self.LOCALE_FALLBACK)
            except Exception: pass

        if (not province or not city_name) and self._qqwry is not None:
            qp, qc = self._qqwry_lookup(ip)
            if not province and qp: province = qp
            if not city_name and qc: city_name = qc
            if (province or city_name) and not country: country = "中国"

        asn_org = ""
        try: asn_org = self._reader_asn.asn(ip).autonomous_system_organization or ""
        except Exception: pass

        is_cdn = False
        if self.detect_cdn:
            al = asn_org.lower()
            is_cdn = any(k.lower() in al for k in CDN_ASN_KEYWORDS)
            if is_cdn and not country: country = "CDN"

        return (country, province, city_name, lat, lon, asn_org, "是" if is_cdn else "否")


# ============================================================================
# Worker thread
# ============================================================================
class WorkerThread(QThread):
    progress = pyqtSignal(int, int)
    status = pyqtSignal(str)
    result = pyqtSignal(list)
    error = pyqtSignal(str)
    finished = pyqtSignal()

    def __init__(self, inputs, dns_mode, custom_dns, doh_url,
                 country_db, city_db, asn_db, qqwry_path=None,
                 detect_cdn=True, first_only=False):
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
        self.first_only = first_only
        self._cancelled = False

    def cancel(self): self._cancelled = True

    def run(self):
        try: self._do_run()
        except Exception as e:
            tb = traceback.format_exc()
            print(f"[IPQuery FATAL] {e}\n{tb}", file=sys.stderr, flush=True)
            self.error.emit(f"查询异常:\n{tb}")

    def _do_run(self):
        # --- Stage 0: preprocess ---
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

        # --- Stage 1: DNS resolve ---
        self.status.emit("阶段 2/3: DNS 解析...")
        dns_resolver = DnsResolver(
            mode=self.dns_mode,
            custom_servers=self.custom_dns if self.dns_mode == DnsResolver.MODE_CUSTOM else None,
            doh_url=self.doh_url if self.dns_mode == DnsResolver.MODE_DOH else None,
        )

        # (raw_src, ip, remark)
        all_entries: list[tuple[str, str, str]] = []
        total = len(hosts)
        for i, (raw_src, host) in enumerate(hosts):
            if self._cancelled: self.finished.emit(); return
            self.progress.emit(i + 1, total)

            if is_ip_address(host):
                all_entries.append((raw_src, host, ""))
                continue

            ips = DnsResolver.resolve_with_retry(host, dns_resolver)
            if ips:
                ip_list = sorted(ips)
                if self.first_only:
                    all_entries.append((raw_src, ip_list[0], ""))
                else:
                    for ip in ip_list:
                        all_entries.append((raw_src, ip, ""))
            else:
                # Ping fallback
                fallback = resolve_via_ping(host)
                if fallback:
                    ip_list = sorted(fallback)
                    if self.first_only:
                        all_entries.append((raw_src, ip_list[0], "Ping获取"))
                    else:
                        for ip in ip_list:
                            all_entries.append((raw_src, ip, "Ping获取"))
                else:
                    all_entries.append((raw_src, "解析失败", "DNS+Ping失败"))

            if i < total - 1: time.sleep(DNS_DELAY_SEC)

        resolved = sum(1 for _, ip, _ in all_entries if ip != "解析失败")
        self.status.emit(f"解析完成: {resolved}/{len(all_entries)}")

        # --- Stage 2: GeoIP lookup (no dedup, preserve input order) ---
        if self._cancelled: self.finished.emit(); return

        self.status.emit("阶段 3/3: 归属地查询...")
        try:
            engine = GeoIPEngine(
                country_db=self.country_db, city_db=self.city_db, asn_db=self.asn_db,
                qqwry_path=self.qqwry_path, detect_cdn=self.detect_cdn,
            )
        except Exception as e:
            self.status.emit(f"打开数据库失败: {e}")
            print(f"[IPQuery ERROR] DB open failed: {e}", file=sys.stderr)
            self.finished.emit(); return

        total_rows = len(all_entries)
        for idx, (src, ip, remark) in enumerate(all_entries):
            if self._cancelled: break
            if ip == "解析失败":
                row = [src, ip, "", "", "", "", "", "", "否", remark]
                self.result.emit(row)
                self.progress.emit(idx + 1, total_rows)
                continue

            try:
                geo_result = engine.lookup(ip)
                row = [src, ip] + list(geo_result) + [remark]
            except Exception:
                row = [src, ip, "查询失败", "", "", "", "", "", "否", "归属地查询异常"]

            self.result.emit(row)
            self.progress.emit(idx + 1, total_rows)

        engine.close()
        self.status.emit("查询完成")
        self.finished.emit()


# ============================================================================
# DB update thread
# ============================================================================
class DbUpdateThread(QThread):
    progress_text = pyqtSignal(str)
    progress_percent = pyqtSignal(int)
    finished = pyqtSignal(bool, str)

    def __init__(self, db_dir): super().__init__(); self.db_dir = db_dir

    def run(self):
        if requests is None:
            self.finished.emit(False, "缺少 requests 库"); return
        total = len(DB_FILES_CONFIG)
        for idx, (name, filename, url) in enumerate(DB_FILES_CONFIG):
            fp = os.path.join(self.db_dir, filename)
            self.progress_text.emit(f"正在下载 {filename} ({name})...")
            try:
                r = requests.get(url, timeout=120, stream=True); r.raise_for_status()
                ts = int(r.headers.get("content-length", 0)); dl = 0
                with open(fp, "wb") as f:
                    for chunk in r.iter_content(8192):
                        f.write(chunk); dl += len(chunk)
                        if ts > 0: self.progress_percent.emit(int(dl / ts * 100))
                self.progress_text.emit(f"{filename} 下载完成")
                self.progress_percent.emit(int((idx + 1) / total * 100))
            except Exception as e:
                self.finished.emit(False, f"下载 {filename} 失败: {e}"); return
        self.finished.emit(True, "全部 4 个数据库更新完成！")


# ============================================================================
# Main window
# ============================================================================
class IPLookupWindow(QMainWindow):
    COLUMNS = ["来源", "IP 地址", "国家", "省份", "城市", "经/纬度", "ASN / 云服务", "CDN", "备注"]

    def __init__(self):
        super().__init__()
        self.setWindowTitle("IPQuery v1.1")
        self.setWindowIcon(_get_embedded_icon())
        self.resize(1180, 780)
        self.setMinimumSize(960, 600)

        _sd = os.path.dirname(os.path.abspath(sys.argv[0]))
        if sys.platform == "darwin" and _sd.endswith(".app/Contents/MacOS"):
            self.default_db_dir = os.path.join(os.path.expanduser("~/Library/Application Support"), "IPQuery", "db")
        else:
            self.default_db_dir = _sd

        self.worker: Optional[WorkerThread] = None
        self.db_thread: Optional[DbUpdateThread] = None
        self.all_results: list[list] = []

        self._check_dependencies()
        self._init_ui()
        self._check_databases()

    # ==================== UI ====================
    def _init_ui(self):
        c = QWidget(); self.setCentralWidget(c)
        ml = QVBoxLayout(c); ml.setContentsMargins(16, 12, 16, 12); ml.setSpacing(12)

        # Input
        ig = QGroupBox("📥 输入（每行一个域名或 IP）")
        il = QVBoxLayout(ig)
        self.input_text = QTextEdit()
        self.input_text.setPlaceholderText("每行一个，支持：域名 / http://url / IPv4 / IPv6")
        self.input_text.setMaximumHeight(130)
        il.addWidget(self.input_text)
        ml.addWidget(ig)

        # Settings row
        mr = QHBoxLayout(); mr.setSpacing(12)

        # DNS
        dg = QGroupBox("🔍 DNS 解析设置")
        dl = QVBoxLayout(dg)
        self.btn_system_dns = QRadioButton("系统 DNS"); self.btn_custom_dns = QRadioButton("自定义 DNS")
        self.btn_doh_dns = QRadioButton("DoH (DNS over HTTPS)"); self.btn_system_dns.setChecked(True)
        bg = QButtonGroup(self); bg.addButton(self.btn_system_dns, 0); bg.addButton(self.btn_custom_dns, 1); bg.addButton(self.btn_doh_dns, 2)
        bg.buttonClicked.connect(self._on_dns_mode_changed)
        dl.addWidget(self.btn_system_dns); dl.addWidget(self.btn_custom_dns); dl.addWidget(self.btn_doh_dns)
        self.custom_dns_input = QLineEdit()
        self.custom_dns_input.setPlaceholderText("用逗号分隔: 8.8.8.8, 223.5.5.5")
        self.custom_dns_input.setText(", ".join(DEFAULT_CUSTOM_DNS)); self.custom_dns_input.setEnabled(False)
        dl.addWidget(self.custom_dns_input)
        self.doh_url_input = QLineEdit(); self.doh_url_input.setPlaceholderText("DoH 接口地址")
        self.doh_url_input.setText(DnsResolver.DEFAULT_DOH_URLS[0]); self.doh_url_input.setEnabled(False)
        self.doh_preset = QComboBox(); self.doh_preset.addItems(DnsResolver.DEFAULT_DOH_URLS)
        self.doh_preset.setCurrentIndex(0); self.doh_preset.setEnabled(False)
        self.doh_preset.currentTextChanged.connect(lambda u: self.doh_url_input.setText(u))
        dr = QHBoxLayout(); dr.addWidget(self.doh_url_input, 1); dr.addWidget(self.doh_preset)
        dl.addLayout(dr)
        mr.addWidget(dg, 2)

        # Options
        og = QGroupBox("⚙ 输出选项")
        ol = QVBoxLayout(og)
        self.cdn_check = QCheckBox("启用 CDN 检测"); self.cdn_check.setChecked(True)
        ol.addWidget(self.cdn_check)
        self.first_only_check = QCheckBox("每个域名只输出一个地址"); self.first_only_check.setChecked(False)
        self.first_only_check.setToolTip("开启后每个域名只输出第一个解析到的 IP，关闭则输出全部")
        ol.addWidget(self.first_only_check)
        mr.addWidget(og, 1)

        # DB path
        dg2 = QGroupBox("🗄️ 数据库路径")
        dbl = QVBoxLayout(dg2)
        dbr = QHBoxLayout()
        self.db_path_input = QLineEdit(); self.db_path_input.setText(self.default_db_dir)
        self.db_path_input.setPlaceholderText("数据库目录")
        dbr.addWidget(self.db_path_input)
        bb = QPushButton("浏览..."); bb.setObjectName("btnBrowseDb"); bb.clicked.connect(self._browse_db_dir); bb.setFixedWidth(90)
        dbr.addWidget(bb); dbl.addLayout(dbr)
        self.db_status_label = QLabel(""); self.db_status_label.setStyleSheet("font-size: 11px;")
        dbl.addWidget(self.db_status_label)
        mr.addWidget(dg2, 3)
        ml.addLayout(mr)

        # Buttons
        br = QHBoxLayout(); br.setSpacing(10)
        self.btn_query = QPushButton("🔎 开始查询"); self.btn_query.setObjectName("btnQuery")
        self.btn_query.clicked.connect(self._start_query); self.btn_query.setMinimumHeight(36); br.addWidget(self.btn_query)
        self.btn_stop = QPushButton("⏹ 停止"); self.btn_stop.clicked.connect(self._stop_query)
        self.btn_stop.setMinimumHeight(36); self.btn_stop.setEnabled(False)
        self.btn_stop.setStyleSheet("QPushButton { background-color: #e74c3c; color: white; border-radius: 6px; padding: 8px 20px; font-size: 13px; border: none; } QPushButton:hover { background-color: #c0392b; }")
        br.addWidget(self.btn_stop); br.addStretch()
        self.btn_update_db = QPushButton("🔄 更新数据库"); self.btn_update_db.setObjectName("btnUpdateDb")
        self.btn_update_db.clicked.connect(self._update_database); self.btn_update_db.setMinimumHeight(36); br.addWidget(self.btn_update_db)
        self.btn_clear = QPushButton("清空输出"); self.btn_clear.setObjectName("btnClear")
        self.btn_clear.clicked.connect(self._clear_output); self.btn_clear.setMinimumHeight(36); br.addWidget(self.btn_clear)
        self.btn_export = QPushButton("📤 导出 CSV"); self.btn_export.setObjectName("btnExport")
        self.btn_export.clicked.connect(self._export_csv); self.btn_export.setMinimumHeight(36); br.addWidget(self.btn_export)
        ml.addLayout(br)

        # Progress
        self.progress_bar = QProgressBar(); self.progress_bar.setValue(0); ml.addWidget(self.progress_bar)
        self.status_label = QLabel("就绪"); self.status_label.setStyleSheet("font-size: 12px; color: #636e72;"); ml.addWidget(self.status_label)

        # Result table
        rg = QGroupBox("📊 查询结果"); rl = QVBoxLayout(rg)
        self.result_table = QTableWidget()
        self.result_table.setColumnCount(len(self.COLUMNS))
        self.result_table.setHorizontalHeaderLabels(self.COLUMNS)
        self.result_table.setAlternatingRowColors(True)
        self.result_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.result_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        h = self.result_table.horizontalHeader()
        for col in (2, 3, 4, 8): h.setSectionResizeMode(col, QHeaderView.ResizeMode.ResizeToContents)
        h.setSectionResizeMode(5, QHeaderView.ResizeMode.Stretch)
        h.setSectionResizeMode(6, QHeaderView.ResizeMode.Stretch)
        h.setSectionResizeMode(7, QHeaderView.ResizeMode.Stretch)
        for col in (0, 1): h.setSectionResizeMode(col, QHeaderView.ResizeMode.Interactive)
        self.result_table.setColumnWidth(0, 180); self.result_table.setColumnWidth(1, 200)
        rl.addWidget(self.result_table); ml.addWidget(rg, 1)

        self.status_bar = QStatusBar(); self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("就绪 — 请输入域名或 IP 后点击「开始查询」")

    # ==================== Slots ====================
    def _on_dns_mode_changed(self, btn):
        self.custom_dns_input.setEnabled(btn == self.btn_custom_dns)
        doh = btn == self.btn_doh_dns
        self.doh_url_input.setEnabled(doh); self.doh_preset.setEnabled(doh)

    def _browse_db_dir(self):
        p = QFileDialog.getExistingDirectory(self, "选择数据库目录", self.db_path_input.text())
        if p: self.db_path_input.setText(p); self._check_databases()

    def _check_dependencies(self):
        mp = []
        if geoip2 is None: mp.append("geoip2")
        if dns is None: mp.append("dnspython")
        if requests is None: mp.append("requests")
        if QQwryReader is None: mp.append("qqwry-py3")
        if not mp: return
        cmd = f"pip install {' '.join(mp)}"
        d = QDialog(self); d.setWindowTitle("缺少依赖"); d.setMinimumWidth(480); d.setModal(True)
        l = QVBoxLayout(d); l.setSpacing(12)
        m = QLabel(f"以下 Python 依赖库未安装：\n" + "\n".join(f"  · {p}" for p in mp) + "\n\n请在终端执行：")
        m.setWordWrap(True); m.setStyleSheet("font-size: 13px; color: #2d3436;"); l.addWidget(m)
        cl = QLabel(cmd); cl.setStyleSheet("font-size: 13px; font-family: monospace; background-color: #ecf0f1; padding: 10px; border-radius: 4px; color: #2c3e50;")
        cl.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse); l.addWidget(cl)
        br = QHBoxLayout()
        bc = QPushButton("📋 复制命令"); bc.setStyleSheet("QPushButton { background-color: #3498db; color: white; border-radius: 6px; padding: 8px 20px; font-size: 13px; border: none; } QPushButton:hover { background-color: #2980b9; }")
        bc.clicked.connect(lambda: self._copy_pip_cmd(cmd, d)); br.addWidget(bc); br.addStretch()
        be = QPushButton("退出程序"); be.setStyleSheet("QPushButton { background-color: #95a5a6; color: white; border-radius: 6px; padding: 8px 20px; font-size: 13px; border: none; } QPushButton:hover { background-color: #7f8c8d; }")
        be.clicked.connect(sys.exit); br.addWidget(be); l.addLayout(br); d.exec()

    @staticmethod
    def _copy_pip_cmd(cmd, dlg):
        QApplication.clipboard().setText(cmd)
        for btn in dlg.findChildren(QPushButton):
            if btn.text() == "📋 复制命令":
                btn.setText("✅ 已复制"); btn.setStyleSheet("QPushButton { background-color: #27ae60; color: white; border-radius: 6px; padding: 8px 20px; font-size: 13px; border: none; }")

    def _check_databases(self):
        db_dir = self.db_path_input.text()
        os.makedirs(db_dir, exist_ok=True)
        present, missing = [], []
        for name, fn, _ in DB_FILES_CONFIG:
            fp = os.path.join(db_dir, fn)
            if os.path.exists(fp): present.append(f"{name} ({os.path.getsize(fp)/1048576:.1f} MB)")
            else: missing.append(name)
        if not missing:
            self.status_label.setText(f"✅ 全部 {len(DB_FILES_CONFIG)} 个数据库文件完整")
            self.status_label.setStyleSheet("font-size: 12px; color: #27ae60;")
            self.db_status_label.setText(" | ".join(present)); self.db_status_label.setStyleSheet("font-size: 11px; color: #27ae60;")
        else:
            self.status_label.setText(f"⚠ 缺少数据库: {' / '.join(missing)} — 请点击「更新数据库」下载")
            self.status_label.setStyleSheet("font-size: 12px; color: #e67e22;")
            self.db_status_label.setText(f"✅ {' | '.join(present)}  ⚠ 缺少: {' / '.join(missing)}")
            self.db_status_label.setStyleSheet("font-size: 11px; color: #e67e22;")

    def _start_query(self):
        text = self.input_text.toPlainText().strip()
        if not text: QMessageBox.warning(self, "提示", "请先输入域名或 IP 地址。"); return
        db_dir = self.db_path_input.text()
        db_paths = {}; missing = []
        for name, fn, _ in DB_FILES_CONFIG:
            fp = os.path.join(db_dir, fn); db_paths[name] = fp
            if not os.path.exists(fp): missing.append(name)
        if missing:
            QMessageBox.critical(self, "数据库缺失", f"以下数据库文件不存在：\n  " + "\n  ".join(missing) + "\n\n请点击「更新数据库」下载。"); return
        if geoip2 is None: QMessageBox.critical(self, "缺少依赖", "请安装 geoip2"); return
        if dns is None: QMessageBox.critical(self, "缺少依赖", "请安装 dnspython"); return

        inputs = [l.strip() for l in text.split("\n") if l.strip()]
        dns_mode = "custom" if self.btn_custom_dns.isChecked() else "doh" if self.btn_doh_dns.isChecked() else "system"
        custom_dns_list = [s.strip() for s in self.custom_dns_input.text().split(",") if s.strip()]
        doh_url = self.doh_url_input.text().strip() or DnsResolver.DEFAULT_DOH_URLS[0]

        self.result_table.setRowCount(0); self.all_results = []
        self.btn_query.setEnabled(False); self.btn_stop.setEnabled(True)
        self.input_text.setEnabled(False); self.progress_bar.setValue(0)

        self.worker = WorkerThread(
            inputs=inputs, dns_mode=dns_mode, custom_dns=custom_dns_list,
            doh_url=doh_url, country_db=db_paths["Country"], city_db=db_paths["City"],
            asn_db=db_paths["ASN"], qqwry_path=db_paths["纯真IP"],
            detect_cdn=self.cdn_check.isChecked(), first_only=self.first_only_check.isChecked(),
        )
        self.worker.progress.connect(self._on_progress); self.worker.status.connect(self._on_status)
        self.worker.result.connect(self._on_result); self.worker.error.connect(self._on_worker_error)
        self.worker.finished.connect(self._on_finished); self.worker.start()

    def _stop_query(self):
        if self.worker and self.worker.isRunning(): self.worker.cancel()
        self.status_label.setText("正在停止..."); self.status_label.setStyleSheet("font-size: 12px; color: #e74c3c;")

    def _on_progress(self, cur, tot):
        self.progress_bar.setMaximum(tot); self.progress_bar.setValue(cur)
        self.status_bar.showMessage(f"处理中... {cur}/{tot}")

    def _on_status(self, msg): self.status_label.setText(msg)

    def _on_worker_error(self, msg):
        QMessageBox.critical(self, "查询异常", msg)
        self.btn_query.setEnabled(True); self.btn_stop.setEnabled(False)
        self.input_text.setEnabled(True)
        self.status_label.setText(f"❌ {msg.split(chr(10))[0]}"); self.status_label.setStyleSheet("font-size: 12px; color: #e74c3c;")

    def _on_result(self, row):
        """
        row = [source, ip, country, province, city, lat, lon, asn, cdn, remark]
        table = [source, ip, country, province, city, lat_lon, asn, cdn, remark]
        """
        self.all_results.append(row)
        tr = self.result_table.rowCount(); self.result_table.insertRow(tr)
        ll = ""
        if len(row) > 6 and row[5] and row[6]: ll = f"{row[5]}, {row[6]}"
        remark = row[9] if len(row) > 9 else ""
        disp = [row[0], row[1], row[2], row[3], row[4], ll,
                row[7] if len(row) > 7 else "", row[8] if len(row) > 8 else "", remark]
        for col, val in enumerate(disp):
            item = QTableWidgetItem(str(val))
            item.setTextAlignment(Qt.AlignmentFlag.AlignCenter if col >= 2 else (Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter))
            # CDN highlight
            if col == 7 and val == "是":
                item.setForeground(QColor("#e67e22")); item.setFont(QFont(self.font().family(), -1, QFont.Weight.Bold))
            # Failure highlight
            if col == 1 and (val == "解析失败" or val == ""):
                item.setForeground(QColor("#e74c3c"));
            if col == 8 and val:
                item.setForeground(QColor("#e74c3c"));
            if col == 1 and val == "查询失败":
                item.setForeground(QColor("#e74c3c"));
            self.result_table.setItem(tr, col, item)
        self.result_table.scrollToBottom()

    def _on_finished(self):
        self.btn_query.setEnabled(True); self.btn_stop.setEnabled(False)
        self.input_text.setEnabled(True); self.progress_bar.setValue(self.progress_bar.maximum())
        count = self.result_table.rowCount()
        if count == 0 and self.worker is not None:
            self.status_label.setText("⚠ 查询结束但无结果，请检查控制台输出或重试")
            self.status_label.setStyleSheet("font-size: 12px; color: #e67e22;")
            self.status_bar.showMessage("无结果 — 可能 DNS 解析全部失败或数据库路径异常")
        else:
            ok = sum(1 for r in self.all_results if r[1] not in ("解析失败", "查询失败", ""))
            fail = count - ok
            self.status_bar.showMessage(f"完成 — 共 {count} 条，成功 {ok}，失败 {fail}")
            self.status_label.setText(f"✅ 查询完成 — {count} 条记录")
            self.status_label.setStyleSheet("font-size: 12px; color: #27ae60;")
        self.worker = None

    def _clear_output(self):
        self.result_table.setRowCount(0); self.all_results = []
        self.progress_bar.setValue(0); self.status_bar.showMessage("就绪")
        self.status_label.setText("就绪"); self.status_label.setStyleSheet("font-size: 12px; color: #636e72;")
        self._check_databases()

    def _export_csv(self):
        if not self.all_results: QMessageBox.information(self, "提示", "没有可导出的数据。"); return
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        default_name = f"ips_result_{ts}.csv"
        path, _ = QFileDialog.getSaveFileName(self, "导出 CSV", default_name, "CSV 文件 (*.csv)")
        if not path: return
        try:
            with open(path, "w", newline="", encoding="utf-8-sig") as f:
                w = csv.writer(f)
                w.writerow(["来源", "IP地址", "国家", "省份", "城市", "纬度", "经度", "ASN/云服务", "是否CDN", "备注"])
                for row in self.all_results: w.writerow(row)
            self.status_bar.showMessage(f"已导出: {os.path.basename(path)}")
            # Custom dialog with Open Folder / Open File
            d = QDialog(self); d.setWindowTitle("导出完成"); d.setMinimumWidth(420)
            l = QVBoxLayout(d); l.setSpacing(12)
            l.addWidget(QLabel(f"结果已保存到:\n{os.path.basename(path)}"))
            fp_label = QLabel(path); fp_label.setWordWrap(True)
            fp_label.setStyleSheet("font-size: 11px; color: #636e72;"); l.addWidget(fp_label)
            br = QHBoxLayout()
            bf = QPushButton("📂 打开文件夹"); bf.setStyleSheet("QPushButton { background-color: #3498db; color: white; border-radius: 6px; padding: 8px 16px; font-size: 13px; border: none; } QPushButton:hover { background-color: #2980b9; }")
            bf.clicked.connect(lambda: self._open_file(path, folder=True))
            bo = QPushButton("📄 打开文件"); bo.setStyleSheet("QPushButton { background-color: #27ae60; color: white; border-radius: 6px; padding: 8px 16px; font-size: 13px; border: none; } QPushButton:hover { background-color: #219a52; }")
            bo.clicked.connect(lambda: self._open_file(path, folder=False))
            bok = QPushButton("确定"); bok.clicked.connect(d.accept)
            br.addWidget(bf); br.addWidget(bo); br.addStretch(); br.addWidget(bok); l.addLayout(br); d.exec()
        except Exception as e:
            QMessageBox.critical(self, "导出失败", str(e))

    @staticmethod
    def _open_file(path, folder=False):
        target = os.path.dirname(path) if folder else path
        if sys.platform == "darwin":
            subprocess.Popen(["open", target if folder else "-R", target if not folder else target])
        elif sys.platform == "win32":
            os.startfile(target if not folder else os.path.dirname(target))
        else:
            subprocess.Popen(["xdg-open", target])

    def _update_database(self):
        if requests is None: QMessageBox.critical(self, "缺少依赖", "请安装 requests"); return
        db_dir = self.db_path_input.text()
        if not os.path.isdir(db_dir): QMessageBox.critical(self, "路径无效", f"目录不存在:\n{db_dir}"); return
        r = QMessageBox.question(self, "确认更新", f"将从以下源下载全部 4 个数据库到:\n{db_dir}\n\n" + "\n".join(f"  · {n}: {fn}" for n, fn, _ in DB_FILES_CONFIG) + "\n\n是否继续？", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if r != QMessageBox.StandardButton.Yes: return
        self.btn_update_db.setEnabled(False); self.btn_query.setEnabled(False); self.progress_bar.setValue(0)
        self.db_thread = DbUpdateThread(db_dir)
        self.db_thread.progress_text.connect(self._on_db_progress_text)
        self.db_thread.progress_percent.connect(self._on_db_progress_pct)
        self.db_thread.finished.connect(self._on_db_finished); self.db_thread.start()

    def _on_db_progress_text(self, m): self.status_label.setText(m)
    def _on_db_progress_pct(self, p): self.progress_bar.setValue(p)

    def _on_db_finished(self, ok, msg):
        self.btn_update_db.setEnabled(True); self.btn_query.setEnabled(True)
        self.progress_bar.setValue(100 if ok else 0)
        self.status_label.setText(f"{'✅' if ok else '❌'} {msg}")
        self.status_label.setStyleSheet(f"font-size: 12px; color: {'#27ae60' if ok else '#e74c3c'};")
        if ok: self._check_databases()
        QMessageBox.information(self, "更新结果" if ok else "更新失败", msg)
        self.db_thread = None


# ============================================================================
# Entry
# ============================================================================
def main():
    app = QApplication(sys.argv)
    app.setStyleSheet(STYLE_QSS)
    if sys.platform == "darwin": app.setAttribute(Qt.ApplicationAttribute.AA_DontShowIconsInMenus, False)
    w = IPLookupWindow(); w.show(); sys.exit(app.exec())

if __name__ == "__main__": main()
