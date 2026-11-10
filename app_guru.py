import sys
import os
import json
import base64
import csv
import socket
import threading
import re
from flask import Flask, request, jsonify
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                             QTabWidget, QLabel, QLineEdit, QPushButton, QComboBox, 
                             QTableWidget, QTableWidgetItem, QHeaderView, QDoubleSpinBox, 
                             QTextEdit, QFileDialog, QMessageBox, QGroupBox, QScrollArea,
                             QFormLayout, QRadioButton, QCheckBox, QDialog, QAbstractItemView,
                             QToolBar)
from PyQt6.QtGui import QFont, QPixmap, QIcon, QAction
from PyQt6.QtCore import Qt, QTimer

try:
    import docx
    DOCX_AVAILABLE = True
except ImportError:
    DOCX_AVAILABLE = False

def dapatkan_path_file(nama_file):
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, nama_file)

# ================= KUSTOM KOMPONEN =================
class AntiScrollComboBox(QComboBox):
    def wheelEvent(self, e): e.ignore()

class AntiScrollSpinBox(QDoubleSpinBox):
    def wheelEvent(self, e): e.ignore()

class AntiScrollTableWidget(QTableWidget):
    pass

class RichTextEditor(QWidget):
    def __init__(self):
        super().__init__()
        ly = QVBoxLayout(self)
        ly.setContentsMargins(0, 0, 0, 0)
        ly.setSpacing(2)
        
        self.toolbar = QToolBar()
        self.editor = QTextEdit()
        self.editor.setStyleSheet("font-family: 'Times New Roman'; font-size: 12pt; background-color: white; color: black; border: 1px solid gray;")
        
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
        
        self.cb_font = QComboBox()
        self.cb_font.addItems(["Times New Roman", "Segoe UI", "Arial", "Courier New"])
        self.cb_font.currentTextChanged.connect(self.editor.setFontFamily)
        
        self.toolbar.addAction(btn_b)
        self.toolbar.addAction(btn_i)
        self.toolbar.addAction(btn_u)
        self.toolbar.addWidget(QLabel("  Font: "))
        self.toolbar.addWidget(self.cb_font)
        
        ly.addWidget(self.toolbar)
        ly.addWidget(self.editor)
        
    def toHtml(self): return self.editor.toHtml()
    def setHtml(self, html): self.editor.setHtml(html)
    def toPlainText(self): return self.editor.toPlainText()
    def clear(self): self.editor.clear()

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
            with open(AUTOSAVE_FILE, 'r') as f:
                JAWABAN_SEMENTARA = json.load(f)
        except:
            JAWABAN_SEMENTARA = {}

def load_hasil():
    global HASIL_SISWA
    if os.path.exists(HASIL_FILE):
        try:
            with open(HASIL_FILE, 'r') as f:
                HASIL_SISWA = json.load(f)
        except:
            HASIL_SISWA = {}

def save_hasil():
    try:
        with open(HASIL_FILE, 'w') as f:
            json.dump(HASIL_SISWA, f, indent=4)
    except:
        pass

def init_db():
    global DAFTAR_FILE_DB
    default_db = os.path.abspath("database_ujian_cbt.json")
    DAFTAR_FILE_DB = [default_db]
    if not os.path.exists(default_db):
        with open(default_db, 'w') as f:
            json.dump({"proctor_password": "admin123", "paket_ujian": {}, "akun_siswa": {}}, f)
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
                    if d.get("proctor_password") and PROCTOR_PASSWORD == "admin123":
                        PROCTOR_PASSWORD = d.get("proctor_password")
                    for pid, pdata in d.get("paket_ujian", {}).items():
                        unik_id = f"{fpath}||{pid}"
                        pdata['_file_asal'] = fpath
                        pdata['_pid_asli'] = pid
                        new_data[unik_id] = pdata
                    for nis, adata in d.get("akun_siswa", {}).items():
                        new_akun[nis] = adata
            except:
                pass
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
            with open(fpath, 'r') as f:
                d = json.load(f)
        except:
            d = {}
            
        d['proctor_password'] = PROCTOR_PASSWORD
        d['paket_ujian'] = paket_untuk_file
        d['akun_siswa'] = AKUN_SISWA 
        
        with open(fpath, 'w') as f:
            json.dump(d, f, indent=4)

@app_flask.route('/api/cek_password', methods=['POST'])
def cek_password():
    if request.json.get('password') == PROCTOR_PASSWORD: return jsonify({"status": "sukses"})
    return jsonify({"status": "error", "pesan": "Password salah!"})

@app_flask.route('/api/login_siswa', methods=['POST'])
def login_siswa():
    d = request.json
    nis = d.get('nis', '').strip()
    password = d.get('password', '').strip()

    if nis not in AKUN_SISWA:
        return jsonify({"status": "error", "pesan": "NIS tidak ditemukan. Hubungi Proktor!"})
    if AKUN_SISWA[nis]['password'] != password:
        return jsonify({"status": "error", "pesan": "Password salah!"})
    
    return jsonify({"status": "sukses", "nama": AKUN_SISWA[nis]['nama'], "kelas": AKUN_SISWA[nis]['kelas']})

@app_flask.route('/api/auth_soal', methods=['POST'])
def auth_soal():
    token = request.json.get('token')
    nis = request.json.get('nis', '')
    
    paket = next((p for p in DATA_UJIAN.values() if p.get('token') == token), None)
    if not paket: return jsonify({"status": "error", "pesan": "Token ujian tidak ditemukan!"})
    if not paket.get('aktif'): return jsonify({"status": "error", "pesan": "Ujian belum diaktifkan!"})
    if len(paket['soal']) == 0: return jsonify({"status": "error", "pesan": "Belum ada soal!"})
    
    kunci_autosave = f"{nis}_{token}"
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

@app_flask.route('/api/autosave', methods=['POST'])
def autosave():
    data = request.json
    nis = data.get('nis')
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
                with open(AUTOSAVE_FILE, 'w') as f:
                    json.dump(JAWABAN_SEMENTARA, f)
        except:
            pass
            
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
    return jsonify({"status": "sukses"})

def run_server():
    app_flask.run(host='0.0.0.0', port=5000, debug=False, use_reloader=False, threaded=True)

