import sys
import os
import json
import base64
import csv
import socket
import threading
import re
import ctypes
import time

WAKTU_AKTIF_SISWA = {}

from flask import Flask, request, jsonify
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                             QLabel, QLineEdit, QPushButton, QComboBox, QStackedWidget,
                             QTableWidget, QTableWidgetItem, QHeaderView, QDoubleSpinBox, 
                             QTextEdit, QFileDialog, QMessageBox, QScrollArea,
                             QFormLayout, QCheckBox, QDialog, QAbstractItemView,
                             QToolBar, QInputDialog, QDialogButtonBox,
                             QFrame, QSplitter, QButtonGroup)
from PyQt6.QtGui import QFont, QPixmap, QIcon, QAction, QTextBlockFormat, QPainter, QColor
from PyQt6.QtCore import Qt, QTimer, QVariantAnimation, QEasingCurve, QPointF

try:
    import docx
    DOCX_AVAILABLE = True
except ImportError:
    DOCX_AVAILABLE = False

def dapatkan_path_file(nama_file):
    if os.path.exists(nama_file):
        return os.path.abspath(nama_file)
    try:
        base_path = sys._MEIPASS
        path_meipass = os.path.join(base_path, nama_file)
        if os.path.exists(path_meipass):
            return path_meipass
    except Exception:
        pass
    if getattr(sys, 'frozen', False):
        base_exe = os.path.dirname(sys.executable)
        path_exe = os.path.join(base_exe, nama_file)
        if os.path.exists(path_exe):
            return path_exe
    return os.path.abspath(nama_file)

def dapatkan_ip_lokal():
    """Mendeteksi IP Wi-Fi / LAN aktif secara real-time (mendukung router dengan/tanpa internet)."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.settimeout(0.1)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        if ip and not ip.startswith("127.") and not ip.startswith("169.254."):
            return ip
    except Exception:
        pass

    try:
        hostname = socket.gethostname()
        infos = socket.getaddrinfo(hostname, None, socket.AF_INET)
        kandidat = []
        for info in infos:
            ip = info[4][0]
            if not ip.startswith("127.") and not ip.startswith("169.254."):
                kandidat.append(ip)
        for prefix in ("192.168.", "10.", "172."):
            for ip in kandidat:
                if ip.startswith(prefix):
                    return ip
        if kandidat:
            return kandidat[0]
    except Exception:
        pass

    return "Tidak Terhubung"

# ================= GAYA VISUAL SEJUK & RENDAH SILAU (QSS) =================
STYLE_GLOBAL = """
    QMainWindow, QWidget {
        background-color: #D8E0EA;
        color: #1E293B;
        font-family: 'Segoe UI';
        font-size: 10pt;
    }
    QScrollBar:vertical {
        border: none;
        background: transparent;
        width: 8px;
        margin: 2px;
    }
    QScrollBar::handle:vertical {
        background: #94A3B8;
        min-height: 30px;
        border-radius: 4px;
    }
    QScrollBar::handle:vertical:hover {
        background: #64748B;
    }
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
        height: 0px;
    }
    QScrollBar:horizontal {
        border: none;
        background: transparent;
        height: 8px;
        margin: 2px;
    }
    QScrollBar::handle:horizontal {
        background: #94A3B8;
        min-width: 30px;
        border-radius: 4px;
    }
    QScrollBar::handle:horizontal:hover {
        background: #64748B;
    }
    QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
        width: 0px;
    }
    QSplitter::handle {
        background-color: #B8C4D4;
        width: 3px;
        margin: 12px 4px;
        border-radius: 1px;
    }
    QSplitter::handle:hover {
        background-color: #4F46E5;
    }
"""

STYLE_TABEL = """
    QTableWidget {
        background-color: #F4F7FA;
        border-radius: 10px;
        border: 1px solid #C2CEDB;
        gridline-color: transparent;
        font-size: 10pt;
        alternate-background-color: #E9EFF5;
        selection-background-color: #DDE4FA;
        selection-color: #3730A3;
        outline: none;
    }
    QHeaderView::section {
        background-color: #E2E8F0;
        color: #334155;
        font-weight: bold;
        padding: 10px 12px;
        border: none;
        border-bottom: 2px solid #C2CEDB;
        font-size: 10pt;
    }
    QTableWidget::item {
        padding: 6px 12px;
        border-bottom: 1px solid #DCE3EC;
        color: #1E293B;
    }
    QTableWidget::item:hover {
        background-color: #E4EAF4;
    }
    QTableWidget::item:selected {
        background-color: #DDE4FA;
        color: #3730A3;
        font-weight: bold;
    }
"""

STYLE_CARD = """
    QFrame#CardPanel {
        background-color: #EEF2F6;
        border-radius: 14px;
        border: 1px solid #C2CEDB;
    }