# ================= GURU APP GUI =================
class GuruApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Server Proktor CBT - SMA Islam Darussalam (Fitur Lengkap)")
        
        ikon_path = dapatkan_path_file("logo.jpg")
        if os.path.exists(ikon_path):
            self.setWindowIcon(QIcon(ikon_path))
            
        self.resize(1100, 850)
        self.setStyleSheet("background-color: #f4f6f9; color: black; font-family: 'Segoe UI'; font-size: 10pt;")
        
        init_db()
        self.b64_image = ""
        self.edit_id = None
        self.input_dinamis = []

        widget_utama = QWidget()
        self.setCentralWidget(widget_utama)
        layout_utama = QVBoxLayout(widget_utama)
        layout_utama.setContentsMargins(15, 15, 15, 15)
        
        w_header = QWidget()
        w_header.setStyleSheet("background-color: #e9ecef; border-radius: 5px;")
        ly_h = QHBoxLayout(w_header)
        ly_h.setContentsMargins(10, 10, 10, 10)
        
        lbl_logo = QLabel()
        if os.path.exists(ikon_path):
            pix = QPixmap(ikon_path)
            lbl_logo.setPixmap(pix.scaled(40, 40, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
            ly_h.addWidget(lbl_logo)

        lbl_header = QLabel("🖥️ SERVER PROKTOR CBT - SMA ISLAM DARUSSALAM")
        lbl_header.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
        lbl_header.setStyleSheet("color: #1a252f; border: none;")
        ly_h.addWidget(lbl_header)
        ly_h.addStretch()
        layout_utama.addWidget(w_header)

        self.tabs = QTabWidget()
        self.tabs.setStyleSheet("QTabWidget::pane { border: 1px solid #ccc; background: white; } QTabBar::tab { background: #e9ecef; color: black; padding: 8px 15px; margin-right: 2px; } QTabBar::tab:selected { background: white; font-weight: bold; }")
        layout_utama.addWidget(self.tabs)

        self.tab_soal = QWidget()
        self.tab_proktor = QWidget()
        self.tab_siswa = QWidget() 
        
        self.tabs.addTab(self.tab_soal, "📝 Manajemen Soal")
        self.tabs.addTab(self.tab_proktor, "⚙️ Kontrol Proktor & Hasil")
        self.tabs.addTab(self.tab_siswa, "👥 Data Akun Siswa")

        self.setup_tab_soal()
        self.setup_tab_proktor()
        self.setup_tab_siswa()
        
        self.timer_hasil = QTimer()
        self.timer_hasil.timeout.connect(self.update_tabel_hasil_dan_live)
        self.timer_hasil.start(2500)

        threading.Thread(target=run_server, daemon=True).start()

    # ================= TAB 1: MANAJEMEN SOAL =================
    def setup_tab_soal(self):
        layout = QVBoxLayout(self.tab_soal)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        
        konten_scroll = QWidget()
        konten_scroll.setStyleSheet("background-color: #f4f6f9; color: black;")
        layout_scroll = QVBoxLayout(konten_scroll)
        layout_scroll.setSpacing(15)
        layout_scroll.setContentsMargins(10, 10, 10, 10)

        gb_db = QGroupBox("📁 Manajemen File Database JSON")
        gb_db.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        gb_db.setStyleSheet("background-color: white; color: black;")
        ly_db = QHBoxLayout(gb_db)
        
        ly_db.addWidget(QLabel("File JSON Aktif:"))
        self.cb_file_db = AntiScrollComboBox()
        self.cb_file_db.setStyleSheet("background-color: white; color: blue; font-weight: bold; border: 1px solid gray;")
        self.cb_file_db.setMinimumWidth(250)
        self.cb_file_db.currentIndexChanged.connect(self.update_cb_paket)
        ly_db.addWidget(self.cb_file_db)
        ly_db.addStretch()
        
        btn_db_baru = QPushButton("📄 Buat File Baru")
        btn_db_baru.setStyleSheet("background-color: #17a2b8; color: white; padding: 5px;")
        btn_db_baru.clicked.connect(self.buat_file_db)
        btn_db_buka = QPushButton("📂 Tambah / Buka File JSON")
        btn_db_buka.setStyleSheet("background-color: #6c757d; color: white; padding: 5px;")
        btn_db_buka.clicked.connect(self.buka_file_db)
        ly_db.addWidget(btn_db_baru)
        ly_db.addWidget(btn_db_buka)
        layout_scroll.addWidget(gb_db)

        gb_paket = QGroupBox("📦 Pilih / Buat Paket Ujian")
        gb_paket.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        gb_paket.setStyleSheet("background-color: white; color: black;")
        ly_paket = QHBoxLayout(gb_paket)
        
        self.cb_paket = AntiScrollComboBox()
        self.cb_paket.setStyleSheet("background-color: white; color: black; border: 1px solid gray;")
        self.cb_paket.currentIndexChanged.connect(self.muat_tabel_soal)
        self.cb_paket.setMinimumWidth(400)
        ly_paket.addWidget(self.cb_paket)
        
        btn_paket_baru = QPushButton("➕ Buat Paket Baru")
        btn_paket_baru.setStyleSheet("background-color: #28a745; color: white; padding: 5px;")
        btn_paket_baru.clicked.connect(self.buat_paket)
        ly_paket.addWidget(btn_paket_baru)
        ly_paket.addStretch()
        layout_scroll.addWidget(gb_paket)

        gb_list = QGroupBox("📋 Daftar Soal di Paket Ini")
        gb_list.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        gb_list.setStyleSheet("background-color: white; color: black;")
        ly_list = QHBoxLayout(gb_list)
        
        self.tabel_soal = AntiScrollTableWidget(0, 4)
        self.tabel_soal.setStyleSheet("background-color: white; color: black; gridline-color: #ccc; selection-background-color: #cce5ff; selection-color: black;")
        self.tabel_soal.setHorizontalHeaderLabels(["No", "Tipe", "Bobot", "Pertanyaan"])
        self.tabel_soal.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        self.tabel_soal.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.tabel_soal.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.tabel_soal.setMinimumHeight(180)
        ly_list.addWidget(self.tabel_soal)
        
        ly_btn_tabel = QVBoxLayout()
        btn_import = QPushButton("📥 Import Word (.docx)")
        btn_import.setStyleSheet("background-color: #28a745; color: white; font-weight: bold; padding: 6px;")
        btn_import.clicked.connect(self.import_word)
        btn_preview = QPushButton("🔍 Preview Soal")
        btn_preview.setStyleSheet("background-color: #17a2b8; color: white; padding: 5px;")
        btn_preview.clicked.connect(self.preview_soal)
        btn_edit = QPushButton("✏️ Edit Soal")
        btn_edit.setStyleSheet("background-color: #ffc107; color: black; padding: 5px;")
        btn_edit.clicked.connect(self.edit_soal)
        btn_hapus = QPushButton("🗑️ Hapus Soal")
        btn_hapus.setStyleSheet("background-color: #dc3545; color: white; padding: 5px;")
        btn_hapus.clicked.connect(self.hapus_soal)
        
        ly_btn_tabel.addWidget(btn_import)
        ly_btn_tabel.addWidget(btn_preview)
        ly_btn_tabel.addWidget(btn_edit)
        ly_btn_tabel.addWidget(btn_hapus)
        ly_btn_tabel.addStretch()
        ly_list.addLayout(ly_btn_tabel)
        layout_scroll.addWidget(gb_list)

        gb_form = QGroupBox("✏️ Form Input / Edit Soal")
        gb_form.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        gb_form.setStyleSheet("background-color: white; color: black;")
        ly_form = QFormLayout(gb_form)
        ly_form.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.AllNonFixedFieldsGrow)
        
        self.cb_tipe = AntiScrollComboBox()
        self.cb_tipe.setStyleSheet("background-color: white; color: black; border: 1px solid gray;")
        self.cb_tipe.addItems(["PG", "PGK", "BS", "ESSAY"])
        self.cb_tipe.currentTextChanged.connect(self.ref_form)
        ly_form.addRow("Tipe Soal:", self.cb_tipe)
        
        self.sb_bobot = AntiScrollSpinBox()
        self.sb_bobot.setStyleSheet("background-color: white; color: black; border: 1px solid gray;")
        self.sb_bobot.setValue(10.0)
        self.sb_bobot.setMaximum(100.0)
        ly_form.addRow("Bobot Poin:", self.sb_bobot)
        
        self.txt_wacana = RichTextEditor()
        self.txt_wacana.setMinimumHeight(140)
        ly_form.addRow("Wacana (Opsional):", self.txt_wacana)
        
        self.txt_soal = RichTextEditor()
        self.txt_soal.setMinimumHeight(140)
        ly_form.addRow("Pertanyaan:", self.txt_soal)
        
        ly_img = QHBoxLayout()
        btn_img = QPushButton("Unggah Gambar")
        btn_img.clicked.connect(self.unggah_gambar)
        btn_img_lihat = QPushButton("Lihat Gambar")
        btn_img_lihat.clicked.connect(self.lihat_gambar_form)
        self.lbl_img_status = QLabel("Tidak ada gambar")
        ly_img.addWidget(btn_img)
        ly_img.addWidget(btn_img_lihat)
        ly_img.addWidget(self.lbl_img_status)
        ly_img.addStretch()
        ly_form.addRow("Gambar:", ly_img)
        
        self.ent_sumber = QLineEdit()
        self.ent_sumber.setStyleSheet("background-color: white; color: black; border: 1px solid gray;")
        ly_form.addRow("Sumber Gambar:", self.ent_sumber)

        self.w_dinamis = QWidget()
        self.ly_dinamis = QFormLayout(self.w_dinamis)
        self.ly_dinamis.setContentsMargins(0, 0, 0, 0)
        ly_form.addRow("", self.w_dinamis)

        ly_btn_simpan = QHBoxLayout()
        self.btn_batal = QPushButton("❌ BATAL")
        self.btn_batal.setStyleSheet("background-color: #6c757d; color: white; font-weight: bold; padding: 8px;")
        self.btn_batal.hide()
        self.btn_batal.clicked.connect(self.batal_edit)
        self.btn_simpan = QPushButton("➕ SIMPAN SOAL BARU")
        self.btn_simpan.setStyleSheet("background-color: #0d6efd; color: white; font-weight: bold; padding: 8px;")
        self.btn_simpan.clicked.connect(self.simpan_soal)
        
        ly_btn_simpan.addWidget(self.btn_batal)
        ly_btn_simpan.addStretch()
        ly_btn_simpan.addWidget(self.btn_simpan)
        ly_form.addRow("", ly_btn_simpan)

        layout_scroll.addWidget(gb_form)
        scroll.setWidget(konten_scroll)
        layout.addWidget(scroll)
        
        self.update_cb_file_db()
        self.ref_form()

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
                ent.setStyleSheet("background-color: white; color: black; border: 1px solid gray;")
                self.ly_dinamis.addRow(f"Opsi {l}:", ent)
                self.input_dinamis.append(ent)
                
            self.cb_kunci_pg = AntiScrollComboBox()
            self.cb_kunci_pg.setStyleSheet("background-color: white; color: black; border: 1px solid gray;")
            self.cb_kunci_pg.addItems(['A','B','C','D','E'])
            self.ly_dinamis.addRow("Kunci Benar:", self.cb_kunci_pg)
            
        elif t in ["PGK", "BS"]:
            for i in range(4):
                ly_baris = QHBoxLayout()
                ent = QLineEdit()
                ent.setStyleSheet("background-color: white; color: black; border: 1px solid gray;")
                self.input_dinamis.append(ent)
                ly_baris.addWidget(ent)
                
                if t == "PGK":
                    chk = QCheckBox("Benar")
                    self.cek_kunci.append(chk)
                    ly_baris.addWidget(chk)
                else:
                    cb = AntiScrollComboBox()
                    cb.setStyleSheet("background-color: white; color: black; border: 1px solid gray;")
                    cb.addItems(["B", "S"])
                    self.cek_kunci.append(cb)
                    ly_baris.addWidget(cb)
                self.ly_dinamis.addRow(f"Pernyataan {i+1}:", ly_baris)
        elif t == "ESSAY":
            lbl = QLabel("(Soal Essay dinilai manual oleh Guru)")
            lbl.setStyleSheet("color: blue; font-style: italic;")
            self.ly_dinamis.addRow("", lbl)

    def import_word(self):
        if not DOCX_AVAILABLE:
            return QMessageBox.warning(self, "Library Belum Terpasang", "Fitur ini membutuhkan 'python-docx'.\nJalankan perintah: pip install python-docx")
        
        unik_id = self.cb_paket.currentData()
        if not unik_id: 
            return QMessageBox.warning(self, "Error", "Pilih Paket Ujian terlebih dahulu!")
            
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
                
                # EKSTRAK GAMBAR SEBAGAI INLINE HTML (Gambar akan menyatu dengan teks, bebas posisi)
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
                                    # Tambahkan tag <img> HTML langsung ke dalam teks dengan lebar maksimal 450px
                                    kumpulan_gambar_html += f'<br><img src="data:image/png;base64,{img_b64}" width="450"><br>'
                
                # Deteksi awal nomor soal
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
                        
                    # Bersihkan teks dari awalan soal
                    clean_txt = txt.split(".", 1)[1].replace(f"[{tipe}]", "").strip()
                    
                    curr = {
                        "id": next_id, "tipe": tipe, "bobot": 10.0, 
                        # Field 'gambar' dikosongkan karena gambar kini hidup menyatu di dalam HTML bacaan/soal
                        "bacaan": "", "soal": "", "gambar": "", "sumber_gambar": "" 
                    }
                    if tipe == "PG": curr["opsi"], curr["kunci"] = {}, "A"
                    elif tipe in ["PGK", "BS"]: curr["pernyataan"], curr["kunci"] = [], []
                    next_id += 1
                    
                    if clean_txt:
                        soal_temp.append(f"<p style=\"font-family:'Times New Roman'; font-size:12pt; margin: 0;\">{clean_txt}</p>")
                    if kumpulan_gambar_html:
                        soal_temp.append(kumpulan_gambar_html)
                        
                elif curr:
                    # Ubah [SUMBER: ...] menjadi tulisan miring berwarna abu-abu yang menyatu dengan teks
                    if "[SUMBER:" in txt:
                        sumber_teks = txt[txt.find("[SUMBER:") + 8 : txt.find("]")].strip()
                        txt = txt.replace(txt[txt.find("[SUMBER:") : txt.find("]") + 1], f"<br><i style='color:gray; font-size:10pt;'>Sumber: {sumber_teks}</i><br>").strip()
                        
                    # Deteksi perpindahan target teks (Wacana atau Soal)
                    if "[WACANA]" in txt:
                        mode_input = "wacana"
                        txt = txt.replace("[WACANA]", "").strip()
                    elif "[SOAL]" in txt:
                        mode_input = "soal"
                        txt = txt.replace("[SOAL]", "").strip()
                    
                    is_kunci = txt.lower().startswith("kunci:")
                    is_opsi = curr["tipe"] == "PG" and len(txt) > 2 and txt[0] in "ABCDE" and txt[1] in ".)"
                    is_pernyataan = txt.startswith("-") and curr["tipe"] in ["BS", "PGK"]
                    
                    if is_opsi:
                        curr["opsi"][txt[0].upper()] = txt[2:].strip()
                        mode_input = "biasa"
                        # Jika ada gambar nyasar sebaris dengan opsi, masukkan ke soal utama
                        if kumpulan_gambar_html: soal_temp.append(kumpulan_gambar_html)
                    elif is_kunci:
                        curr["kunci"] = txt.split(":", 1)[1].strip().upper()
                        mode_input = "biasa"
                        if kumpulan_gambar_html: soal_temp.append(kumpulan_gambar_html)
                    elif is_pernyataan:
                        parts = txt.split("[")
                        curr["pernyataan"].append(parts[0].replace("-", "").strip())
                        if len(parts) > 1:
                            val = parts[1].replace("]", "").strip().upper()
                            if curr["tipe"] == "PGK" and val == "BENAR": curr["kunci"].append(len(curr["pernyataan"]) - 1)
                            elif curr["tipe"] == "BS": curr["kunci"].append(val)
                        mode_input = "biasa"
                        if kumpulan_gambar_html: soal_temp.append(kumpulan_gambar_html)
                    elif txt or kumpulan_gambar_html:
                        # GABUNGKAN teks dan gambar yang ada di paragraf ini
                        teks_gabungan = ""
                        if txt:
                            teks_gabungan += f"<p style=\"font-family:'Times New Roman'; font-size:12pt; margin: 0;\">{txt}</p>"
                        if kumpulan_gambar_html:
                            teks_gabungan += kumpulan_gambar_html
                            
                        # Lempar ke penampungan sesuai posisinya (Wacana atau Soal)
                        if mode_input == "wacana":
                            wacana_temp.append(teks_gabungan)
                        else:
                            soal_temp.append(teks_gabungan)
                            
            # Simpan soal terakhir (penutup)
            if curr:
                curr['bacaan'] = "".join(wacana_temp)
                curr['soal'] = "".join(soal_temp)
                soal_list.append(curr)
                
            save_all_dbs()
            self.muat_tabel_soal()
            self.update_tabel_paket()
            QMessageBox.information(self, "Sukses", "Impor Berhasil! Teks, Gambar, dan Sumber disisipkan persis sesuai urutan di MS Word.")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Gagal membaca file Word:\n{str(e)}")

    def unggah_gambar(self):
        fp, _ = QFileDialog.getOpenFileName(self, "Pilih Gambar", "", "Image Files (*.png *.jpg *.jpeg)")
        if fp:
            with open(fp, "rb") as f:
                self.b64_image = base64.b64encode(f.read()).decode('utf-8')
            self.lbl_img_status.setText("Gambar Siap! ✅")

    def lihat_gambar_form(self):
        if not self.b64_image:
            return QMessageBox.information(self, "Info", "Tidak ada gambar tersimpan.")
        d = QDialog(self)
        d.setWindowTitle("Preview Gambar")
        d.resize(500, 500)
        ly = QVBoxLayout(d)
        lbl = QLabel()
        pix = QPixmap()
        pix.loadFromData(base64.b64decode(self.b64_image))
        lbl.setPixmap(pix.scaled(450, 450, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
        ly.addWidget(lbl)
        d.exec()

    def update_cb_file_db(self):
        self.cb_file_db.blockSignals(True)
        self.cb_file_db.clear()
        for fp in DAFTAR_FILE_DB: 
            self.cb_file_db.addItem(os.path.basename(fp), fp)
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
        for i, s in enumerate(soal_list):
            self.tabel_soal.setItem(i, 0, QTableWidgetItem(str(s['id'])))
            self.tabel_soal.setItem(i, 1, QTableWidgetItem(s['tipe']))
            self.tabel_soal.setItem(i, 2, QTableWidgetItem(str(s.get('bobot', 10))))
            teks_bersih = re.sub('<[^<]+?>', '', s['soal'])
            teks_preview = teks_bersih[:50] + "..." if len(teks_bersih)>50 else teks_bersih
            self.tabel_soal.setItem(i, 3, QTableWidgetItem(teks_preview))

    def simpan_soal(self):
        unik_id = self.cb_paket.currentData()
        if not unik_id: return QMessageBox.warning(self, "Error", "Pilih Paket Ujian terlebih dahulu!")
        t = self.cb_tipe.currentText()
        if not self.txt_soal.toPlainText().strip(): return QMessageBox.warning(self, "Error", "Pertanyaan tidak boleh kosong!")
            
        pdata = DATA_UJIAN[unik_id]
        s_id = self.edit_id
        if not s_id:
            exist_ids = [x['id'] for x in pdata['soal']]
            s_id = max(exist_ids) + 1 if exist_ids else 1
            
        ds = {
            "id": s_id, "tipe": t, "bobot": self.sb_bobot.value(),
            "bacaan": self.txt_wacana.toHtml(),
            "soal": self.txt_soal.toHtml(),
            "gambar": self.b64_image, "sumber_gambar": self.ent_sumber.text().strip()
        }
        
        if t == "PG":
            ds["opsi"] = {chr(65+i): e.text() for i, e in enumerate(self.input_dinamis)}
            ds["kunci"] = self.cb_kunci_pg.currentText()
        elif t in ["PGK", "BS"]:
            ds["pernyataan"] = [e.text() for e in self.input_dinamis]
            if t == "PGK":
                ds["kunci"] = [i for i, chk in enumerate(self.cek_kunci) if chk.isChecked()]
            else:
                ds["kunci"] = [cb.currentText() for cb in self.cek_kunci]
        elif t == "ESSAY": ds["kunci"] = ""

        if self.edit_id:
            idx = next(i for i, x in enumerate(pdata['soal']) if x['id'] == s_id)
            pdata['soal'][idx] = ds
        else:
            pdata['soal'].append(ds)
            
        save_all_dbs()
        self.batal_edit()
        self.muat_tabel_soal()
        self.update_tabel_paket()
        QMessageBox.information(self, "Sukses", "Soal berhasil disimpan!")

    def batal_edit(self):
        self.edit_id = None
        self.txt_wacana.clear()
        self.txt_soal.clear()
        self.ent_sumber.clear()
        # Bobot tidak di-reset agar nyaman memasukkan banyak soal dengan bobot sama
        self.b64_image = ""
        self.lbl_img_status.setText("Tidak ada gambar")
        self.btn_simpan.setText("➕ SIMPAN SOAL BARU")
        self.btn_simpan.setStyleSheet("background-color: #0d6efd; color: white; font-weight: bold; padding: 8px;")
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
        self.cb_tipe.setCurrentText(soal['tipe'])
        self.sb_bobot.setValue(soal.get('bobot', 10.0))
        
        bacaan = soal.get('bacaan', '')
        if "<p" in bacaan or "<html" in bacaan: self.txt_wacana.setHtml(bacaan)
        else: self.txt_wacana.editor.setText(bacaan)
        
        tanya = soal['soal']
        if "<p" in tanya or "<html" in tanya: self.txt_soal.setHtml(tanya)
        else: self.txt_soal.editor.setText(tanya)
        
        self.ent_sumber.setText(soal.get('sumber_gambar', ''))
        self.b64_image = soal.get('gambar', '')
        self.lbl_img_status.setText("Gambar ada ✅" if self.b64_image else "Tidak ada gambar")
            
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
        self.btn_simpan.setStyleSheet("background-color: #ffc107; color: black; font-weight: bold; padding: 8px;")
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
        d.setStyleSheet("background-color: white; color: black;")
        ly = QVBoxLayout(d)
        
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        w_scroll = QWidget()
        w_scroll.setStyleSheet("background-color: white; color: black;")
        ly_scroll = QVBoxLayout(w_scroll)
        ly_scroll.setSpacing(10)
        ly_scroll.setContentsMargins(15, 15, 15, 50) 
        
        for s in soal_list:
            lbl_no = QLabel(f"<b>Soal No {s['id']} ({s['tipe']})</b> - Bobot: {s.get('bobot', 10.0)}")
            lbl_no.setStyleSheet("color: blue; font-size: 12pt;")
            ly_scroll.addWidget(lbl_no)
            
            bacaan = s.get('bacaan', '').replace("<br>", "").replace("<p></p>", "").strip()
            if bacaan:
                lbl_wacana = QLabel(f"<b>📄 Teks Bacaan:</b><br>{bacaan}")
                lbl_wacana.setWordWrap(True)
                lbl_wacana.setStyleSheet("font-family: 'Times New Roman'; font-size: 11pt; padding: 10px; border: 1px solid blue; background-color: #f8f9fa;")
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
                
                # Munculkan Sumber Gambar di bawah Gambar
                if s.get('sumber_gambar'):
                    lbl_sumber = QLabel(f"<i>Sumber: {s.get('sumber_gambar')}</i>")
                    lbl_sumber.setStyleSheet("color: gray; font-size: 10pt; font-family: 'Times New Roman';")
                    ly_scroll.addWidget(lbl_sumber)

            if s['tipe'] == 'PG':
                for k, v in s.get('opsi', {}).items():
                    warna = "green" if k == s.get('kunci') else "black"
                    lbl_opsi = QLabel(f"{k}. {v}")
                    lbl_opsi.setWordWrap(True)
                    lbl_opsi.setStyleSheet(f"color: {warna}; font-family: 'Times New Roman';")
                    ly_scroll.addWidget(lbl_opsi)
            elif s['tipe'] in ['PGK', 'BS']:
                for i, p in enumerate(s.get('pernyataan', [])):
                    if s['tipe'] == 'PGK':
                        kunci_teks = "[BENAR]" if i in s.get('kunci', []) else "[SALAH]"
                    else:
                        kunci_teks = f"[{s.get('kunci', [])[i]}]" if i < len(s.get('kunci', [])) else ""
                    lbl_p = QLabel(f"- {p} {kunci_teks}")
                    lbl_p.setWordWrap(True)
                    lbl_p.setStyleSheet("color: green; font-weight: bold; font-family: 'Times New Roman';")
                    ly_scroll.addWidget(lbl_p)
            ly_scroll.addWidget(QLabel("<hr>"))
            
        ly_scroll.addSpacing(40) 
        
        scroll.setWidget(w_scroll)
        ly.addWidget(scroll)
        d.exec()

    def buat_paket(self):
        d = QDialog(self)
        d.setWindowTitle("Paket Baru")
        d.setStyleSheet("background-color: white; color: black;")
        ly = QFormLayout(d)
        e_mapel, e_kelas, e_token = QLineEdit(), QLineEdit(), QLineEdit()
        for e in (e_mapel, e_kelas, e_token): e.setStyleSheet("background-color: white; color: black; border: 1px solid gray;")
        ly.addRow("Mapel:", e_mapel)
        ly.addRow("Kelas:", e_kelas)
        ly.addRow("Token:", e_token)
        btn = QPushButton("Simpan")
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

    # ================= TAB 2: KONTROL PROKTOR & LIVE MONITOR =================
   # ================= TAB 2: KONTROL PROKTOR & LIVE MONITOR =================
    def setup_tab_proktor(self):
        layout_tab = QVBoxLayout(self.tab_proktor)
        
        # 1. BUNGKUS DENGAN SCROLL AREA AGAR TIDAK TERGENCET
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        
        konten_scroll = QWidget()
        konten_scroll.setStyleSheet("background-color: #f4f6f9; color: black;")
        ly = QVBoxLayout(konten_scroll)
        ly.setSpacing(15)
        ly.setContentsMargins(10, 10, 10, 10)
        
        # --- GRUP 1: STATUS SERVER ---
        gb_server = QGroupBox("🌐 Status Server & Keamanan")
        gb_server.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        gb_server.setStyleSheet("background-color: white;")
        ly_server = QVBoxLayout(gb_server)
        
        ip = socket.gethostbyname(socket.gethostname())
        lbl_ip = QLabel(f"IP SERVER PROKTOR: {ip}")
        lbl_ip.setStyleSheet("color: red; font-size: 14pt; font-weight: bold;")
        ly_server.addWidget(lbl_ip)
        
        ly_pwd = QHBoxLayout()
        ly_pwd.addWidget(QLabel("Password Keluar Siswa:"))
        self.ent_pwd = QLineEdit(PROCTOR_PASSWORD)
        self.ent_pwd.setStyleSheet("background-color: white; color: black; padding: 5px; border: 1px solid gray;")
        self.ent_pwd.setEchoMode(QLineEdit.EchoMode.Password)
        btn_pwd = QPushButton("Simpan ke Semua File")
        btn_pwd.setStyleSheet("background-color: #6c757d; color: white; padding: 5px;")
        btn_pwd.clicked.connect(self.simpan_pwd)
        ly_pwd.addWidget(self.ent_pwd)
        ly_pwd.addWidget(btn_pwd)
        ly_pwd.addStretch()
        ly_server.addLayout(ly_pwd)
        ly.addWidget(gb_server)
        
        # --- GRUP 2: PAKET UJIAN ---
        gb_paket = QGroupBox("📦 Status Paket Ujian Aktif")
        gb_paket.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        gb_paket.setStyleSheet("background-color: white;")
        ly_paket = QVBoxLayout(gb_paket)
        
        self.tabel_paket = AntiScrollTableWidget(0, 7)
        self.tabel_paket.setStyleSheet("background-color: white; color: black; gridline-color: #ccc; selection-background-color: #cce5ff; selection-color: black;")
        self.tabel_paket.setHorizontalHeaderLabels(["File Sumber", "Mapel", "Kelas", "Token", "Jml Soal", "Status", "UnikID"])
        self.tabel_paket.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.tabel_paket.setColumnHidden(6, True) 
        self.tabel_paket.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.tabel_paket.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.tabel_paket.setMinimumHeight(120)
        ly_paket.addWidget(self.tabel_paket)
        
        ly_btn_prok = QHBoxLayout()
        btn_on = QPushButton("▶ AKTIFKAN UJIAN")
        btn_on.setStyleSheet("background-color: green; color: white; padding: 5px; font-weight: bold;")
        btn_on.clicked.connect(lambda: self.tog_ujian(True))
        btn_off = QPushButton("⏸ TUTUP UJIAN")
        btn_off.setStyleSheet("background-color: red; color: white; padding: 5px; font-weight: bold;")
        btn_off.clicked.connect(lambda: self.tog_ujian(False))
        btn_reset_autosave = QPushButton("🧹 BERSIHKAN AUTO-SAVE SEMENTARA")
        btn_reset_autosave.setStyleSheet("background-color: #ffc107; color: black; padding: 5px; font-weight: bold;")
        btn_reset_autosave.clicked.connect(self.hapus_autosave)
        
        ly_btn_prok.addWidget(btn_on)
        ly_btn_prok.addWidget(btn_off)
        ly_btn_prok.addSpacing(15)
        ly_btn_prok.addWidget(btn_reset_autosave)
        ly_btn_prok.addStretch()
        ly_paket.addLayout(ly_btn_prok)
        ly.addWidget(gb_paket)
        
        # --- GRUP 3: LIVE MONITOR ---
        gb_live = QGroupBox("🟢 Live Monitor Progres Siswa (Real-Time)")
        gb_live.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        gb_live.setStyleSheet("background-color: white;")
        ly_live = QVBoxLayout(gb_live)
        
        self.tabel_live = AntiScrollTableWidget(0, 5)
        self.tabel_live.setStyleSheet("background-color: white; color: black; gridline-color: #ccc; selection-background-color: #ffcccc; selection-color: black;")
        self.tabel_live.setHorizontalHeaderLabels(["NIS", "Token", "Terjawab", "Total Soal", "Progres (%)"])
        self.tabel_live.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.Stretch)
        self.tabel_live.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.tabel_live.setMinimumHeight(150)
        ly_live.addWidget(self.tabel_live)
        
        btn_kick = QPushButton("🔄 RESET / KICK SISWA TERPILIH KEMBALI KE LOGIN")
        btn_kick.setStyleSheet("background-color: #dc3545; color: white; font-weight: bold; padding: 8px;")
        btn_kick.clicked.connect(self.kick_siswa)
        ly_live.addWidget(btn_kick)
        ly.addWidget(gb_live)
        
        # --- GRUP 4: HASIL PERMANEN ---
        gb_hasil = QGroupBox("💾 Rekap Hasil Ujian (Permanen)")
        gb_hasil.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        gb_hasil.setStyleSheet("background-color: white;")
        ly_hasil = QVBoxLayout(gb_hasil)
        
        ly_h_hasil = QHBoxLayout()
        btn_csv = QPushButton("📥 UNDUH HASIL CSV")
        btn_csv.setStyleSheet("background-color: #17a2b8; color: white; padding: 5px; font-weight: bold;")
        btn_csv.clicked.connect(self.unduh_csv)
        btn_analisis = QPushButton("📊 ANALISIS SOAL CSV")
        btn_analisis.setStyleSheet("background-color: #fd7e14; color: white; padding: 5px; font-weight: bold;")
        btn_analisis.clicked.connect(self.unduh_analisis_soal)
        btn_hapus_hasil = QPushButton("🗑️ HAPUS HASIL TERPILIH")
        btn_hapus_hasil.setStyleSheet("background-color: #e83e8c; color: white; padding: 5px; font-weight: bold;")
        btn_hapus_hasil.clicked.connect(self.hapus_hasil_ujian)

        ly_h_hasil.addWidget(btn_csv)
        ly_h_hasil.addWidget(btn_analisis)
        ly_h_hasil.addWidget(btn_hapus_hasil)
        ly_h_hasil.addStretch()
        ly_hasil.addLayout(ly_h_hasil)
        
        ly_h_filter = QHBoxLayout()
        ly_h_filter.addWidget(QLabel("Filter Paket:"))
        self.cb_filter_hasil = AntiScrollComboBox()
        self.cb_filter_hasil.setStyleSheet("background-color: white; color: black; border: 1px solid gray; padding: 2px;")
        self.cb_filter_hasil.addItem("Semua Paket dari Semua File")
        self.cb_filter_hasil.currentTextChanged.connect(self.update_tabel_hasil_langsung)
        self.cb_filter_hasil.setMinimumWidth(300)
        ly_h_filter.addWidget(self.cb_filter_hasil)
        ly_h_filter.addStretch()
        ly_hasil.addLayout(ly_h_filter)

        self.tabel_hasil = AntiScrollTableWidget(0, 4)
        self.tabel_hasil.setStyleSheet("background-color: white; color: black; gridline-color: #ccc; selection-background-color: #cce5ff; selection-color: black;")
        self.tabel_hasil.setHorizontalHeaderLabels(["Nama", "Kelas", "Mapel", "Skor Akhir"])
        self.tabel_hasil.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.tabel_hasil.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.tabel_hasil.setMinimumHeight(180)
        self.tabel_hasil.cellDoubleClicked.connect(self.cek_detail_essay)
        ly_hasil.addWidget(self.tabel_hasil)
        
        ly.addWidget(gb_hasil)

        # PASANG SCROLL KE LAYOUT TAB
        scroll.setWidget(konten_scroll)
        layout_tab.addWidget(scroll)
        
        self.update_tabel_paket()

    def kick_siswa(self):
        baris = self.tabel_live.currentRow()
        if baris < 0: return QMessageBox.warning(self, "Peringatan", "Pilih siswa dari tabel Live Monitor.")
        nis = self.tabel_live.item(baris, 0).text()
        token = self.tabel_live.item(baris, 1).text()
        kunci = f"{nis}_{token}"
        
        tanya = QMessageBox.question(self, "Konfirmasi Reset", f"Keluarkan NIS {nis} kembali ke Menu Login secara remote?")
        if tanya == QMessageBox.StandardButton.Yes:
            FLAG_RESET.add(kunci)
            QMessageBox.information(self, "Info", f"Sinyal Reset dikirim. Laptop siswa {nis} akan kembali ke Login dalam 3 detik.")

    def hapus_autosave(self):
        tanya = QMessageBox.question(self, "Konfirmasi", "Bersihkan seluruh data Auto-Save untuk sesi baru?")
        if tanya == QMessageBox.StandardButton.Yes:
            global JAWABAN_SEMENTARA
            JAWABAN_SEMENTARA.clear()
            try:
                if os.path.exists(AUTOSAVE_FILE): os.remove(AUTOSAVE_FILE)
                QMessageBox.information(self, "Sukses", "Data Auto-Save dibersihkan!")
            except Exception as e:
                QMessageBox.warning(self, "Error", str(e))

    def hapus_hasil_ujian(self):
        filter_text = self.cb_filter_hasil.currentText()
        if QMessageBox.question(self, "Hapus Hasil", f"Hapus hasil ujian untuk: {filter_text}?") == QMessageBox.StandardButton.Yes:
            global HASIL_SISWA
            if filter_text == "Semua Paket dari Semua File": HASIL_SISWA.clear()
            else:
                kunci_hapus = [k for k, d in HASIL_SISWA.items() if f"{d['mapel']} - Kls {d['kelas']} ({d['token']})" == filter_text]
                for k in kunci_hapus: del HASIL_SISWA[k]
            save_hasil()
            self.update_tabel_hasil_dan_live()

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
        self.tabel_paket.setRowCount(len(DATA_UJIAN))
        for i, (unik_id, v) in enumerate(DATA_UJIAN.items()):
            self.tabel_paket.setItem(i, 0, QTableWidgetItem(os.path.basename(v['_file_asal'])))
            self.tabel_paket.setItem(i, 1, QTableWidgetItem(v['mapel']))
            self.tabel_paket.setItem(i, 2, QTableWidgetItem(v['kelas']))
            self.tabel_paket.setItem(i, 3, QTableWidgetItem(v['token']))
            self.tabel_paket.setItem(i, 4, QTableWidgetItem(str(len(v['soal']))))
            self.tabel_paket.setItem(i, 5, QTableWidgetItem("🟢 Aktif" if v.get('aktif') else "🔴 Tutup"))
            self.tabel_paket.setItem(i, 6, QTableWidgetItem(unik_id))
            
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
        self.update_tabel_hasil_dan_live()

    def update_tabel_hasil_dan_live(self):
        # Update Live Monitor
        self.tabel_live.setRowCount(len(JAWABAN_SEMENTARA))
        for i, (kunci, data) in enumerate(JAWABAN_SEMENTARA.items()):
            parts = kunci.split("_", 1)
            nis = parts[0]
            token = parts[1] if len(parts) > 1 else ""
            paket = next((p for p in DATA_UJIAN.values() if p['token'] == token), None)
            total = len(paket['soal']) if paket else 0
            
            terjawab = data.get("terjawab", 0) if isinstance(data, dict) else (len([k for k in data.keys() if data[k]]) if isinstance(data, dict) else 0)
            pct = f"{(terjawab/total)*100:.0f}%" if total > 0 else "0%"
            
            self.tabel_live.setItem(i, 0, QTableWidgetItem(nis))
            self.tabel_live.setItem(i, 1, QTableWidgetItem(token))
            self.tabel_live.setItem(i, 2, QTableWidgetItem(str(terjawab)))
            self.tabel_live.setItem(i, 3, QTableWidgetItem(str(total)))
            self.tabel_live.setItem(i, 4, QTableWidgetItem(pct))

        # Update Hasil Permanen
        filter_text = self.cb_filter_hasil.currentText()
        data_filtered = [d for k, d in HASIL_SISWA.items() if filter_text == "Semua Paket dari Semua File" or f"{d['mapel']} - Kls {d['kelas']} ({d['token']})" == filter_text]
        self.tabel_hasil.setRowCount(len(data_filtered))
        for i, d in enumerate(data_filtered):
            self.tabel_hasil.setItem(i, 0, QTableWidgetItem(d['nama']))
            self.tabel_hasil.setItem(i, 1, QTableWidgetItem(d['kelas']))
            self.tabel_hasil.setItem(i, 2, QTableWidgetItem(d['mapel']))
            self.tabel_hasil.setItem(i, 3, QTableWidgetItem(f"{d['skor']:.2f}"))

    def cek_detail_essay(self, baris, kolom):
        nama = self.tabel_hasil.item(baris, 0).text()
        kls = self.tabel_hasil.item(baris, 1).text()
        d = next((x for x in HASIL_SISWA.values() if x['nama']==nama and str(x['kelas'])==kls), None)
        if not d: return
        p = next((x for x in DATA_UJIAN.values() if x['token']==d['token']), None)
        
        d_win = QDialog(self)
        d_win.setWindowTitle(f"Detail Jawaban - {nama}")
        d_win.resize(700, 600)
        d_win.setStyleSheet("background-color: white; color: black;")
        ly = QVBoxLayout(d_win)
        lbl = QLabel(f"<b>{nama}</b> | Skor: {d['skor']:.2f}")
        lbl.setFont(QFont("Segoe UI", 14))
        ly.addWidget(lbl)
        txt = QTextEdit()
        txt.setReadOnly(True)
        txt.setStyleSheet("background-color: #f8f9fa; color: black; font-family: 'Times New Roman'; font-size: 11pt;")
        
        for soal in (p['soal'] if p else []):
            tipe = soal['tipe']
            sid = str(soal['id'])
            jwb = d['detail'].get(sid, '[Tidak Dijawab]')
            kunci = soal.get('kunci', '')
            
            html = f"<b>Soal No {soal['id']} ({tipe}) - Bobot: {soal.get('bobot', 10):.2f}</b><br>"
            if soal.get('bacaan'): html += f"<i>Teks Bacaan: {soal['bacaan']}</i><br><br>"
            html += f"Tanya: {soal['soal']}<br>"
            
            if tipe == 'ESSAY':
                html += f"Jawaban Siswa:<br><font color='blue'>{jwb}</font><br>"
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
        if filter_text == "Semua Paket dari Semua File":
            return QMessageBox.warning(self, "Peringatan", "Pilih salah satu paket di Filter Paket terlebih dahulu.")
            
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
                for s in paket['soal']:
                    sid = str(s['id'])
                    tanya_singkat = re.sub('<[^<]+?>', '', s['soal'])[:60]
                    if s['tipe'] == 'PG':
                        benar = sum(1 for d in data_filtered if d['detail'].get(sid) == s.get('kunci'))
                        salah = total_siswa - benar
                        pct = f"{(benar/total_siswa)*100:.1f}%" if total_siswa > 0 else "0%"
                        writer.writerow([sid, s['tipe'], tanya_singkat, benar, salah, pct])
                    elif s['tipe'] == 'ESSAY':
                        writer.writerow([sid, s['tipe'], tanya_singkat, "Manual", "Manual", "-"])
            QMessageBox.information(self, "Sukses", f"Analisis disimpan ke:\n{os.path.basename(fp)}")
        except Exception as e: QMessageBox.critical(self, "Error", str(e))

    # ================= TAB 3: DATA AKUN SISWA =================
    def setup_tab_siswa(self):
        ly = QVBoxLayout(self.tab_siswa)
        ly.setContentsMargins(10, 10, 10, 10)
        
        ly_top = QHBoxLayout()
        ly_top.addWidget(QLabel("<b>Daftar Akun Siswa (Tersinkron ke Semua File JSON):</b>"))
        ly_top.addStretch()
        
        btn_tambah = QPushButton("➕ Tambah Akun")
        btn_tambah.setStyleSheet("background-color: #28a745; color: white; font-weight: bold; padding: 6px 12px;")
        btn_tambah.clicked.connect(self.tambah_akun_manual)
        
        btn_edit = QPushButton("✏️ Edit Akun")
        btn_edit.setStyleSheet("background-color: #ffc107; color: black; font-weight: bold; padding: 6px 12px;")
        btn_edit.clicked.connect(self.edit_akun_manual)
        
        btn_hapus = QPushButton("🗑️ Hapus Akun")
        btn_hapus.setStyleSheet("background-color: #dc3545; color: white; font-weight: bold; padding: 6px 12px;")
        btn_hapus.clicked.connect(self.hapus_akun_manual)
        
        ly_top.addWidget(btn_tambah)
        ly_top.addWidget(btn_edit)
        ly_top.addWidget(btn_hapus)
        ly.addLayout(ly_top)
        
        self.tabel_akun = AntiScrollTableWidget(0, 4)
        self.tabel_akun.setStyleSheet("background-color: white; color: black; gridline-color: #ccc;")
        self.tabel_akun.setHorizontalHeaderLabels(["NIS / Username", "Nama Lengkap", "Kelas", "Password Akun"])
        self.tabel_akun.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.tabel_akun.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.tabel_akun.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        ly.addWidget(self.tabel_akun)
        self.update_tabel_akun()

    def tambah_akun_manual(self):
        d = QDialog(self)
        d.setWindowTitle("Tambah Akun Siswa Baru")
        d.resize(350, 200)
        d.setStyleSheet("background-color: white; color: black;")
        ly = QFormLayout(d)
        e_nis, e_nama, e_kelas, e_pass = QLineEdit(), QLineEdit(), QLineEdit(), QLineEdit()
        for e in (e_nis, e_nama, e_kelas, e_pass): e.setStyleSheet("padding: 5px; border: 1px solid gray;")
        ly.addRow("NIS / Username:", e_nis)
        ly.addRow("Nama Lengkap:", e_nama)
        ly.addRow("Kelas:", e_kelas)
        ly.addRow("Password Login:", e_pass)
        btn = QPushButton("Simpan Akun")
        btn.setStyleSheet("background-color: #0d6efd; color: white; font-weight: bold; padding: 8px;")
        btn.clicked.connect(lambda: d.accept())
        ly.addRow("", btn)
        if d.exec() == QDialog.DialogCode.Accepted:
            nis = e_nis.text().strip()
            if not nis or not e_nama.text().strip() or not e_pass.text().strip(): 
                return QMessageBox.warning(self, "Error", "Wajib mengisi semua kolom!")
            if nis in AKUN_SISWA: 
                return QMessageBox.warning(self, "Error", "NIS ini sudah terdaftar!")
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
        d.resize(350, 200)
        d.setStyleSheet("background-color: white; color: black;")
        ly = QFormLayout(d)
        e_nis = QLineEdit(nis_lama)
        e_nama = QLineEdit(data_lama['nama'])
        e_kelas = QLineEdit(data_lama['kelas'])
        e_pass = QLineEdit(data_lama['password'])
        for e in (e_nis, e_nama, e_kelas, e_pass): e.setStyleSheet("padding: 5px; border: 1px solid gray;")
        ly.addRow("NIS / Username:", e_nis)
        ly.addRow("Nama Lengkap:", e_nama)
        ly.addRow("Kelas:", e_kelas)
        ly.addRow("Password Login:", e_pass)
        btn = QPushButton("Simpan Perubahan")
        btn.setStyleSheet("background-color: #ffc107; color: black; font-weight: bold; padding: 8px;")
        btn.clicked.connect(lambda: d.accept())
        ly.addRow("", btn)
        if d.exec() == QDialog.DialogCode.Accepted:
            nis_baru = e_nis.text().strip()
            if not nis_baru or not e_nama.text().strip() or not e_pass.text().strip(): 
                return QMessageBox.warning(self, "Error", "Semua kolom wajib diisi!")
            if nis_baru != nis_lama and nis_baru in AKUN_SISWA: 
                return QMessageBox.warning(self, "Error", "NIS baru sudah dipakai akun lain!")
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

if __name__ == '__main__':
    app = QApplication(sys.argv)
    app.setStyle("Fusion") 
    window = GuruApp()
    window.show()
    sys.exit(app.exec())