"""

STYLE_BTN_PRIMARY = """
    QPushButton {
        background-color: #4F46E5;
        color: #F8FAFC;
        border-radius: 8px;
        padding: 9px 15px;
        font-weight: bold;
        border: none;
    }
    QPushButton:hover { background-color: #4338CA; }
    QPushButton:pressed { background-color: #3730A3; }
    QPushButton:disabled { background-color: #64748B; color: #CBD5E1; }
"""

STYLE_BTN_SUCCESS = """
    QPushButton {
        background-color: #059669;
        color: #F8FAFC;
        border-radius: 8px;
        padding: 9px 15px;
        font-weight: bold;
        border: none;
    }
    QPushButton:hover { background-color: #047857; }
    QPushButton:pressed { background-color: #065F46; }
"""

STYLE_BTN_DANGER = """
    QPushButton {
        background-color: #DC2626;
        color: #F8FAFC;
        border-radius: 8px;
        padding: 9px 15px;
        font-weight: bold;
        border: none;
    }
    QPushButton:hover { background-color: #B91C1C; }
    QPushButton:pressed { background-color: #991B1B; }
"""

STYLE_BTN_WARNING = """
    QPushButton {
        background-color: #D97706;
        color: #F8FAFC;
        border-radius: 8px;
        padding: 9px 15px;
        font-weight: bold;
        border: none;
    }
    QPushButton:hover { background-color: #B45309; }
    QPushButton:pressed { background-color: #92400E; }
"""

STYLE_BTN_SECONDARY = """
    QPushButton {
        background-color: #E2E8F0;
        color: #1E293B;
        border-radius: 8px;
        padding: 9px 14px;
        font-weight: bold;
        border: 1px solid #B8C4D4;
    }
    QPushButton:hover {
        background-color: #D5DFEC;
        color: #3730A3;
        border: 1px solid #94A3B8;
    }
    QPushButton:pressed { background-color: #CBD5E1; }
"""

STYLE_NAV_BTN = """
    QPushButton {
        background-color: transparent;
        color: #CBD5E1;
        border-radius: 10px;
        padding: 11px 14px;
        text-align: left;
        font-weight: bold;
        font-size: 10pt;
        border: none;
    }
    QPushButton:hover {
        background-color: #293548;
        color: #F8FAFC;
    }
    QPushButton:checked {
        background-color: #334155;
        color: #FFFFFF;
        border-left: 4px solid #818CF8;
    }
"""

STYLE_INPUT = """
    QLineEdit, QComboBox, QDoubleSpinBox {
        background-color: #E4EAF1;
        color: #0F172A;
        border: 1.5px solid #B8C4D4;
        border-radius: 8px;
        padding: 7px 10px;
    }
    QLineEdit:focus, QComboBox:focus, QDoubleSpinBox:focus {
        border: 1.5px solid #4F46E5;
        background-color: #F8FAFC;
    }
    QComboBox::drop-down {
        border: none;
        padding-right: 8px;
    }
    QComboBox QAbstractItemView {
        background-color: #EEF2F6;
        color: #0F172A;
        selection-background-color: #DDE4FA;
        selection-color: #3730A3;
        border: 1px solid #B8C4D4;
        border-radius: 8px;
        outline: none;
        padding: 4px;
    }
"""

# ================= KUSTOM KOMPONEN =================
class AntiScrollComboBox(QComboBox):
    def wheelEvent(self, e): e.ignore()

class AntiScrollSpinBox(QDoubleSpinBox):
    def wheelEvent(self, e): e.ignore()

class SmoothTableWidget(QTableWidget):
    def __init__(self, rows=0, cols=0):
        super().__init__(rows, cols)
        self.setVerticalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
        self.setHorizontalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
        self.setShowGrid(False)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.verticalHeader().setDefaultSectionSize(38)

    def wheelEvent(self, event):
        super().wheelEvent(event)
        event.accept()

class _TransisiOverlay(QWidget):
    """Kanvas compositor 60 FPS untuk crossfade + micro-slide ala React/Framer Motion."""
    def __init__(self, parent, pix_lama, pix_baru, arah=1, bg_color="#D8E0EA"):
        super().__init__(parent)
        self.pix_lama = pix_lama
        self.pix_baru = pix_baru
        self.arah = arah
        self.bg_color = QColor(bg_color)
        self.progress = 0.0
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.setGeometry(0, 0, parent.width(), parent.height())

    def set_progress(self, val):
        self.progress = float(val)
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)
        p.fillRect(self.rect(), self.bg_color)

        t = self.progress
        jarak = 18.0 * self.arah

        # Halaman lama: memudar halus & bergeser tipis
        opacity_lama = max(0.0, 1.0 - (t * 1.15))
        if opacity_lama > 0.0:
            p.setOpacity(opacity_lama)
            p.drawPixmap(QPointF(0.0, -jarak * 0.35 * t), self.pix_lama)

        # Halaman baru: muncul halus & meluncur presisi ke titik (0, 0)
        p.setOpacity(min(1.0, t))
        p.drawPixmap(QPointF(0.0, jarak * (1.0 - t)), self.pix_baru)
        p.end()

class SmoothStackedWidget(QStackedWidget):
    """Transisi halaman sehalus React tanpa getar maupun QGraphicsEffect."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self._overlay = None
        self._anim = None

    def _bersihkan_transisi(self):
        if self._anim is not None:
            self._anim.stop()
            self._anim.deleteLater()
            self._anim = None
        if self._overlay is not None:
            self._overlay.hide()
            self._overlay.deleteLater()
            self._overlay = None

    def resizeEvent(self, event):
        self._bersihkan_transisi()
        super().resizeEvent(event)

    def slide_ke(self, index):
        idx_lama = self.currentIndex()
        if index == idx_lama or index < 0 or index >= self.count():
            return

        self._bersihkan_transisi()
        widget_lama = self.currentWidget()
        if not widget_lama or self.width() <= 0 or self.height() <= 0:
            self.setCurrentIndex(index)
            return

        arah = 1 if index > idx_lama else -1
        pix_lama = widget_lama.grab()

        self.setCurrentIndex(index)
        widget_baru = self.currentWidget()
        widget_baru.resize(self.size())
        if widget_baru.layout():
            widget_baru.layout().activate()
        pix_baru = widget_baru.grab()

        self._overlay = _TransisiOverlay(self, pix_lama, pix_baru, arah=arah)
        self._overlay.show()
        self._overlay.raise_()

        self._anim = QVariantAnimation(self)
        self._anim.setDuration(190)
        self._anim.setStartValue(0.0)
        self._anim.setEndValue(1.0)
        self._anim.setEasingCurve(QEasingCurve.Type.OutQuart)
        self._anim.valueChanged.connect(self._overlay.set_progress)
        self._anim.finished.connect(self._bersihkan_transisi)
        self._anim.start()

class RichTextEditor(QWidget):
    def __init__(self):
        super().__init__()
        ly = QVBoxLayout(self)
        ly.setContentsMargins(0, 0, 0, 0)
        ly.setSpacing(4)
        
        self.toolbar = QToolBar()
        self.toolbar.setStyleSheet("""
            QToolBar {
                background-color: #E2E8F0;
                border: 1px solid #B8C4D4;
                border-radius: 8px;
                padding: 2px;
                spacing: 3px;
            }
            QToolButton {
                background-color: transparent;
                border-radius: 5px;
                padding: 4px 7px;
                font-weight: bold;
                color: #1E293B;
            }
            QToolButton:hover {
                background-color: #CBD5E1;
                color: #3730A3;
            }
        """)
        self.editor = QTextEdit()
        self.editor.setStyleSheet("""
            QTextEdit {
                font-family: 'Times New Roman';
                font-size: 12pt;
                background-color: #F8FAFC;
                color: #0F172A;
                border: 1.5px solid #B8C4D4;
                border-radius: 8px;
                padding: 6px;
            }
            QTextEdit:focus {
                border: 1.5px solid #4F46E5;
                background-color: #FBFDFF;
            }
        """)
        
        btn_b = QAction("B", self)
        btn_b.setFont(QFont("Arial", 10, QFont.Weight.Bold))
        btn_b.triggered.connect(lambda: self.editor.setFontWeight(QFont.Weight.Bold if self.editor.fontWeight() != QFont.Weight.Bold else QFont.Weight.Normal))
        
        btn_i = QAction("I", self)
        btn_i.setFont(QFont("Arial", 10, QFont.Weight.Normal, True))
        btn_i.triggered.connect(lambda: self.editor.setFontItalic(not self.editor.fontItalic()))
        
        btn_u = QAction("U", self)
        font_u = QFont("Arial", 10)
        font_u.setUnderline(True)
        btn_u.setFont(font_u)
        btn_u.triggered.connect(lambda: self.editor.setFontUnderline(not self.editor.fontUnderline()))
        
        btn_al = QAction("L", self); btn_al.setToolTip("Rata Kiri"); btn_al.triggered.connect(lambda: self.editor.setAlignment(Qt.AlignmentFlag.AlignLeft))
        btn_ac = QAction("C", self); btn_ac.setToolTip("Rata Tengah"); btn_ac.triggered.connect(lambda: self.editor.setAlignment(Qt.AlignmentFlag.AlignCenter))
        btn_ar = QAction("R", self); btn_ar.setToolTip("Rata Kanan"); btn_ar.triggered.connect(lambda: self.editor.setAlignment(Qt.AlignmentFlag.AlignRight))
        btn_aj = QAction("J", self); btn_aj.setToolTip("Rata Kanan-Kiri (Justify)"); btn_aj.triggered.connect(lambda: self.editor.setAlignment(Qt.AlignmentFlag.AlignJustify))
        
        btn_img_inline = QAction("🖼️ Gambar", self)
        btn_img_inline.setToolTip("Sisipkan Gambar di baris ini")
        btn_img_inline.triggered.connect(self.sisipkan_gambar_inline)
        
        self.cb_font = AntiScrollComboBox()
        self.cb_font.addItems(["Times New Roman", "Segoe UI", "Arial", "Courier New"])
        self.cb_font.currentTextChanged.connect(self.editor.setFontFamily)
        
        self.cb_size = AntiScrollComboBox()
        self.cb_size.addItems(["8", "10", "11", "12", "14", "16", "18", "20", "24", "36"])
        self.cb_size.setCurrentText("12")
        self.cb_size.currentTextChanged.connect(lambda s: self.editor.setFontPointSize(float(s)))
        
        self.cb_spasi = AntiScrollComboBox()
        self.cb_spasi.addItems(["1.0", "1.15", "1.5", "2.0"])
        self.cb_spasi.currentTextChanged.connect(self.ubah_spasi)
        
        self.toolbar.addAction(btn_b)
        self.toolbar.addAction(btn_i)
        self.toolbar.addAction(btn_u)
        self.toolbar.addSeparator()
        self.toolbar.addAction(btn_al)
        self.toolbar.addAction(btn_ac)
        self.toolbar.addAction(btn_ar)
        self.toolbar.addAction(btn_aj)
        self.toolbar.addSeparator()
        self.toolbar.addAction(btn_img_inline)
        self.toolbar.addSeparator()
        
        lbl_f = QLabel(" Font: "); lbl_f.setStyleSheet("background: transparent;")
        lbl_u = QLabel(" Ukuran: "); lbl_u.setStyleSheet("background: transparent;")
        lbl_s = QLabel(" Spasi: "); lbl_s.setStyleSheet("background: transparent;")
        self.toolbar.addWidget(lbl_f)
        self.toolbar.addWidget(self.cb_font)
        self.toolbar.addWidget(lbl_u)
        self.toolbar.addWidget(self.cb_size)
        self.toolbar.addWidget(lbl_s)
        self.toolbar.addWidget(self.cb_spasi)
        
        ly.addWidget(self.toolbar)
        ly.addWidget(self.editor)
        
    def sisipkan_gambar_inline(self):
        fp, _ = QFileDialog.getOpenFileName(self, "Pilih Gambar", "", "Image Files (*.png *.jpg *.jpeg)")
        if fp:
            try:
                with open(fp, "rb") as f:
                    b64 = base64.b64encode(f.read()).decode('utf-8')
                    img_html = f'<br><img src="data:image/png;base64,{b64}" width="400"><br>'
                    self.editor.insertHtml(img_html)
            except Exception: pass

    def ubah_spasi(self, val):
        cursor = self.editor.textCursor()
        fmt = QTextBlockFormat()
        fmt.setLineHeight(float(val) * 100, QTextBlockFormat.LineHeightTypes.ProportionalHeight)
        cursor.mergeBlockFormat(fmt)
        self.editor.setTextCursor(cursor)
                
    def toHtml(self): 
        html = self.editor.toHtml()
        if not self.editor.toPlainText().strip() and '<img' not in html.lower():
            return ""
        return html
        
    def setHtml(self, html): self.editor.setHtml(html)
    def toPlainText(self): return self.editor.toPlainText()
    def clear(self): self.editor.clear()

# ================= DIALOG POPUP SETTING BOBOT IMPORT =================
class DialogSettingBobot(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Pengaturan Bobot Import")
        self.setMinimumWidth(340)
        self.setStyleSheet("background-color: #EEF2F6; color: #0F172A;")
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)
        
        lbl_info = QLabel("Atur bobot poin otomatis untuk setiap tipe soal:")
        lbl_info.setStyleSheet("font-weight: bold; color: #3730A3; background: transparent;")
        layout.addWidget(lbl_info)
        
        form_layout = QFormLayout()
        form_layout.setSpacing(10)
        
        self.spin_pg = AntiScrollSpinBox()
        self.spin_pg.setStyleSheet(STYLE_INPUT)
        self.spin_pg.setDecimals(2)
        self.spin_pg.setValue(2.0)  
        
        self.spin_pgk = AntiScrollSpinBox()
        self.spin_pgk.setStyleSheet(STYLE_INPUT)
        self.spin_pgk.setDecimals(2)
        self.spin_pgk.setValue(4.0) 
        
        self.spin_bs = AntiScrollSpinBox()
        self.spin_bs.setStyleSheet(STYLE_INPUT)
        self.spin_bs.setDecimals(2)
        self.spin_bs.setValue(4.0)  
        
        self.spin_essay = AntiScrollSpinBox()
        self.spin_essay.setStyleSheet(STYLE_INPUT)
        self.spin_essay.setDecimals(2)
        self.spin_essay.setValue(15.33) 
        
        form_layout.addRow("Bobot Pilihan Ganda [PG]:", self.spin_pg)
        form_layout.addRow("Bobot PG Kompleks [PGK]:", self.spin_pgk)
        form_layout.addRow("Bobot Benar Salah [BS]:", self.spin_bs)
        form_layout.addRow("Bobot Soal [ESSAY]:", self.spin_essay)
        
        layout.addLayout(form_layout)
        
        self.buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        self.buttons.setStyleSheet(STYLE_BTN_PRIMARY)
        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)
        layout.addWidget(self.buttons)

    def get_bobot(self):
        return {
            "PG": self.spin_pg.value(),
            "PGK": self.spin_pgk.value(),
            "BS": self.spin_bs.value(),
            "ESSAY": self.spin_essay.value()
        }

# ================= FLASK SERVER & DATABASE MULTI-FILE =================
app_flask = Flask(__name__)
PROCTOR_PASSWORD = "admin123"
DATA_UJIAN = {}  
AKUN_SISWA = {}
HASIL_SISWA = {}
DAFTAR_FILE_DB = [] 

JAWABAN_SEMENTARA = {}
FLAG_RESET = set()
AUTOSAVE_FILE = os.path.abspath("autosave_jawaban.json")
HASIL_FILE = os.path.abspath("hasil_ujian_permanen.json")
kunci_file = threading.Lock() 

def load_autosave():
    global JAWABAN_SEMENTARA
    if os.path.exists(AUTOSAVE_FILE):
        try:
            with open(AUTOSAVE_FILE, 'r') as f: JAWABAN_SEMENTARA = json.load(f)
        except: JAWABAN_SEMENTARA = {}

def load_hasil():
    global HASIL_SISWA
    if os.path.exists(HASIL_FILE):
        try:
            with open(HASIL_FILE, 'r') as f: HASIL_SISWA = json.load(f)
        except: HASIL_SISWA = {}

def save_hasil():
    try:
        with open(HASIL_FILE, 'w') as f: json.dump(HASIL_SISWA, f, indent=4)
    except: pass

def init_db():
    global DAFTAR_FILE_DB
    default_db = os.path.abspath("database_ujian_cbt.json")
    DAFTAR_FILE_DB = [default_db]
    if not os.path.exists(default_db):
        with open(default_db, 'w') as f: json.dump({"proctor_password": "admin123", "paket_ujian": {}, "akun_siswa": {}}, f)
    reload_all_dbs()
    load_autosave() 
    load_hasil() 

def reload_all_dbs():
    global DATA_UJIAN, AKUN_SISWA, PROCTOR_PASSWORD
    new_data = {}
    new_akun = {}
    for fpath in DAFTAR_FILE_DB:
        if os.path.exists(fpath):
            try:
                with open(fpath, 'r') as f:
                    d = json.load(f)
                    if d.get("proctor_password") and PROCTOR_PASSWORD == "admin123": PROCTOR_PASSWORD = d.get("proctor_password")
                    for pid, pdata in d.get("paket_ujian", {}).items():
                        unik_id = f"{fpath}||{pid}"
                        pdata['_file_asal'] = fpath
                        pdata['_pid_asli'] = pid
                        new_data[unik_id] = pdata
                    for nis, adata in d.get("akun_siswa", {}).items(): new_akun[nis] = adata
            except: pass
    DATA_UJIAN = new_data
    AKUN_SISWA = new_akun

def save_all_dbs():
    for fpath in DAFTAR_FILE_DB:
        paket_untuk_file = {}
        for unik_id, pdata in DATA_UJIAN.items():
            if pdata.get('_file_asal') == fpath:
                clean = dict(pdata)
                pid_asli = clean.pop('_pid_asli')
                clean.pop('_file_asal')
                paket_untuk_file[pid_asli] = clean
        try:
            with open(fpath, 'r') as f: d = json.load(f)
        except: d = {}
            
        d['proctor_password'] = PROCTOR_PASSWORD
        d['paket_ujian'] = paket_untuk_file
        d['akun_siswa'] = AKUN_SISWA 
        
        with open(fpath, 'w') as f: json.dump(d, f, indent=4)

@app_flask.route('/api/cek_password', methods=['POST'])
def cek_password():
    if request.json.get('password') == PROCTOR_PASSWORD: return jsonify({"status": "sukses"})
    return jsonify({"status": "error", "pesan": "Password salah!"})

@app_flask.route('/api/login_siswa', methods=['POST'])
def login_siswa():
    d = request.json
    nis = d.get('nis', '').strip()
    password = d.get('password', '').strip()

    if nis not in AKUN_SISWA: return jsonify({"status": "error", "pesan": "NIS tidak ditemukan. Hubungi Proktor!"})
    if AKUN_SISWA[nis]['password'] != password: return jsonify({"status": "error", "pesan": "Password salah!"})
    
    kunci_login = f"{nis}_LOGIN"
    with kunci_file:
        if kunci_login not in JAWABAN_SEMENTARA:
            JAWABAN_SEMENTARA[kunci_login] = {"jawaban": {}, "terjawab": 0, "status": "Di Beranda"}
        try:
            with open(AUTOSAVE_FILE, 'w') as f: json.dump(JAWABAN_SEMENTARA, f)
        except: pass
    
    return jsonify({"status": "sukses", "nama": AKUN_SISWA[nis]['nama'], "kelas": AKUN_SISWA[nis]['kelas']})

@app_flask.route('/api/auth_soal', methods=['POST'])
def auth_soal():
    token = request.json.get('token')
    nis = request.json.get('nis', '')
    
    paket = next((p for p in DATA_UJIAN.values() if p.get('token') == token), None)
    if not paket: return jsonify({"status": "error", "pesan": "Token ujian tidak ditemukan!"})
    if not paket.get('aktif'): return jsonify({"status": "error", "pesan": "Ujian belum diaktifkan!"})
    if len(paket['soal']) == 0: return jsonify({"status": "error", "pesan": "Belum ada soal!"})
    
    kunci_login = f"{nis}_LOGIN"
    kunci_autosave = f"{nis}_{token}"
    
    with kunci_file:
        if kunci_login in JAWABAN_SEMENTARA: del JAWABAN_SEMENTARA[kunci_login]
        if kunci_autosave not in JAWABAN_SEMENTARA:
            JAWABAN_SEMENTARA[kunci_autosave] = {"jawaban": {}, "terjawab": 0}
        try:
            with open(AUTOSAVE_FILE, 'w') as f: json.dump(JAWABAN_SEMENTARA, f)
        except: pass

    jwb_data = JAWABAN_SEMENTARA.get(kunci_autosave, {})
    jawaban_lama = jwb_data.get("jawaban", {}) if isinstance(jwb_data, dict) else jwb_data

    return jsonify({
        "status": "sukses", 
        "mapel": paket['mapel'], 
        "kelas": paket['kelas'],
        "proctor_pwd": PROCTOR_PASSWORD,
        "soal": [{k:v for k,v in s.items() if k not in ['kunci', '_file_asal', '_pid_asli']} for s in paket['soal']],
        "jawaban_tersimpan": jawaban_lama 
    })

@app_flask.route('/api/cek_status_siswa', methods=['POST'])
def cek_status_siswa():
    d = request.json
    nis = d.get('nis')
    if nis: WAKTU_AKTIF_SISWA[nis] = time.time()
    token = d.get('token', 'LOGIN')
    kunci = f"{nis}_{token}"
    
    if kunci in FLAG_RESET:
        FLAG_RESET.remove(kunci)
        return jsonify({"status": "kick", "action": "reset"})
    return jsonify({"status": "aman"})

@app_flask.route('/api/autosave', methods=['POST'])
def autosave():
    data = request.json
    nis = data.get('nis')
    if nis: WAKTU_AKTIF_SISWA[nis] = time.time()
    token = data.get('token')
    jawaban = data.get('jawaban')
    terjawab = data.get('terjawab', 0)
    kunci = f"{nis}_{token}"
    
    if kunci in FLAG_RESET:
        FLAG_RESET.remove(kunci)
        return jsonify({"status": "sukses", "action": "reset"})
    
    if nis and token:
        try:
            with kunci_file:
                JAWABAN_SEMENTARA[kunci] = {"jawaban": jawaban, "terjawab": terjawab}
                with open(AUTOSAVE_FILE, 'w') as f: json.dump(JAWABAN_SEMENTARA, f)
        except: pass
            
    return jsonify({"status": "sukses"})

@app_flask.route('/api/submit', methods=['POST'])
def submit_jawaban():
    d = request.json
    token = d.get('token')
    nama = d.get('nama')
    paket = next((p for p in DATA_UJIAN.values() if p.get('token') == token), None)
    if not paket: return jsonify({"status": "error"})
    
    skor = 0.0
    for s in paket['soal']:
        sid = str(s['id'])
        if sid in d['jawaban']:
            jwb = d['jawaban'][sid]
            bobot = float(s.get('bobot', 10.0))
            if s['tipe'] == 'PG' and jwb == s['kunci']: skor += bobot
            elif s['tipe'] == 'PGK' and isinstance(jwb, list) and sorted(jwb) == sorted(s['kunci']): skor += bobot
            elif s['tipe'] == 'BS' and isinstance(jwb, list) and jwb == s['kunci']: skor += bobot
            
    HASIL_SISWA[f"{nama}_{token}"] = {"nama": nama, "kelas": paket['kelas'], "mapel": paket['mapel'], "token": token, "skor": skor, "detail": d['jawaban']}
    save_hasil()
    
    nis = next((k for k, v in AKUN_SISWA.items() if v['nama'] == nama), "")
    kunci_autosave = f"{nis}_{token}"
    if kunci_autosave in JAWABAN_SEMENTARA:
        del JAWABAN_SEMENTARA[kunci_autosave]
        try:
            with open(AUTOSAVE_FILE, 'w') as f: json.dump(JAWABAN_SEMENTARA, f)
        except: pass
        
    return jsonify({"status": "sukses"})

def run_server():
    app_flask.run(host='0.0.0.0', port=5000, debug=False, use_reloader=False, threaded=True)

# ================= GURU APP GUI =================
class GuruApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Server Proktor CBT - SMA Islam Darussalam (v1.0.1)")
        
        ikon_path = dapatkan_path_file("logo.ico")
        if not os.path.exists(ikon_path):
            ikon_path = dapatkan_path_file("logo.jpg")
        if os.path.exists(ikon_path):
            self.setWindowIcon(QIcon(ikon_path))
            
        self.resize(1240, 820)
        self.setStyleSheet(STYLE_GLOBAL)
        
        init_db()
        self.edit_id = None
        self.input_dinamis = []
        self._last_live_snapshot = None
        self._last_hasil_snapshot = None
        self._last_stats_snapshot = None

        widget_utama = QWidget()
        self.setCentralWidget(widget_utama)
        layout_root = QHBoxLayout(widget_utama)
        layout_root.setContentsMargins(14, 14, 14, 14)
        layout_root.setSpacing(14)

        # ===== SIDEBAR KIRI GELAP LEMBUT (ANTI SILAU) =====
        sidebar = QFrame()
        sidebar.setFixedWidth(245)
        sidebar.setStyleSheet("""
            QFrame {
                background-color: #1E293B;
                border-radius: 14px;
                border: 1px solid #0F172A;
            }
        """)
        ly_side = QVBoxLayout(sidebar)
        ly_side.setContentsMargins(14, 18, 14, 16)
        ly_side.setSpacing(6)

        # Brand Sekolah di Sidebar
        ly_brand = QHBoxLayout()
        ly_brand.setSpacing(10)
        lbl_logo = QLabel()
        lbl_logo.setStyleSheet("background: transparent; border: none;")
        logo_display = dapatkan_path_file("logo.jpg")
        if not os.path.exists(logo_display):
            logo_display = ikon_path
        if os.path.exists(logo_display):
            pix = QPixmap(logo_display)
            lbl_logo.setPixmap(pix.scaled(38, 38, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
            ly_brand.addWidget(lbl_logo)

        ly_brand_txt = QVBoxLayout()
        ly_brand_txt.setSpacing(1)
        lbl_app = QLabel("CBT Proktor")
        lbl_app.setFont(QFont("Segoe UI", 13, QFont.Weight.Bold))
        lbl_app.setStyleSheet("color: #F8FAFC; border: none; background: transparent;")
        lbl_sch = QLabel("SMA Islam Darussalam")
        lbl_sch.setFont(QFont("Segoe UI", 9))
        lbl_sch.setStyleSheet("color: #94A3B8; border: none; background: transparent;")
        ly_brand_txt.addWidget(lbl_app)
        ly_brand_txt.addWidget(lbl_sch)
        ly_brand.addLayout(ly_brand_txt)
        ly_side.addLayout(ly_brand)

        garis = QFrame()
        garis.setFrameShape(QFrame.Shape.HLine)
        garis.setStyleSheet("background-color: #334155; border: none; max-height: 1px; margin: 6px 0;")
        ly_side.addWidget(garis)

        # Tombol Navigasi Sidebar
        self.nav_group = QButtonGroup(self)
        self.nav_group.setExclusive(True)
        menu_items = [
            ("📝  Bank Soal", 0),
            ("⚙️  Kontrol Ujian", 1),
            ("🟢  Live Monitor", 2),
            ("🏆  Rekap Hasil", 3),
            ("👥  Data Akun", 4),
        ]
        for teks, idx in menu_items:
            btn_nav = QPushButton(teks)
            btn_nav.setCheckable(True)
            btn_nav.setStyleSheet(STYLE_NAV_BTN)
            btn_nav.setCursor(Qt.CursorShape.PointingHandCursor)
            btn_nav.setFocusPolicy(Qt.FocusPolicy.NoFocus)
            if idx == 0:
                btn_nav.setChecked(True)
            self.nav_group.addButton(btn_nav, idx)
            ly_side.addWidget(btn_nav)

        ly_side.addStretch()

        # Kartu Info IP Server di Bawah Sidebar (Otomatis Update Saat Pindah Wi-Fi)
        box_ip = QFrame()
        box_ip.setStyleSheet("""
            QFrame {
                background-color: #0F172A;
                border-radius: 12px;
                border: 1px solid #334155;
            }
        """)
        ly_box_ip = QVBoxLayout(box_ip)
        ly_box_ip.setContentsMargins(12, 10, 12, 10)
        ly_box_ip.setSpacing(6)

        self.lbl_srv_status = QLabel("🟢 Server Aktif (Port 5000)")
        self.lbl_srv_status.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        self.lbl_srv_status.setStyleSheet("color: #34D399; border: none; background: transparent;")
        ly_box_ip.addWidget(self.lbl_srv_status)

        self.ip_server_aktif = ""
        self.lbl_ip_side = QLabel("IP: Mendeteksi...")
        self.lbl_ip_side.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        self.lbl_ip_side.setStyleSheet("color: #F1F5F9; border: none; background: transparent;")
        ly_box_ip.addWidget(self.lbl_ip_side)

        self.btn_salin_ip = QPushButton("📋 Salin IP Server")
        self.btn_salin_ip.setStyleSheet(STYLE_BTN_PRIMARY)
        self.btn_salin_ip.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_salin_ip.clicked.connect(self.salin_ip_server)
        ly_box_ip.addWidget(self.btn_salin_ip)

        ly_side.addWidget(box_ip)
        layout_root.addWidget(sidebar)

        # ===== AREA KONTEN UTAMA (KANAN) =====
        self.pages = SmoothStackedWidget()
        layout_root.addWidget(self.pages, 1)

        self.tab_soal = QWidget()
        self.tab_server = QWidget()
        self.tab_live = QWidget()
        self.tab_hasil = QWidget()
        self.tab_siswa = QWidget() 
        
        self.pages.addWidget(self.tab_soal)
        self.pages.addWidget(self.tab_server)
        self.pages.addWidget(self.tab_live)
        self.pages.addWidget(self.tab_hasil)
        self.pages.addWidget(self.tab_siswa)

        self.nav_group.idClicked.connect(self.pages.slide_ke)

        self.setup_tab_soal()
        self.setup_tab_server()
        self.setup_tab_live()
        self.setup_tab_hasil()
        self.setup_tab_siswa()

        self.perbarui_status_ip()
        self.update_tabel_paket()
        self.update_tabel_hasil_dan_live()
        self.rapikan_tombol(self)
        
        self.timer_hasil = QTimer()
        self.timer_hasil.timeout.connect(self.siklus_pembaruan_latar)
        self.timer_hasil.start(2500)

        threading.Thread(target=run_server, daemon=True).start()

    def siklus_pembaruan_latar(self):
        self.perbarui_status_ip()
        self.update_tabel_hasil_dan_live()

    def perbarui_status_ip(self):
        ip_baru = dapatkan_ip_lokal()
        if ip_baru != self.ip_server_aktif:
            self.ip_server_aktif = ip_baru
            if ip_baru == "Tidak Terhubung":
                self.lbl_srv_status.setText("🟠 Wi-Fi Terputus")
                self.lbl_srv_status.setStyleSheet("color: #FBBF24; border: none; background: transparent;")
                self.lbl_ip_side.setText("IP: Menunggu Wi-Fi...")
                self.btn_salin_ip.setEnabled(False)
            else:
                self.lbl_srv_status.setText("🟢 Server Aktif (Port 5000)")
                self.lbl_srv_status.setStyleSheet("color: #34D399; border: none; background: transparent;")
                self.lbl_ip_side.setText(f"IP: {ip_baru}")
                self.btn_salin_ip.setEnabled(True)

    def rapikan_tombol(self, parent):
        for btn in parent.findChildren(QPushButton):
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)

    def buat_kartu_panel(self):
        card = QFrame()
        card.setObjectName("CardPanel")
        card.setStyleSheet(STYLE_CARD)
        return card

    def buat_judul_seksi(self, teks):
        lbl = QLabel(teks)
        lbl.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        lbl.setStyleSheet("color: #0F172A; background: transparent; border: none;")
        return lbl

    def buat_kartu_statistik(self, judul, nilai_awal, warna_aksen):
        kartu = QFrame()
        kartu.setStyleSheet(f"""
            QFrame {{
                background-color: #EEF2F6;
                border-radius: 14px;
                border: 1px solid #C2CEDB;
                border-left: 5px solid {warna_aksen};
            }}
        """)
        ly = QVBoxLayout(kartu)
        ly.setContentsMargins(16, 12, 16, 12)
        ly.setSpacing(2)

        lbl_j = QLabel(judul)
        lbl_j.setStyleSheet("color: #475569; font-size: 9pt; font-weight: bold; border: none; background: transparent;")
        lbl_v = QLabel(nilai_awal)
        lbl_v.setFont(QFont("Segoe UI", 15, QFont.Weight.Bold))
        lbl_v.setStyleSheet(f"color: {warna_aksen}; border: none; background: transparent;")

        ly.addWidget(lbl_j)
        ly.addWidget(lbl_v)
        return kartu, lbl_v

    def salin_ip_server(self):
        if self.ip_server_aktif and self.ip_server_aktif != "Tidak Terhubung":
            QApplication.clipboard().setText(self.ip_server_aktif)
            self.btn_salin_ip.setText("✅ IP Tersalin!")
            QTimer.singleShot(1500, lambda: self.btn_salin_ip.setText("📋 Salin IP Server"))

    # ================= TAB 1: BANK SOAL (SPLIT-VIEW KIRI-KANAN) =================
    def setup_tab_soal(self):
        layout = QVBoxLayout(self.tab_soal)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        card_top = self.buat_kartu_panel()
        ly_top = QHBoxLayout(card_top)
        ly_top.setContentsMargins(16, 12, 16, 12)
        ly_top.setSpacing(10)

        lbl_db = QLabel("Database:")
        lbl_db.setStyleSheet("font-weight: bold; background: transparent; border: none;")
        ly_top.addWidget(lbl_db)

        self.cb_file_db = AntiScrollComboBox()
        self.cb_file_db.setStyleSheet(STYLE_INPUT)
        self.cb_file_db.setMinimumWidth(180)
        self.cb_file_db.currentIndexChanged.connect(self.update_cb_paket)
        ly_top.addWidget(self.cb_file_db)

        btn_db_baru = QPushButton("📄 Baru")
        btn_db_baru.setStyleSheet(STYLE_BTN_SECONDARY)
        btn_db_baru.setToolTip("Buat File Database JSON Baru")
        btn_db_baru.clicked.connect(self.buat_file_db)
        btn_db_buka = QPushButton("📂 Buka")
        btn_db_buka.setStyleSheet(STYLE_BTN_SECONDARY)
        btn_db_buka.setToolTip("Buka File Database JSON")
        btn_db_buka.clicked.connect(self.buka_file_db)
        ly_top.addWidget(btn_db_baru)
        ly_top.addWidget(btn_db_buka)

        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.VLine)
        sep.setStyleSheet("background-color: #C2CEDB; border: none; max-width: 1px; margin: 2px 4px;")
        ly_top.addWidget(sep)

        lbl_pkt = QLabel("Paket:")
        lbl_pkt.setStyleSheet("font-weight: bold; background: transparent; border: none;")
        ly_top.addWidget(lbl_pkt)

        self.cb_paket = AntiScrollComboBox()
        self.cb_paket.setStyleSheet(STYLE_INPUT)
        self.cb_paket.setMinimumWidth(250)
        self.cb_paket.currentIndexChanged.connect(self.muat_tabel_soal)
        ly_top.addWidget(self.cb_paket, 1)

        btn_paket_baru = QPushButton("➕ Paket Baru")
        btn_paket_baru.setStyleSheet(STYLE_BTN_PRIMARY)
        btn_paket_baru.clicked.connect(self.buat_paket)
        ly_top.addWidget(btn_paket_baru)

        layout.addWidget(card_top)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setChildrenCollapsible(False)

        # --- PANEL KIRI: DAFTAR SOAL ---
        card_kiri = self.buat_kartu_panel()
        ly_kiri = QVBoxLayout(card_kiri)
        ly_kiri.setContentsMargins(16, 14, 16, 14)
        ly_kiri.setSpacing(10)

        ly_kiri_hdr = QHBoxLayout()
        ly_kiri_hdr.addWidget(self.buat_judul_seksi("📋 Daftar Soal"))
        ly_kiri_hdr.addStretch()
        btn_import = QPushButton("📥 Import Word")
        btn_import.setStyleSheet(STYLE_BTN_SUCCESS)
        btn_import.clicked.connect(self.import_word)
        ly_kiri_hdr.addWidget(btn_import)
        ly_kiri.addLayout(ly_kiri_hdr)

        self.tabel_soal = SmoothTableWidget(0, 4)
        self.tabel_soal.setStyleSheet(STYLE_TABEL)
        self.tabel_soal.setAlternatingRowColors(True)
        self.tabel_soal.setHorizontalHeaderLabels(["No", "Tipe", "Bobot", "Pertanyaan"])
        self.tabel_soal.verticalHeader().setVisible(False)
        self.tabel_soal.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        self.tabel_soal.setColumnWidth(0, 52)
        self.tabel_soal.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.tabel_soal.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.tabel_soal.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        self.tabel_soal.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.tabel_soal.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.tabel_soal.cellDoubleClicked.connect(lambda r, c: self.edit_soal())
        ly_kiri.addWidget(self.tabel_soal, 1)

        ly_aksi_kiri = QHBoxLayout()
        ly_aksi_kiri.setSpacing(8)
        btn_preview = QPushButton("🔍 Preview")
        btn_preview.setStyleSheet(STYLE_BTN_SECONDARY)
        btn_preview.clicked.connect(self.preview_soal)
        btn_edit = QPushButton("✏️ Edit")
        btn_edit.setStyleSheet(STYLE_BTN_WARNING)
        btn_edit.clicked.connect(self.edit_soal)
        btn_hapus = QPushButton("🗑️ Hapus")
        btn_hapus.setStyleSheet(STYLE_BTN_DANGER)
        btn_hapus.clicked.connect(self.hapus_soal)
        ly_aksi_kiri.addWidget(btn_preview)
        ly_aksi_kiri.addWidget(btn_edit)
        ly_aksi_kiri.addWidget(btn_hapus)
        ly_kiri.addLayout(ly_aksi_kiri)

        # --- PANEL KANAN: FORM INPUT / EDIT SOAL ---
        card_kanan = self.buat_kartu_panel()
        ly_kanan_wrap = QVBoxLayout(card_kanan)
        ly_kanan_wrap.setContentsMargins(16, 14, 10, 14)
        ly_kanan_wrap.setSpacing(8)

        self.lbl_judul_form = self.buat_judul_seksi("✏️ Tambah Soal Baru")
        ly_kanan_wrap.addWidget(self.lbl_judul_form)

        scroll_form = QScrollArea()
        scroll_form.setWidgetResizable(True)
        scroll_form.setStyleSheet("QScrollArea { border: none; background: transparent; }")

        w_form_inner = QWidget()
        w_form_inner.setStyleSheet("background: transparent;")
        ly_form = QVBoxLayout(w_form_inner)
        ly_form.setContentsMargins(0, 2, 8, 6)
        ly_form.setSpacing(10)

        ly_meta = QHBoxLayout()
        ly_meta.setSpacing(12)

        ly_t = QVBoxLayout()
        lbl_t = QLabel("Tipe Soal:")
        lbl_t.setStyleSheet("font-weight: bold; color: #334155; background: transparent;")
        self.cb_tipe = AntiScrollComboBox()
        self.cb_tipe.setStyleSheet(STYLE_INPUT)
        self.cb_tipe.addItems(["PG", "PGK", "BS", "ESSAY"])
        self.cb_tipe.currentTextChanged.connect(self.ref_form)
        ly_t.addWidget(lbl_t)
        ly_t.addWidget(self.cb_tipe)

        ly_b = QVBoxLayout()
        lbl_b = QLabel("Bobot Poin:")
        lbl_b.setStyleSheet("font-weight: bold; color: #334155; background: transparent;")
        self.sb_bobot = AntiScrollSpinBox()
        self.sb_bobot.setStyleSheet(STYLE_INPUT)
        self.sb_bobot.setValue(10.0)
        self.sb_bobot.setMaximum(100.0)
        ly_b.addWidget(lbl_b)
        ly_b.addWidget(self.sb_bobot)

        ly_meta.addLayout(ly_t, 1)
        ly_meta.addLayout(ly_b, 1)
        ly_form.addLayout(ly_meta)

        lbl_wac = QLabel("Wacana / Teks Bacaan (Opsional):")
        lbl_wac.setStyleSheet("font-weight: bold; color: #334155; background: transparent;")
        ly_form.addWidget(lbl_wac)
        self.txt_wacana = RichTextEditor()
        self.txt_wacana.setMinimumHeight(125)
        ly_form.addWidget(self.txt_wacana)

        lbl_pert = QLabel("Pertanyaan:")
        lbl_pert.setStyleSheet("font-weight: bold; color: #334155; background: transparent;")
        ly_form.addWidget(lbl_pert)
        self.txt_soal = RichTextEditor()
        self.txt_soal.setMinimumHeight(135)
        ly_form.addWidget(self.txt_soal)

        self.w_dinamis = QWidget()
        self.w_dinamis.setStyleSheet("background: transparent;")
        self.ly_dinamis = QFormLayout(self.w_dinamis)
        self.ly_dinamis.setContentsMargins(0, 4, 0, 4)
        self.ly_dinamis.setSpacing(8)
        ly_form.addWidget(self.w_dinamis)

        ly_form.addStretch()
        scroll_form.setWidget(w_form_inner)
        ly_kanan_wrap.addWidget(scroll_form, 1)

        ly_btn_simpan = QHBoxLayout()
        self.btn_batal = QPushButton("❌ BATAL EDIT")
        self.btn_batal.setStyleSheet(STYLE_BTN_SECONDARY)
        self.btn_batal.hide()
        self.btn_batal.clicked.connect(self.batal_edit)
        self.btn_simpan = QPushButton("➕ SIMPAN SOAL BARU")
        self.btn_simpan.setStyleSheet(STYLE_BTN_PRIMARY)
        self.btn_simpan.clicked.connect(self.simpan_soal)
        
        ly_btn_simpan.addWidget(self.btn_batal)
        ly_btn_simpan.addStretch()
        ly_btn_simpan.addWidget(self.btn_simpan)
        ly_kanan_wrap.addLayout(ly_btn_simpan)

        splitter.addWidget(card_kiri)
        splitter.addWidget(card_kanan)
        splitter.setSizes([430, 560])
        layout.addWidget(splitter, 1)
        
        self.update_cb_file_db()
        self.ref_form()

    # ================= TAB 2: KONTROL UJIAN =================
    def setup_tab_server(self):
        ly = QVBoxLayout(self.tab_server)
        ly.setContentsMargins(0, 0, 0, 0)
        ly.setSpacing(14)

        ly_cards = QHBoxLayout()
        ly_cards.setSpacing(14)
        k1, self.lbl_stat_paket = self.buat_kartu_statistik("📦 Paket Ujian Aktif", "0 Paket", "#4F46E5")
        k2, self.lbl_stat_online = self.buat_kartu_statistik("🟢 Siswa Online", "0 Siswa", "#059669")
        k3, self.lbl_stat_akun = self.buat_kartu_statistik("👥 Total Akun Siswa", "0 Akun", "#0284C7")
        k4, self.lbl_stat_hasil = self.buat_kartu_statistik("🏆 Hasil Terkumpul", "0 Data", "#D97706")
        ly_cards.addWidget(k1)
        ly_cards.addWidget(k2)
        ly_cards.addWidget(k3)
        ly_cards.addWidget(k4)
        ly.addLayout(ly_cards)
        
        card_pwd = self.buat_kartu_panel()
        ly_pwd_wrap = QVBoxLayout(card_pwd)
        ly_pwd_wrap.setContentsMargins(18, 14, 18, 14)
        ly_pwd_wrap.setSpacing(10)
        ly_pwd_wrap.addWidget(self.buat_judul_seksi("🔐 Keamanan & Password Proktor"))
        
        ly_pwd = QHBoxLayout()
        lbl_pwd = QLabel("Password Keluar Siswa / Kunci Hapus:")
        lbl_pwd.setStyleSheet("background: transparent; border: none; color: #334155; font-weight: bold;")
        ly_pwd.addWidget(lbl_pwd)
        self.ent_pwd = QLineEdit(PROCTOR_PASSWORD)
        self.ent_pwd.setStyleSheet(STYLE_INPUT)
        self.ent_pwd.setMaximumWidth(260)
        self.ent_pwd.setEchoMode(QLineEdit.EchoMode.Password)
        btn_pwd = QPushButton("💾 Simpan ke Semua File")
        btn_pwd.setStyleSheet(STYLE_BTN_PRIMARY)
        btn_pwd.clicked.connect(self.simpan_pwd)
        ly_pwd.addWidget(self.ent_pwd)
        ly_pwd.addWidget(btn_pwd)
        ly_pwd.addStretch()
        ly_pwd_wrap.addLayout(ly_pwd)
        ly.addWidget(card_pwd)
        
        card_paket = self.buat_kartu_panel()
        ly_paket = QVBoxLayout(card_paket)
        ly_paket.setContentsMargins(18, 16, 18, 16)
        ly_paket.setSpacing(12)

        ly_pkt_top = QHBoxLayout()
        ly_pkt_top.addWidget(self.buat_judul_seksi("📦 Status Aktivasi Paket Ujian"))
        ly_pkt_top.addStretch()
        btn_on = QPushButton("▶ AKTIFKAN UJIAN")
        btn_on.setStyleSheet(STYLE_BTN_SUCCESS)
        btn_on.clicked.connect(lambda: self.tog_ujian(True))
        btn_off = QPushButton("⏸ TUTUP UJIAN")
        btn_off.setStyleSheet(STYLE_BTN_DANGER)
        btn_off.clicked.connect(lambda: self.tog_ujian(False))
        ly_pkt_top.addWidget(btn_on)
        ly_pkt_top.addWidget(btn_off)
        ly_paket.addLayout(ly_pkt_top)
        
        self.tabel_paket = SmoothTableWidget(0, 7)
        self.tabel_paket.setStyleSheet(STYLE_TABEL)
        self.tabel_paket.setAlternatingRowColors(True)
        self.tabel_paket.setHorizontalHeaderLabels(["File Sumber", "Mapel", "Kelas", "Token", "Jml Soal", "Status", "UnikID"])
        
        self.tabel_paket.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.tabel_paket.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.tabel_paket.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.tabel_paket.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self.tabel_paket.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        self.tabel_paket.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)
        
        self.tabel_paket.setColumnHidden(6, True) 
        self.tabel_paket.verticalHeader().setVisible(False)
        self.tabel_paket.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.tabel_paket.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        ly_paket.addWidget(self.tabel_paket, 1)
        
        ly.addWidget(card_paket, 1)

    # ================= TAB 3: LIVE MONITOR =================
    def setup_tab_live(self):
        layout_tab = QVBoxLayout(self.tab_live)
        layout_tab.setContentsMargins(0, 0, 0, 0)
        
        card_live = self.buat_kartu_panel()
        ly_live = QVBoxLayout(card_live)
        ly_live.setContentsMargins(18, 16, 18, 16)
        ly_live.setSpacing(12)

        ly_live.addWidget(self.buat_judul_seksi("🟢 Live Monitor Progres Siswa (Real-Time)"))
        
        self.tabel_live = SmoothTableWidget(0, 6)
        self.tabel_live.setStyleSheet(STYLE_TABEL)
        self.tabel_live.setAlternatingRowColors(True)
        self.tabel_live.setHorizontalHeaderLabels(["NIS / Username", "Token", "Terjawab", "Total Soal", "Progres (%)", "Status Koneksi"])
        
        self.tabel_live.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.tabel_live.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.tabel_live.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.tabel_live.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self.tabel_live.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.Stretch)
        self.tabel_live.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)
        self.tabel_live.verticalHeader().setVisible(False)
        self.tabel_live.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.tabel_live.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        ly_live.addWidget(self.tabel_live, 1)
        
        ly_bawah = QHBoxLayout()
        btn_kick = QPushButton("🔄 KICK / FORCE LOGOUT SISWA (PROGRES AMAN)")
        btn_kick.setStyleSheet(STYLE_BTN_DANGER)
        btn_kick.clicked.connect(self.kick_siswa)
        
        btn_reset_autosave = QPushButton("🧹 BERSIHKAN AUTO-SAVE SEMENTARA (Sesi Baru)")
        btn_reset_autosave.setStyleSheet(STYLE_BTN_WARNING)
        btn_reset_autosave.clicked.connect(self.hapus_autosave)
        
        ly_bawah.addWidget(btn_kick)
        ly_bawah.addStretch()
        ly_bawah.addWidget(btn_reset_autosave)
        
        ly_live.addLayout(ly_bawah)
        layout_tab.addWidget(card_live)

    # ================= TAB 4: REKAP HASIL =================
    def setup_tab_hasil(self):
        layout_tab = QVBoxLayout(self.tab_hasil)
        layout_tab.setContentsMargins(0, 0, 0, 0)
        
        card_hasil = self.buat_kartu_panel()
        ly_hasil = QVBoxLayout(card_hasil)
        ly_hasil.setContentsMargins(18, 16, 18, 16)
        ly_hasil.setSpacing(12)
        
        ly_h_filter = QHBoxLayout()
        ly_h_filter.addWidget(self.buat_judul_seksi("🏆 Rekap Hasil Ujian"))
        ly_h_filter.addStretch()
        lbl_fp = QLabel("Filter Paket:")
        lbl_fp.setStyleSheet("background: transparent; border: none; font-weight: bold; color: #334155;")
        ly_h_filter.addWidget(lbl_fp)
        self.cb_filter_hasil = AntiScrollComboBox()
        self.cb_filter_hasil.setStyleSheet(STYLE_INPUT)
        self.cb_filter_hasil.addItem("Semua Paket dari Semua File")
        self.cb_filter_hasil.currentTextChanged.connect(self.update_tabel_hasil_langsung)
        self.cb_filter_hasil.setMinimumWidth(340)
        ly_h_filter.addWidget(self.cb_filter_hasil)
        ly_hasil.addLayout(ly_h_filter)

        self.tabel_hasil = SmoothTableWidget(0, 4)
        self.tabel_hasil.setStyleSheet(STYLE_TABEL)
        self.tabel_hasil.setAlternatingRowColors(True)
        self.tabel_hasil.setHorizontalHeaderLabels(["Nama Lengkap", "Kelas", "Mapel", "Skor Akhir"])
        
        self.tabel_hasil.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.tabel_hasil.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.tabel_hasil.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.tabel_hasil.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self.tabel_hasil.verticalHeader().setVisible(False)
        self.tabel_hasil.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.tabel_hasil.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.tabel_hasil.cellDoubleClicked.connect(self.cek_detail_essay)
        ly_hasil.addWidget(self.tabel_hasil, 1)
        
        ly_h_hasil = QHBoxLayout()
        btn_csv = QPushButton("📥 UNDUH HASIL CSV")
        btn_csv.setStyleSheet(STYLE_BTN_SUCCESS)
        btn_csv.clicked.connect(self.unduh_csv)
        btn_analisis = QPushButton("📊 ANALISIS SOAL CSV")
        btn_analisis.setStyleSheet(STYLE_BTN_PRIMARY)
        btn_analisis.clicked.connect(self.unduh_analisis_soal)
        
        btn_hapus_siswa_hasil = QPushButton("🗑️ HAPUS 1 SISWA")
        btn_hapus_siswa_hasil.setStyleSheet(STYLE_BTN_WARNING)
        btn_hapus_siswa_hasil.clicked.connect(self.hapus_satu_hasil)
        
        btn_hapus_hasil = QPushButton("🗑️ HAPUS SEMUA HASIL PAKET")
        btn_hapus_hasil.setStyleSheet(STYLE_BTN_DANGER)
        btn_hapus_hasil.clicked.connect(self.hapus_semua_hasil_paket)

        ly_h_hasil.addWidget(btn_csv)
        ly_h_hasil.addWidget(btn_analisis)
        ly_h_hasil.addStretch()
        ly_h_hasil.addWidget(btn_hapus_siswa_hasil)
        ly_h_hasil.addWidget(btn_hapus_hasil)
        ly_hasil.addLayout(ly_h_hasil)
        
        layout_tab.addWidget(card_hasil)

    # ================= TAB 5: DATA AKUN SISWA =================
    def setup_tab_siswa(self):
        ly = QVBoxLayout(self.tab_siswa)
        ly.setContentsMargins(0, 0, 0, 0)
        
        card_akun = self.buat_kartu_panel()
        ly_akun = QVBoxLayout(card_akun)
        ly_akun.setContentsMargins(18, 16, 18, 16)
        ly_akun.setSpacing(12)
        
        ly_top = QHBoxLayout()
        ly_top.addWidget(self.buat_judul_seksi("👥 Manajemen Data Akun Siswa"))
        ly_top.addStretch()

        btn_tambah = QPushButton("➕ Tambah Akun")
        btn_tambah.setStyleSheet(STYLE_BTN_SUCCESS)
        btn_tambah.clicked.connect(self.tambah_akun_manual)
        
        btn_edit = QPushButton("✏️ Edit Akun")
        btn_edit.setStyleSheet(STYLE_BTN_WARNING)
        btn_edit.clicked.connect(self.edit_akun_manual)
        
        btn_hapus = QPushButton("🗑️ Hapus Akun")
        btn_hapus.setStyleSheet(STYLE_BTN_DANGER)
        btn_hapus.clicked.connect(self.hapus_akun_manual)
        
        ly_top.addWidget(btn_tambah)
        ly_top.addWidget(btn_edit)
        ly_top.addWidget(btn_hapus)
        ly_akun.addLayout(ly_top)
        
        self.tabel_akun = SmoothTableWidget(0, 4)
        self.tabel_akun.setStyleSheet(STYLE_TABEL)
        self.tabel_akun.setAlternatingRowColors(True)
        self.tabel_akun.setHorizontalHeaderLabels(["NIS / Username", "Nama Lengkap", "Kelas", "Password Akun"])
        
        self.tabel_akun.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.tabel_akun.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.tabel_akun.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.tabel_akun.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        self.tabel_akun.verticalHeader().setVisible(False)
        self.tabel_akun.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.tabel_akun.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        ly_akun.addWidget(self.tabel_akun, 1)
        
        ly.addWidget(card_akun)
        self.update_tabel_akun()

    # ================= FUNGSI & LOGIKA =================
    def ref_form(self):
        while self.ly_dinamis.count():
            child = self.ly_dinamis.takeAt(0)
            if child.widget(): child.widget().deleteLater()
            elif child.layout(): 
                while child.layout().count():
                    c = child.layout().takeAt(0)
                    if c.widget(): c.widget().deleteLater()
                child.layout().deleteLater()
            
        t = self.cb_tipe.currentText()
        self.input_dinamis.clear()
        self.cek_kunci = []
        
        if t == "PG":
            for l in ['A','B','C','D','E']:
                ent = QLineEdit()
                ent.setStyleSheet(STYLE_INPUT)
                self.ly_dinamis.addRow(f"Opsi {l}:", ent)
                self.input_dinamis.append(ent)
                
            self.cb_kunci_pg = AntiScrollComboBox()
            self.cb_kunci_pg.setStyleSheet(STYLE_INPUT)
            self.cb_kunci_pg.addItems(['A','B','C','D','E'])
            self.ly_dinamis.addRow("Kunci Benar:", self.cb_kunci_pg)
            
        elif t in ["PGK", "BS"]:
            for i in range(4):
                ly_baris = QHBoxLayout()
                ent = QLineEdit()
                ent.setStyleSheet(STYLE_INPUT)
                self.input_dinamis.append(ent)
                ly_baris.addWidget(ent)
                
                if t == "PGK":
                    chk = QCheckBox("Benar")
                    self.cek_kunci.append(chk)
                    ly_baris.addWidget(chk)
                else:
                    cb = AntiScrollComboBox()
                    cb.setStyleSheet(STYLE_INPUT)
                    cb.addItems(["B", "S"])
                    self.cek_kunci.append(cb)
                    ly_baris.addWidget(cb)
                self.ly_dinamis.addRow(f"Pernyataan {i+1}:", ly_baris)
        elif t == "ESSAY":
            lbl = QLabel("(Soal Essay dinilai manual oleh Guru)")
            lbl.setStyleSheet("color: #3730A3; font-style: italic; background: transparent;")
            self.ly_dinamis.addRow("", lbl)

    def import_word(self):
        if not DOCX_AVAILABLE:
            return QMessageBox.warning(self, "Library Belum Terpasang", "Fitur ini membutuhkan 'python-docx'.\nJalankan perintah: pip install python-docx")
        
        unik_id = self.cb_paket.currentData()
        if not unik_id: return QMessageBox.warning(self, "Error", "Pilih Paket Ujian terlebih dahulu!")
            
        dialog = DialogSettingBobot(self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
            
        bobot_diatur = dialog.get_bobot()
            
        fp, _ = QFileDialog.getOpenFileName(self, "Import Word (.docx)", "", "Word Document (*.docx)")
        if not fp: return
        
        try:
            doc = docx.Document(fp)
            soal_list = DATA_UJIAN[unik_id]['soal']
            exist_ids = [x['id'] for x in soal_list]
            next_id = max(exist_ids) + 1 if exist_ids else 1
            
            curr = None
            mode_input = "biasa"
            wacana_temp = []
            soal_temp = []

            for para in doc.paragraphs:
                txt = para.text.strip() 
                
                align_html = "left"
                if para.alignment is not None:
                    if para.alignment == 1: align_html = "center"
                    elif para.alignment == 2: align_html = "right"
                    elif para.alignment == 3: align_html = "justify"
                
                html_teks = ""
                kumpulan_gambar_html = ""
                
                for run in para.runs:
                    xml_str = run._element.xml
                    if 'r:embed=' in xml_str or 'r:id=' in xml_str:
                        match = re.search(r'(?:r:embed|r:id)="([^"]+)"', xml_str)
                        if match:
                            rel_id = match.group(1)
                            if rel_id in doc.part.related_parts:
                                part = doc.part.related_parts[rel_id]
                                if "image" in part.content_type:
                                    img_b64 = base64.b64encode(part.blob).decode('utf-8')
                                    kumpulan_gambar_html += f'<br><img src="data:image/png;base64,{img_b64}" width="400"><br>'
                    
                    t = run.text.replace("&", "&").replace("<", "<").replace(">", ">").replace("\n", "<br>")
                    if not t: continue
                    if run.bold: t = f"<b>{t}</b>"
                    if run.italic: t = f"<i>{t}</i>"
                    if run.underline: t = f"<u>{t}</u>"
                    html_teks += t
                    
                html_teks = html_teks.strip()
                
                if txt and txt[0].isdigit() and "." in txt[:4] and any(t in txt for t in ["[PG]", "[BS]", "[PGK]", "[ESSAY]"]):
                    if curr: 
                        curr['bacaan'] = "".join(wacana_temp)
                        curr['soal'] = "".join(soal_temp)
                        soal_list.append(curr)
                        
                    wacana_temp, soal_temp = [], []
                    mode_input = "biasa"
                    
                    tipe = "PG"
                    for t in ["PGK", "BS", "ESSAY", "PG"]:
                        if f"[{t}]" in txt: 
                            tipe = t
                            break
                    
                    clean_html = re.sub(r'^(?:<[^>]+>)*\d+\.(?:<[^>]+>)*\s*(?:<[^>]+>)*\[(?:PG|BS|PGK|ESSAY)\](?:<[^>]+>)*\s*', '', html_teks, flags=re.IGNORECASE)
                    bobot_soal = bobot_diatur.get(tipe, 10.0)
                    
                    curr = {
                        "id": next_id, "tipe": tipe, "bobot": bobot_soal, 
                        "bacaan": "", "soal": "", "gambar": "", "sumber_gambar": "" 
                    }
                    if tipe == "PG": curr["opsi"], curr["kunci"] = {}, "A"
                    elif tipe in ["PGK", "BS"]: curr["pernyataan"], curr["kunci"] = [], []
                    next_id += 1
                    
                    if clean_html: soal_temp.append(f"<p style=\"font-family:'Times New Roman'; font-size:12pt; margin: 0; text-align:{align_html};\">{clean_html}</p>")
                    if kumpulan_gambar_html: soal_temp.append(kumpulan_gambar_html)
                        
                elif curr:
                    if "[SUMBER:" in txt:
                        sumber_teks = txt[txt.find("[SUMBER:") + 8 : txt.find("]")].strip()
                        html_teks = re.sub(r'(?:<[^>]+>)*\[SUMBER:[^\]]+\](?:<[^>]+>)*', f"<br><i style='color:gray; font-size:10pt;'>Sumber: {sumber_teks}</i><br>", html_teks, flags=re.IGNORECASE)
                        
                    if "[WACANA]" in txt:
                        mode_input = "wacana"
                        html_teks = re.sub(r'^(?:<[^>]+>)*\[WACANA\](?:<[^>]+>)*\s*', '', html_teks, flags=re.IGNORECASE)
                    elif "[SOAL]" in txt:
                        mode_input = "soal"
                        html_teks = re.sub(r'^(?:<[^>]+>)*\[SOAL\](?:<[^>]+>)*\s*', '', html_teks, flags=re.IGNORECASE)
                    
                    is_kunci = txt.lower().startswith("kunci:")
                    is_opsi = curr["tipe"] == "PG" and len(txt) > 2 and txt[0] in "ABCDE" and txt[1] in ".)"
                    is_pernyataan = txt.startswith("-") and curr["tipe"] in ["BS", "PGK"]
                    
                    if is_opsi:
                        clean_html = re.sub(r'^(?:<[^>]+>)*[A-E][.)](?:<[^>]+>)*\s*', '', html_teks, count=1, flags=re.IGNORECASE)
                        curr["opsi"][txt[0].upper()] = clean_html
                        mode_input = "biasa"
                        if kumpulan_gambar_html: soal_temp.append(kumpulan_gambar_html)
                    elif is_kunci:
                        curr["kunci"] = txt.split(":", 1)[1].strip().upper()
                        mode_input = "biasa"
                        if kumpulan_gambar_html: soal_temp.append(kumpulan_gambar_html)
                    elif is_pernyataan:
                        clean_html = re.sub(r'^(?:<[^>]+>)*-(?:<[^>]+>)*\s*', '', html_teks, count=1)
                        parts = txt.split("[")
                        if len(parts) > 1:
                            val = parts[-1].replace("]", "").strip().upper()
                            if curr["tipe"] == "PGK" and val == "BENAR": curr["kunci"].append(len(curr["pernyataan"]))
                            elif curr["tipe"] == "BS": curr["kunci"].append(val)
                            clean_html = re.sub(r'(?:<[^>]+>)*\[(?:BENAR|SALAH|B|S)\](?:<[^>]+>)*\s*$', '', clean_html, flags=re.IGNORECASE)
                        curr["pernyataan"].append(clean_html)
                        mode_input = "biasa"
                        if kumpulan_gambar_html: soal_temp.append(kumpulan_gambar_html)
                    elif html_teks or kumpulan_gambar_html:
                        teks_gabungan = ""
                        if html_teks: teks_gabungan += f"<p style=\"font-family:'Times New Roman'; font-size:12pt; margin: 0; text-align:{align_html};\">{html_teks}</p>"
                        if kumpulan_gambar_html: teks_gabungan += kumpulan_gambar_html
                            
                        if mode_input == "wacana": wacana_temp.append(teks_gabungan)
                        else: soal_temp.append(teks_gabungan)
                            
            if curr:
                curr['bacaan'] = "".join(wacana_temp)
                curr['soal'] = "".join(soal_temp)
                soal_list.append(curr)
                
            save_all_dbs()
            self.muat_tabel_soal()
            self.update_tabel_paket()
            QMessageBox.information(self, "Sukses", "Impor Berhasil! Periksa kembali soal dan bobot yang diimpor.")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Gagal membaca file Word:\n{str(e)}")

    def update_cb_file_db(self):
        self.cb_file_db.blockSignals(True)
        self.cb_file_db.clear()
        for fp in DAFTAR_FILE_DB: self.cb_file_db.addItem(os.path.basename(fp), fp)
        self.cb_file_db.blockSignals(False)
        self.update_cb_paket()

    def update_cb_paket(self):
        self.cb_paket.blockSignals(True)
        self.cb_paket.clear()
        fpath_aktif = self.cb_file_db.currentData()
        for unik_id, v in DATA_UJIAN.items():
            if v.get('_file_asal') == fpath_aktif:
                self.cb_paket.addItem(f"{v['_pid_asli']} | {v['mapel']} - Token: {v['token']}", unik_id)
        self.cb_paket.blockSignals(False)
        self.muat_tabel_soal()

    def muat_tabel_soal(self):
        self.tabel_soal.setRowCount(0)
        unik_id = self.cb_paket.currentData()
        if not unik_id or unik_id not in DATA_UJIAN: return
        soal_list = DATA_UJIAN[unik_id]['soal']
        self.tabel_soal.setRowCount(len(soal_list))
        
        temp_editor = QTextEdit()
        
        for i, s in enumerate(soal_list):
            item_no = QTableWidgetItem(str(s['id']))
            item_no.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.tabel_soal.setItem(i, 0, item_no)
            self.tabel_soal.setItem(i, 1, QTableWidgetItem(s['tipe']))
            self.tabel_soal.setItem(i, 2, QTableWidgetItem(str(s.get('bobot', 10))))
            
            temp_editor.setHtml(s['soal'])
            teks_bersih = temp_editor.toPlainText().strip().replace('\n', ' ')
            
            if not teks_bersih and '<img' in s['soal'].lower():
                teks_preview = "[🖼️ Berisi Gambar]"
            else:
                teks_preview = teks_bersih[:55] + "..." if len(teks_bersih) > 55 else teks_bersih
                
            self.tabel_soal.setItem(i, 3, QTableWidgetItem(teks_preview))

    def simpan_soal(self):
        unik_id = self.cb_paket.currentData()
        if not unik_id: return QMessageBox.warning(self, "Error", "Pilih Paket Ujian terlebih dahulu!")
        t = self.cb_tipe.currentText()
        
        if not self.txt_soal.toPlainText().strip() and '<img' not in self.txt_soal.toHtml().lower(): 
            return QMessageBox.warning(self, "Error", "Pertanyaan tidak boleh kosong!")
            
        pdata = DATA_UJIAN[unik_id]
        s_id = self.edit_id
        if not s_id:
            exist_ids = [x['id'] for x in pdata['soal']]
            s_id = max(exist_ids) + 1 if exist_ids else 1
            
        ds = {
            "id": s_id, "tipe": t, "bobot": self.sb_bobot.value(),
            "bacaan": self.txt_wacana.toHtml(), "soal": self.txt_soal.toHtml(),
            "gambar": "", "sumber_gambar": ""
        }
        
        if t == "PG":
            ds["opsi"] = {chr(65+i): e.text() for i, e in enumerate(self.input_dinamis)}
            ds["kunci"] = self.cb_kunci_pg.currentText()
        elif t in ["PGK", "BS"]:
            ds["pernyataan"] = [e.text() for e in self.input_dinamis]
            if t == "PGK": ds["kunci"] = [i for i, chk in enumerate(self.cek_kunci) if chk.isChecked()]
            else: ds["kunci"] = [cb.currentText() for cb in self.cek_kunci]
        elif t == "ESSAY": ds["kunci"] = ""

        if self.edit_id:
            idx = next(i for i, x in enumerate(pdata['soal']) if x['id'] == s_id)
            pdata['soal'][idx] = ds
        else: pdata['soal'].append(ds)
            
        save_all_dbs()
        self.batal_edit()
        self.muat_tabel_soal()
        self.update_tabel_paket()
        QMessageBox.information(self, "Sukses", "Soal berhasil disimpan!")

    def batal_edit(self):
        self.edit_id = None
        self.lbl_judul_form.setText("✏️ Tambah Soal Baru")
        self.txt_wacana.clear()
        self.txt_soal.clear()
        self.btn_simpan.setText("➕ SIMPAN SOAL BARU")
        self.btn_simpan.setStyleSheet(STYLE_BTN_PRIMARY)
        self.btn_batal.hide()
        self.ref_form()

    def edit_soal(self):
        baris = self.tabel_soal.currentRow()
        if baris < 0: return QMessageBox.warning(self, "Peringatan", "Pilih soal dari tabel.")
        s_id = int(self.tabel_soal.item(baris, 0).text())
        unik_id = self.cb_paket.currentData()
        soal = next((x for x in DATA_UJIAN[unik_id]['soal'] if x['id'] == s_id), None)
        if not soal: return
        
        self.edit_id = s_id
        self.lbl_judul_form.setText(f"✏️ Edit Soal No. {s_id}")
        self.cb_tipe.setCurrentText(soal['tipe'])
        self.sb_bobot.setValue(soal.get('bobot', 10.0))
        
        bacaan = soal.get('bacaan', '')
        if "<p" in bacaan or "<html" in bacaan: self.txt_wacana.setHtml(bacaan)
        else: self.txt_wacana.editor.setText(bacaan)
        
        tanya = soal['soal']
        
        gambar_lama = soal.get('gambar', '')
        if gambar_lama:
            img_html = f'<br><img src="data:image/png;base64,{gambar_lama}" width="400"><br>'
            tanya += img_html
            sumber = soal.get('sumber_gambar', '')
            if sumber: tanya += f"<br><i style='color:gray; font-size:10pt;'>Sumber: {sumber}</i><br>"
        
        if "<p" in tanya or "<html" in tanya: self.txt_soal.setHtml(tanya)
        else: self.txt_soal.editor.setText(tanya)
            
        self.ref_form()
        t = soal['tipe']
        if t == "PG":
            for i, l in enumerate(['A','B','C','D','E']): self.input_dinamis[i].setText(soal['opsi'].get(l, ''))
            self.cb_kunci_pg.setCurrentText(soal['kunci'])
        elif t in ["PGK", "BS"]:
            for i in range(min(4, len(soal['pernyataan']))): self.input_dinamis[i].setText(soal['pernyataan'][i])
            if t == "PGK":
                for i in range(4): self.cek_kunci[i].setChecked(i in soal['kunci'])
            else:
                for i in range(min(4, len(soal['kunci']))): self.cek_kunci[i].setCurrentText(soal['kunci'][i])
                
        self.btn_simpan.setText("💾 UPDATE SOAL")
        self.btn_simpan.setStyleSheet(STYLE_BTN_WARNING)
        self.btn_batal.show()

    def hapus_soal(self):
        baris = self.tabel_soal.currentRow()
        if baris < 0: return QMessageBox.warning(self, "Peringatan", "Pilih soal.")
        if QMessageBox.question(self, "Konfirmasi", "Yakin hapus soal?") != QMessageBox.StandardButton.Yes: return
        s_id = int(self.tabel_soal.item(baris, 0).text())
        unik_id = self.cb_paket.currentData()
        DATA_UJIAN[unik_id]['soal'] = [x for x in DATA_UJIAN[unik_id]['soal'] if x['id'] != s_id]
        save_all_dbs()
        self.muat_tabel_soal()
        self.update_tabel_paket()
        if self.edit_id == s_id: self.batal_edit()

    def preview_soal(self):
        unik_id = self.cb_paket.currentData()
        if not unik_id: return
        soal_list = DATA_UJIAN[unik_id]['soal']
        if not soal_list: return QMessageBox.information(self, "Info", "Belum ada soal.")
        
        d = QDialog(self)
        d.setWindowTitle(f"Preview Soal - {DATA_UJIAN[unik_id]['mapel']}")
        d.resize(900, 700)
        d.setStyleSheet("background-color: #F4F7FA; color: #0F172A;")
        ly = QVBoxLayout(d)
        
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        w_scroll = QWidget()
        w_scroll.setStyleSheet("background-color: #F4F7FA; color: #0F172A;")
        ly_scroll = QVBoxLayout(w_scroll)
        ly_scroll.setSpacing(10)
        ly_scroll.setContentsMargins(18, 18, 18, 50) 
        
        temp_editor = QTextEdit()
        
        for s in soal_list:
            lbl_no = QLabel(f"<b>Soal No {s['id']} ({s['tipe']})</b> - Bobot: {s.get('bobot', 10.0)}")
            lbl_no.setStyleSheet("color: #3730A3; font-size: 12pt;")
            ly_scroll.addWidget(lbl_no)
            
            bacaan = s.get('bacaan', '')
            temp_editor.setHtml(bacaan)
            
            if temp_editor.toPlainText().strip() or '<img' in bacaan.lower():
                lbl_wacana = QLabel(f"<b>📄 Teks Bacaan:</b><br>{bacaan}")
                lbl_wacana.setWordWrap(True)
                lbl_wacana.setStyleSheet("font-family: 'Times New Roman'; font-size: 11pt; padding: 12px; border-left: 4px solid #4F46E5; border-radius: 8px; background-color: #E9EFF5;")
                ly_scroll.addWidget(lbl_wacana)

            lbl_soal = QLabel(s['soal'])
            lbl_soal.setWordWrap(True)
            lbl_soal.setStyleSheet("font-family: 'Times New Roman'; font-size: 12pt; margin-top: 5px;")
            ly_scroll.addWidget(lbl_soal)

            if s.get('gambar'):
                lbl_g = QLabel()
                pix = QPixmap()
                pix.loadFromData(base64.b64decode(s['gambar']))
                lbl_g.setPixmap(pix.scaled(400, 400, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
                ly_scroll.addWidget(lbl_g)
                if s.get('sumber_gambar'):
                    lbl_sumber = QLabel(f"<i>Sumber: {s.get('sumber_gambar')}</i>")
                    lbl_sumber.setStyleSheet("color: #475569; font-size: 10pt; font-family: 'Times New Roman';")
                    ly_scroll.addWidget(lbl_sumber)

            if s['tipe'] == 'PG':
                for k, v in s.get('opsi', {}).items():
                    warna = "#047857" if k == s.get('kunci') else "#0F172A"
                    lbl_opsi = QLabel(f"{k}. {v}")
                    lbl_opsi.setWordWrap(True)
                    lbl_opsi.setStyleSheet(f"color: {warna}; font-family: 'Times New Roman';")
                    ly_scroll.addWidget(lbl_opsi)
            elif s['tipe'] in ['PGK', 'BS']:
                for i, p in enumerate(s.get('pernyataan', [])):
                    if s['tipe'] == 'PGK': kunci_teks = "[BENAR]" if i in s.get('kunci', []) else "[SALAH]"
                    else: kunci_teks = f"[{s.get('kunci', [])[i]}]" if i < len(s.get('kunci', [])) else ""
                    lbl_p = QLabel(f"- {p} {kunci_teks}")
                    lbl_p.setWordWrap(True)
                    lbl_p.setStyleSheet("color: #047857; font-weight: bold; font-family: 'Times New Roman';")
                    ly_scroll.addWidget(lbl_p)
            ly_scroll.addWidget(QLabel("<hr>"))
            
        ly_scroll.addSpacing(40) 
        scroll.setWidget(w_scroll)
        ly.addWidget(scroll)
        d.exec()

    def buat_paket(self):
        d = QDialog(self)
        d.setWindowTitle("Paket Baru")
        d.setMinimumWidth(340)
        d.setStyleSheet("background-color: #EEF2F6; color: #0F172A;")
        ly = QFormLayout(d)
        ly.setContentsMargins(20, 20, 20, 20)
        ly.setSpacing(10)
        e_mapel, e_kelas, e_token = QLineEdit(), QLineEdit(), QLineEdit()
        for e in (e_mapel, e_kelas, e_token): e.setStyleSheet(STYLE_INPUT)
        ly.addRow("Mapel:", e_mapel)
        ly.addRow("Kelas:", e_kelas)
        ly.addRow("Token:", e_token)
        btn = QPushButton("Simpan Paket")
        btn.setStyleSheet(STYLE_BTN_PRIMARY)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.clicked.connect(lambda: d.accept())
        ly.addRow("", btn)
        if d.exec() == QDialog.DialogCode.Accepted:
            fpath_aktif = self.cb_file_db.currentData()
            if not fpath_aktif: return QMessageBox.warning(self, "Error", "Tidak ada file database aktif.")
            if not e_mapel.text() or not e_kelas.text() or not e_token.text(): return QMessageBox.warning(self, "Error", "Isi semua!")
            
            exist_pids = [v['_pid_asli'] for k,v in DATA_UJIAN.items() if v.get('_file_asal') == fpath_aktif]
            num = len(exist_pids) + 1
            new_pid = f"paket_{num}"
            while new_pid in exist_pids:
                num += 1
                new_pid = f"paket_{num}"
                
            unik_id = f"{fpath_aktif}||{new_pid}"
            DATA_UJIAN[unik_id] = {"_file_asal": fpath_aktif, "_pid_asli": new_pid, "mapel": e_mapel.text().strip(), "kelas": e_kelas.text().strip(), "token": e_token.text().strip().upper(), "aktif": False, "soal": []}
            save_all_dbs()
            self.update_cb_paket()
            idx = self.cb_paket.findData(unik_id)
            if idx >= 0: self.cb_paket.setCurrentIndex(idx)
            self.update_tabel_paket()

    def buat_file_db(self):
        fp, _ = QFileDialog.getSaveFileName(self, "Buat DB Baru", "soal_baru.json", "JSON (*.json)")
        if fp:
            fp_abs = os.path.abspath(fp)
            if fp_abs not in DAFTAR_FILE_DB: DAFTAR_FILE_DB.append(fp_abs)
            with open(fp_abs, 'w') as f: json.dump({"proctor_password": PROCTOR_PASSWORD, "paket_ujian": {}, "akun_siswa": AKUN_SISWA}, f)
            reload_all_dbs()
            self.update_cb_file_db()
            idx = self.cb_file_db.findData(fp_abs)
            if idx >= 0: self.cb_file_db.setCurrentIndex(idx)
            self.update_tabel_paket()
            QMessageBox.information(self, "Sukses", "File berhasil dibuat!")

    def buka_file_db(self):
        fps, _ = QFileDialog.getOpenFileNames(self, "Buka File JSON", "", "JSON (*.json)")
        if fps:
            for fp in fps:
                fp_abs = os.path.abspath(fp)
                if fp_abs not in DAFTAR_FILE_DB: DAFTAR_FILE_DB.append(fp_abs)
            reload_all_dbs()
            self.update_cb_file_db()
            self.update_tabel_paket()
            self.update_tabel_akun()
            QMessageBox.information(self, "Sukses", f"{len(fps)} file database dimuat!")

    def verifikasi_password_proktor(self):
        pwd, ok = QInputDialog.getText(self, "Verifikasi Keamanan 🔒", 
            "Masukkan Password Proktor untuk mengonfirmasi tindakan ini:", QLineEdit.EchoMode.Password)
        if ok and pwd == PROCTOR_PASSWORD: return True
        elif ok: QMessageBox.warning(self, "Gagal ❌", "Password Proktor salah! Tindakan dibatalkan.")
        return False

    def kick_siswa(self):
        baris = self.tabel_live.currentRow()
        if baris < 0: return QMessageBox.warning(self, "Peringatan", "Pilih siswa dari tabel Live Monitor.")
        if not self.verifikasi_password_proktor(): return
            
        nis = self.tabel_live.item(baris, 0).text()
        token = self.tabel_live.item(baris, 1).text()
        if token == "Belum Masuk Soal": token = "LOGIN"
        kunci = f"{nis}_{token}"
        
        tanya = QMessageBox.question(self, "Konfirmasi Kick", f"Keluarkan NIS {nis} kembali ke Login?\n\n(Progres jawaban siswa tetap AMAN)")
        if tanya == QMessageBox.StandardButton.Yes:
            FLAG_RESET.add(kunci)
            QMessageBox.information(self, "Info", f"Sinyal dikirim. Aplikasi siswa {nis} akan kembali ke halaman Login dalam beberapa detik.")

    def hapus_satu_hasil(self):
        baris = self.tabel_hasil.currentRow()
        if baris < 0: return QMessageBox.warning(self, "Peringatan", "Pilih siswa pada tabel Rekap Hasil.")
        if not self.verifikasi_password_proktor(): return
            
        nama = self.tabel_hasil.item(baris, 0).text()
        kls = self.tabel_hasil.item(baris, 1).text()
        mapel = self.tabel_hasil.item(baris, 2).text()
        kunci_hapus = next((k for k, d in HASIL_SISWA.items() if d['nama'] == nama and str(d['kelas']) == kls and d['mapel'] == mapel), None)
        
        if kunci_hapus and QMessageBox.question(self, "Konfirmasi", f"Hapus hasil ujian milik {nama}?\n\n(Siswa tersebut bisa ujian ulang)") == QMessageBox.StandardButton.Yes:
            del HASIL_SISWA[kunci_hapus]
            save_hasil()
            self.update_tabel_hasil_dan_live()
            QMessageBox.information(self, "Sukses", f"Hasil ujian {nama} berhasil dihapus.")

    def hapus_semua_hasil_paket(self):
        filter_text = self.cb_filter_hasil.currentText()
        if filter_text == "Semua Paket dari Semua File": return QMessageBox.warning(self, "Peringatan", "Pilih spesifik satu paket dari Filter Paket terlebih dahulu.")
        if not self.verifikasi_password_proktor(): return
            
        if QMessageBox.question(self, "Hapus Hasil", f"Hapus SELURUH hasil ujian untuk paket:\n{filter_text}?") == QMessageBox.StandardButton.Yes:
            global HASIL_SISWA
            kunci_hapus = [k for k, d in HASIL_SISWA.items() if f"{d['mapel']} - Kls {d['kelas']} ({d['token']})" == filter_text]
            for k in kunci_hapus: del HASIL_SISWA[k]
            save_hasil()
            self.update_tabel_hasil_dan_live()
            QMessageBox.information(self, "Sukses", "Seluruh hasil pada paket tersebut dihapus.")

    def hapus_autosave(self):
        if not self.verifikasi_password_proktor(): return
        if QMessageBox.question(self, "Konfirmasi Hapus", "Bersihkan seluruh data Auto-Save untuk sesi baru?") == QMessageBox.StandardButton.Yes:
            global JAWABAN_SEMENTARA
            JAWABAN_SEMENTARA.clear()
            try:
                if os.path.exists(AUTOSAVE_FILE): os.remove(AUTOSAVE_FILE)
                self.update_tabel_hasil_dan_live()
                QMessageBox.information(self, "Sukses", "Data Auto-Save dibersihkan!")
            except Exception as e: QMessageBox.warning(self, "Error", str(e))

    def simpan_pwd(self):
        global PROCTOR_PASSWORD
        PROCTOR_PASSWORD = self.ent_pwd.text().strip()
        save_all_dbs()
        QMessageBox.information(self, "Sukses", "Password diupdate!")

    def tog_ujian(self, status):
        brs = self.tabel_paket.currentRow()
        if brs < 0: return QMessageBox.warning(self, "Peringatan", "Pilih paket terlebih dahulu.")
        unik_id = self.tabel_paket.item(brs, 6).text()
        DATA_UJIAN[unik_id]['aktif'] = status
        save_all_dbs()
        self.update_tabel_paket()

    def update_tabel_paket(self):
        brs_sebelumnya = self.tabel_paket.currentRow()
        self.tabel_paket.setRowCount(len(DATA_UJIAN))
        paket_aktif_count = 0
        for i, (unik_id, v) in enumerate(DATA_UJIAN.items()):
            if v.get('aktif'):
                paket_aktif_count += 1
            self.tabel_paket.setItem(i, 0, QTableWidgetItem(os.path.basename(v['_file_asal'])))
            self.tabel_paket.setItem(i, 1, QTableWidgetItem(v['mapel']))
            self.tabel_paket.setItem(i, 2, QTableWidgetItem(v['kelas']))
            self.tabel_paket.setItem(i, 3, QTableWidgetItem(v['token']))
            self.tabel_paket.setItem(i, 4, QTableWidgetItem(str(len(v['soal']))))
            self.tabel_paket.setItem(i, 5, QTableWidgetItem("🟢 Aktif" if v.get('aktif') else "🔴 Tutup"))
            self.tabel_paket.setItem(i, 6, QTableWidgetItem(unik_id))
        if 0 <= brs_sebelumnya < len(DATA_UJIAN):
            self.tabel_paket.selectRow(brs_sebelumnya)

        if hasattr(self, 'lbl_stat_paket'):
            self.lbl_stat_paket.setText(f"{paket_aktif_count} / {len(DATA_UJIAN)} Paket")
            
        curr_filter = self.cb_filter_hasil.currentText()
        self.cb_filter_hasil.blockSignals(True)
        self.cb_filter_hasil.clear()
        self.cb_filter_hasil.addItem("Semua Paket dari Semua File")
        for v in DATA_UJIAN.values():
            self.cb_filter_hasil.addItem(f"{v['mapel']} - Kls {v['kelas']} ({v['token']})")
        idx = self.cb_filter_hasil.findText(curr_filter)
        if idx >= 0: self.cb_filter_hasil.setCurrentIndex(idx)
        self.cb_filter_hasil.blockSignals(False)

    def update_tabel_hasil_langsung(self):
        self._last_hasil_snapshot = None
        self.update_tabel_hasil_dan_live()

    def update_tabel_hasil_dan_live(self):
        now = time.time()
        siswa_online_count = 0
        live_rows = []

        for kunci, data in JAWABAN_SEMENTARA.items():
            parts = kunci.split("_", 1)
            nis = parts[0]
            token = parts[1] if len(parts) > 1 else ""
            if token == "LOGIN":
                token_disp, total, terjawab, pct = "Belum Masuk Soal", "-", "-", "Di Beranda"
            else:
                token_disp = token
                paket = next((p for p in DATA_UJIAN.values() if p['token'] == token), None)
                total = len(paket['soal']) if paket else 0
                terjawab = data.get("terjawab", 0) if isinstance(data, dict) else (len([k for k in data.keys() if data[k]]) if isinstance(data, dict) else 0)
                pct = f"{(terjawab/total)*100:.0f}%" if total > 0 else "0%"

            if now - WAKTU_AKTIF_SISWA.get(nis, 0) <= 15:
                status_koneksi = "🟢 Online"
                siswa_online_count += 1
            else:
                status_koneksi = "🔴 Offline"
            live_rows.append((nis, token_disp, str(terjawab), str(total), pct, status_koneksi))

        if live_rows != self._last_live_snapshot:
            self._last_live_snapshot = live_rows
            nis_terpilih = None
            if self.tabel_live.currentRow() >= 0 and self.tabel_live.item(self.tabel_live.currentRow(), 0):
                nis_terpilih = self.tabel_live.item(self.tabel_live.currentRow(), 0).text()
            scroll_live_pos = self.tabel_live.verticalScrollBar().value()

            self.tabel_live.setRowCount(len(live_rows))
            baris_restore_live = -1
            for i, row in enumerate(live_rows):
                if row[0] == nis_terpilih:
                    baris_restore_live = i
                for col, val in enumerate(row):
                    self.tabel_live.setItem(i, col, QTableWidgetItem(val))

            if baris_restore_live >= 0:
                self.tabel_live.selectRow(baris_restore_live)
            self.tabel_live.verticalScrollBar().setValue(scroll_live_pos)

        filter_text = self.cb_filter_hasil.currentText()
        hasil_rows = [
            (d['nama'], str(d['kelas']), d['mapel'], f"{d['skor']:.2f}")
            for k, d in HASIL_SISWA.items()
            if filter_text == "Semua Paket dari Semua File" or f"{d['mapel']} - Kls {d['kelas']} ({d['token']})" == filter_text
        ]

        if hasil_rows != self._last_hasil_snapshot:
            self._last_hasil_snapshot = hasil_rows
            kunci_hasil_terpilih = None
            if self.tabel_hasil.currentRow() >= 0 and self.tabel_hasil.item(self.tabel_hasil.currentRow(), 0):
                kunci_hasil_terpilih = (
                    self.tabel_hasil.item(self.tabel_hasil.currentRow(), 0).text(),
                    self.tabel_hasil.item(self.tabel_hasil.currentRow(), 2).text()
                )
            scroll_hasil_pos = self.tabel_hasil.verticalScrollBar().value()

            self.tabel_hasil.setRowCount(len(hasil_rows))
            baris_restore_hasil = -1
            for i, row in enumerate(hasil_rows):
                if kunci_hasil_terpilih == (row[0], row[2]):
                    baris_restore_hasil = i
                for col, val in enumerate(row):
                    self.tabel_hasil.setItem(i, col, QTableWidgetItem(val))

            if baris_restore_hasil >= 0:
                self.tabel_hasil.selectRow(baris_restore_hasil)
            self.tabel_hasil.verticalScrollBar().setValue(scroll_hasil_pos)

        stats_now = (siswa_online_count, len(AKUN_SISWA), len(HASIL_SISWA))
        if stats_now != self._last_stats_snapshot and hasattr(self, 'lbl_stat_online'):
            self._last_stats_snapshot = stats_now
            self.lbl_stat_online.setText(f"{siswa_online_count} Siswa")
            self.lbl_stat_akun.setText(f"{len(AKUN_SISWA)} Akun")
            self.lbl_stat_hasil.setText(f"{len(HASIL_SISWA)} Data")

    def cek_detail_essay(self, baris, kolom):
        nama = self.tabel_hasil.item(baris, 0).text()
        kls = self.tabel_hasil.item(baris, 1).text()
        d = next((x for x in HASIL_SISWA.values() if x['nama']==nama and str(x['kelas'])==kls), None)
        if not d: return
        p = next((x for x in DATA_UJIAN.values() if x['token']==d['token']), None)
        
        d_win = QDialog(self)
        d_win.setWindowTitle(f"Detail Jawaban - {nama}")
        d_win.resize(720, 620)
        d_win.setStyleSheet("background-color: #EEF2F6; color: #0F172A;")
        ly = QVBoxLayout(d_win)
        ly.setContentsMargins(18, 18, 18, 18)
        lbl = QLabel(f"<b>{nama}</b> | Skor: <span style='color:#3730A3;'>{d['skor']:.2f}</span>")
        lbl.setFont(QFont("Segoe UI", 14))
        ly.addWidget(lbl)
        txt = QTextEdit()
        txt.setReadOnly(True)
        txt.setStyleSheet("background-color: #F8FAFC; color: #0F172A; font-family: 'Times New Roman'; font-size: 11pt; border-radius: 10px; padding: 10px; border: 1px solid #C2CEDB;")
        
        temp_editor = QTextEdit()
        
        for soal in (p['soal'] if p else []):
            tipe = soal['tipe']
            sid = str(soal['id'])
            jwb = d['detail'].get(sid, '[Tidak Dijawab]')
            kunci = soal.get('kunci', '')
            
            bacaan = soal.get('bacaan', '')
            temp_editor.setHtml(bacaan)
            
            html = f"<b>Soal No {soal['id']} ({tipe}) - Bobot: {soal.get('bobot', 10):.2f}</b><br>"
            
            if temp_editor.toPlainText().strip() or '<img' in bacaan.lower():
                html += f"<i>Teks Bacaan: {bacaan}</i><br><br>"
                
            html += f"Tanya: {soal['soal']}<br>"
            
            if tipe == 'ESSAY':
                html += f"Jawaban Siswa:<br><font color='#3730A3'>{jwb}</font><br>"
            else:
                html += f"Jawab Siswa: {jwb}<br>Kunci Benar: {kunci}<br>"
                benar = False
                if tipe == 'PG' and jwb == kunci: benar = True
                elif tipe == 'PGK' and isinstance(jwb, list) and sorted(jwb) == sorted(kunci): benar = True
                elif tipe == 'BS' and isinstance(jwb, list) and jwb == kunci: benar = True
                html += "Status: ✅ BENAR<br>" if benar else "Status: ❌ SALAH<br>"
            html += "<hr>"
            txt.append(html)
        ly.addWidget(txt)
        d_win.exec()

    def unduh_csv(self):
        filter_text = self.cb_filter_hasil.currentText()
        data_filtered = [d for k, d in HASIL_SISWA.items() if filter_text == "Semua Paket dari Semua File" or f"{d['mapel']} - Kls {d['kelas']} ({d['token']})" == filter_text]
        if not data_filtered: return QMessageBox.warning(self, "Peringatan", "Tidak ada data untuk diunduh.")
        
        fp, _ = QFileDialog.getSaveFileName(self, "Simpan CSV Hasil", "Rekap_Nilai_CBT.csv", "CSV (*.csv)")
        if not fp: return
        try:
            with open(fp, mode='w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f, delimiter=';')
                max_soal = max([max([int(k) for k in d['detail'].keys() if k.isdigit()] + [0]) for d in data_filtered])
                header = ["Nama Siswa", "Kelas", "Mapel", "Token", "Skor Akhir"] + [f"Soal {i}" for i in range(1, max_soal+1)]
                writer.writerow(header)
                for d in data_filtered:
                    row = [d['nama'], d['kelas'], d['mapel'], d['token'], f"{d['skor']:.2f}"]
                    for i in range(1, max_soal + 1): row.append(d['detail'].get(str(i), "-"))
                    writer.writerow(row)
            QMessageBox.information(self, "Sukses", f"Nilai disimpan ke:\n{os.path.basename(fp)}")
        except Exception as e: QMessageBox.critical(self, "Error", str(e))

    def unduh_analisis_soal(self):
        filter_text = self.cb_filter_hasil.currentText()
        if filter_text == "Semua Paket dari Semua File": return QMessageBox.warning(self, "Peringatan", "Pilih salah satu paket di Filter Paket terlebih dahulu.")
            
        data_filtered = [d for k, d in HASIL_SISWA.items() if f"{d['mapel']} - Kls {d['kelas']} ({d['token']})" == filter_text]
        if not data_filtered: return QMessageBox.warning(self, "Peringatan", "Belum ada siswa yang menyelesaikan paket ini.")
        
        token_paket = data_filtered[0]['token']
        paket = next((v for v in DATA_UJIAN.values() if v['token'] == token_paket), None)
        if not paket: return
            
        fp, _ = QFileDialog.getSaveFileName(self, "Simpan Analisis CSV", f"Analisis_{paket['mapel']}.csv", "CSV (*.csv)")
        if not fp: return
        try:
            with open(fp, mode='w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f, delimiter=';')
                writer.writerow(["No Soal", "Tipe Soal", "Pertanyaan", "Jml Benar", "Jml Salah", "% Keberhasilan"])
                total_siswa = len(data_filtered)
                
                temp_editor = QTextEdit()
                for s in paket['soal']:
                    sid = str(s['id'])
                    
                    temp_editor.setHtml(s['soal'])
                    teks_asli = temp_editor.toPlainText().strip().replace('\n', ' ')
                    if not teks_asli and '<img' in s['soal'].lower():
                        teks_asli = "[Gambar]"
                    
                    tanya_singkat = teks_asli[:60]
                    
                    if s['tipe'] == 'PG':
                        benar = sum(1 for d in data_filtered if d['detail'].get(sid) == s.get('kunci'))
                        salah = total_siswa - benar
                        pct = f"{(benar/total_siswa)*100:.1f}%" if total_siswa > 0 else "0%"
                        writer.writerow([sid, s['tipe'], tanya_singkat, benar, salah, pct])
                        
                    elif s['tipe'] in ['PGK', 'BS']:
                        benar = 0
                        for d in data_filtered:
                            jwb = d['detail'].get(sid)
                            kunci = s.get('kunci')
                            if s['tipe'] == 'PGK' and isinstance(jwb, list) and isinstance(kunci, list) and sorted(jwb) == sorted(kunci):
                                benar += 1
                            elif s['tipe'] == 'BS' and isinstance(jwb, list) and isinstance(kunci, list) and jwb == kunci:
                                benar += 1
                                
                        salah = total_siswa - benar
                        pct = f"{(benar/total_siswa)*100:.1f}%" if total_siswa > 0 else "0%"
                        writer.writerow([sid, s['tipe'], tanya_singkat, benar, salah, pct])
                    
                    elif s['tipe'] == 'ESSAY':
                        writer.writerow([sid, s['tipe'], tanya_singkat, "Manual", "Manual", "-"])
                        
            QMessageBox.information(self, "Sukses", f"Analisis disimpan ke:\n{os.path.basename(fp)}")
        except Exception as e: QMessageBox.critical(self, "Error", str(e))

    def tambah_akun_manual(self):
        d = QDialog(self)
        d.setWindowTitle("Tambah Akun Siswa Baru")
        d.setMinimumWidth(360)
        d.setStyleSheet("background-color: #EEF2F6; color: #0F172A;")
        ly = QFormLayout(d)
        ly.setContentsMargins(20, 20, 20, 20)
        ly.setSpacing(10)
        e_nis, e_nama, e_kelas, e_pass = QLineEdit(), QLineEdit(), QLineEdit(), QLineEdit()
        for e in (e_nis, e_nama, e_kelas, e_pass): e.setStyleSheet(STYLE_INPUT)
        ly.addRow("NIS / Username:", e_nis)
        ly.addRow("Nama Lengkap:", e_nama)
        ly.addRow("Kelas:", e_kelas)
        ly.addRow("Password Login:", e_pass)
        btn = QPushButton("Simpan Akun")
        btn.setStyleSheet(STYLE_BTN_PRIMARY)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.clicked.connect(lambda: d.accept())
        ly.addRow("", btn)
        if d.exec() == QDialog.DialogCode.Accepted:
            nis = e_nis.text().strip()
            if not nis or not e_nama.text().strip() or not e_pass.text().strip(): return QMessageBox.warning(self, "Error", "Wajib mengisi semua kolom!")
            if nis in AKUN_SISWA: return QMessageBox.warning(self, "Error", "NIS ini sudah terdaftar!")
            AKUN_SISWA[nis] = {"nama": e_nama.text().strip(), "kelas": e_kelas.text().strip(), "password": e_pass.text().strip()}
            save_all_dbs()
            self.update_tabel_akun()

    def edit_akun_manual(self):
        baris = self.tabel_akun.currentRow()
        if baris < 0: return QMessageBox.warning(self, "Peringatan", "Pilih salah satu akun di tabel.")
        nis_lama = self.tabel_akun.item(baris, 0).text()
        data_lama = AKUN_SISWA.get(nis_lama)
        if not data_lama: return
        
        d = QDialog(self)
        d.setWindowTitle("Edit Akun Siswa")
        d.setMinimumWidth(360)
        d.setStyleSheet("background-color: #EEF2F6; color: #0F172A;")
        ly = QFormLayout(d)
        ly.setContentsMargins(20, 20, 20, 20)
        ly.setSpacing(10)
        e_nis = QLineEdit(nis_lama)
        e_nama = QLineEdit(data_lama['nama'])
        e_kelas = QLineEdit(data_lama['kelas'])
        e_pass = QLineEdit(data_lama['password'])
        for e in (e_nis, e_nama, e_kelas, e_pass): e.setStyleSheet(STYLE_INPUT)
        ly.addRow("NIS / Username:", e_nis)
        ly.addRow("Nama Lengkap:", e_nama)
        ly.addRow("Kelas:", e_kelas)
        ly.addRow("Password Login:", e_pass)
        btn = QPushButton("Simpan Perubahan")
        btn.setStyleSheet(STYLE_BTN_WARNING)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.clicked.connect(lambda: d.accept())
        ly.addRow("", btn)
        if d.exec() == QDialog.DialogCode.Accepted:
            nis_baru = e_nis.text().strip()
            if not nis_baru or not e_nama.text().strip() or not e_pass.text().strip(): return QMessageBox.warning(self, "Error", "Semua kolom wajib diisi!")
            if nis_baru != nis_lama and nis_baru in AKUN_SISWA: return QMessageBox.warning(self, "Error", "NIS baru sudah dipakai akun lain!")
            if nis_baru != nis_lama: del AKUN_SISWA[nis_lama]
            AKUN_SISWA[nis_baru] = {"nama": e_nama.text().strip(), "kelas": e_kelas.text().strip(), "password": e_pass.text().strip()}
            save_all_dbs()
            self.update_tabel_akun()

    def hapus_akun_manual(self):
        baris = self.tabel_akun.currentRow()
        if baris < 0: return QMessageBox.warning(self, "Peringatan", "Pilih salah satu akun di tabel.")
        nis = self.tabel_akun.item(baris, 0).text()
        if QMessageBox.question(self, "Hapus Akun", f"Hapus akun siswa ini?\nNIS: {nis}") == QMessageBox.StandardButton.Yes:
            if nis in AKUN_SISWA:
                del AKUN_SISWA[nis]
                save_all_dbs()
                self.update_tabel_akun()

    def update_tabel_akun(self):
        self.tabel_akun.setRowCount(len(AKUN_SISWA))
        for i, (nis, data) in enumerate(AKUN_SISWA.items()):
            self.tabel_akun.setItem(i, 0, QTableWidgetItem(nis))
            self.tabel_akun.setItem(i, 1, QTableWidgetItem(data['nama']))
            self.tabel_akun.setItem(i, 2, QTableWidgetItem(data['kelas']))
            self.tabel_akun.setItem(i, 3, QTableWidgetItem(data['password'])) 

from updater import cek_dan_update_otomatis

VERSI_GURU = "1.0.1"

if __name__ == '__main__':
    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("smaid.exambrowser.guru")

    app = QApplication(sys.argv)
    ikon_app = dapatkan_path_file("logo.ico")
    if not os.path.exists(ikon_app):
        ikon_app = dapatkan_path_file("logo.jpg")
    app.setWindowIcon(QIcon(ikon_app))

    cek_dan_update_otomatis("guru", VERSI_GURU)

    window = GuruApp()
    window.show()
    sys.exit(app.exec())