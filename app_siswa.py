import sys
import os
import requests
import base64
import keyboard
import ctypes
import threading
import random
import atexit # Untuk merestart explorer.exe jika aplikasi tertutup tiba-tiba
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                             QLabel, QLineEdit, QPushButton, QMessageBox, QStackedWidget,
                             QScrollArea, QRadioButton, QCheckBox, QButtonGroup, QGridLayout,
                             QTextEdit, QInputDialog, QGraphicsDropShadowEffect, QProgressBar, QDialog)
from PyQt6.QtGui import QFont, QPixmap, QIcon, QColor, QMovie
from PyQt6.QtCore import Qt, QTimer, QThread, pyqtSignal, QMetaObject, QSize

def dapatkan_path_file(nama_file):
    # 1. Cek di VS Code (Path Relatif)
    if os.path.exists(nama_file):
        return os.path.abspath(nama_file)
        
    # 2. Cek di dalam folder _internal (Jika dibawa otomatis oleh PyInstaller)
    try:
        base_path = sys._MEIPASS
        path_meipass = os.path.join(base_path, nama_file)
        if os.path.exists(path_meipass):
            return path_meipass
    except Exception:
        pass
        
    # 3. Cek berdampingan dengan file .exe (Jika paste folder manual)
    if getattr(sys, 'frozen', False):
        base_exe = os.path.dirname(sys.executable)
        path_exe = os.path.join(base_exe, nama_file)
        if os.path.exists(path_exe):
            return path_exe
            
    return os.path.abspath(nama_file)

def terapkan_bayangan(widget, radius=35, y_offset=14, alpha=25):
    shadow = QGraphicsDropShadowEffect()
    shadow.setBlurRadius(radius)
    shadow.setColor(QColor(99, 102, 241, alpha))
    shadow.setOffset(0, y_offset)
    widget.setGraphicsEffect(shadow)

class PopupTransisiDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.Dialog)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setFixedSize(340, 320)
        
        ly = QVBoxLayout(self)
        ly.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        box = QWidget()
        box.setStyleSheet("background-color: white; border-radius: 24px; border: 2px solid #E2E8F0;")
        terapkan_bayangan(box, radius=35, y_offset=12, alpha=40)
        
        ly_box = QVBoxLayout(box)
        ly_box.setAlignment(Qt.AlignmentFlag.AlignCenter)
        ly_box.setContentsMargins(25, 25, 25, 25)
        
        self.lbl_gif = QLabel()
        self.lbl_gif.setFixedSize(130, 130)
        self.lbl_gif.setAlignment(Qt.AlignmentFlag.AlignCenter)
        ly_box.addWidget(self.lbl_gif)
        
        try:
            folder_gif = dapatkan_path_file("gif")
            if os.path.exists(folder_gif):
                gif_files = [f for f in os.listdir(folder_gif) if f.lower().endswith('.gif')]
                if gif_files:
                    pilih_gif = os.path.join(folder_gif, random.choice(gif_files))
                    self.movie = QMovie(pilih_gif)
                    self.movie.setScaledSize(QSize(120, 120))
                    self.lbl_gif.setMovie(self.movie)
                    self.movie.start()
                else:
                    self.lbl_gif.setText("🎉")
                    self.lbl_gif.setFont(QFont("Segoe UI", 45))
            else:
                self.lbl_gif.setText("🔥")
                self.lbl_gif.setFont(QFont("Segoe UI", 45))
        except:
            self.lbl_gif.setText("✨")
            self.lbl_gif.setFont(QFont("Segoe UI", 45))
            
        pesan_list = ["Hebat! Lanjut Terus! 🚀", "Keren Banget! Semangat! ⭐", "Mantap! Soal Berikutnya! 🔥", "Luar Biasa! Hebat! 🎯", "Hebat, Teruskan! ✨"]
        lbl_msg = QLabel(random.choice(pesan_list))
        lbl_msg.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        lbl_msg.setStyleSheet("color: #4F46E5; background: transparent; border: none; margin-top: 12px;")
        lbl_msg.setAlignment(Qt.AlignmentFlag.AlignCenter)
        ly_box.addWidget(lbl_msg)
        
        ly.addWidget(box)
        QTimer.singleShot(1100, self.close)
        
    def mousePressEvent(self, event):
        self.close()

class NetworkWorker(QThread):
    finished = pyqtSignal(dict)
    failed = pyqtSignal(str)

    def __init__(self, url, payload):
        super().__init__()
        self.url = url
        self.payload = payload

    def run(self):
        try:
            r = requests.post(self.url, json=self.payload, timeout=15)
            data = r.json()
            self.finished.emit(data)
        except Exception as e:
            self.failed.emit(str(e))

class SiswaApp(QMainWindow):
    sinyal_kick = pyqtSignal()
    sinyal_koneksi = pyqtSignal(bool)

    def __init__(self):
        super().__init__()
        self.setWindowTitle("ExamBrowser Siswa - SMA Islam Darussalam")
        
        ikon_path = dapatkan_path_file("logo.jpg")
        if os.path.exists(ikon_path): 
            self.setWindowIcon(QIcon(ikon_path))
            
        try:
            myappid = 'smaid.cbt.siswa.1.0'
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
        except: pass
        
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint)
        self.showFullScreen()
        
        self.setStyleSheet("background-color: #F1F5F9; color: #0F172A; font-family: 'Segoe UI';")
        
        self.boleh_tutup = False 
        self.is_dialog_open = False 
        self.sedang_di_kick = False 
        
        self.blokir_keyboard() 
        
        self.server_ip = ""
        self.nis, self.nama, self.kelas, self.token, self.mapel = "", "", "", "", ""
        self.soal_list, self.jawaban = [], {}
        self.indeks_soal = 0
        self.proctor_pwd = ""
        self.soal_sudah_dipopup = set()

        self.sinyal_kick.connect(self.reset_ke_login_dari_server)
        self.sinyal_koneksi.connect(self.update_ui_koneksi)

        self.w_utama = QStackedWidget()
        self.setCentralWidget(self.w_utama)
        
        self.setup_login_ui()
        self.setup_token_ui()
        self.setup_ujian_ui()
        self.setup_selesai_ui()
        
        self.w_utama.setCurrentIndex(0)
        self.timer_anti_cheat = QTimer()
        self.timer_anti_cheat.timeout.connect(self.patroli_fokus)
        
        self.timer_beranda = QTimer()
        self.timer_beranda.timeout.connect(self.cek_kick_dari_beranda)
        
        self.timer_autosave = QTimer()
        self.timer_autosave.timeout.connect(self.kirim_autosave)

        # Mendaftarkan fungsi penghidupan Windows jika aplikasi tertutup paksa
        atexit.register(self.hidupkan_explorer)

    # ================= SISTEM ANTI-CHEAT (Mematikan Explorer) =================
    def matikan_explorer(self):
        try: os.system("taskkill /f /im explorer.exe")
        except: pass

    def hidupkan_explorer(self):
        try: os.system("start explorer.exe")
        except: pass

    def changeEvent(self, event):
        if event.type() == event.Type.ActivationChange:
            if getattr(self, 'is_dialog_open', False): return
            if self.w_utama.currentIndex() == 2 and not self.isActiveWindow():
                self.setWindowState(self.windowState() & ~Qt.WindowState.WindowMinimized | Qt.WindowState.WindowActive)
                self.activateWindow()
                self.raise_()
        super().changeEvent(event)

    def patroli_fokus(self):
        if getattr(self, 'is_dialog_open', False): return
        if self.w_utama.currentIndex() == 2 and not self.isActiveWindow():
            self.setWindowState(self.windowState() & ~Qt.WindowState.WindowMinimized | Qt.WindowState.WindowActive)
            self.activateWindow()
            self.raise_()

    def blokir_keyboard(self):
        try:
            keyboard.block_key('windows')
            keyboard.block_key('left windows')
            keyboard.block_key('right windows')
            keyboard.block_key('alt')
            keyboard.add_hotkey('alt+tab', lambda: None, suppress=True)
            keyboard.add_hotkey('ctrl+win+d', lambda: None, suppress=True)
            keyboard.add_hotkey('ctrl+win+right', lambda: None, suppress=True)
            keyboard.add_hotkey('ctrl+win+left', lambda: None, suppress=True)
            keyboard.add_hotkey('ctrl+esc', lambda: None, suppress=True)
        except: pass 

    def buka_blokir_keyboard(self):
        try: keyboard.unhook_all()
        except: pass

    def closeEvent(self, event):
        if getattr(self, 'boleh_tutup', False): event.accept()
        else: event.ignore()

    # ================= 1. HALAMAN LOGIN =================
    def setup_login_ui(self):
        w = QWidget()
        ly = QVBoxLayout(w)
        ly.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        box = QWidget()
        box.setStyleSheet("""
            QWidget { background-color: white; border-radius: 28px; border: 1px solid #E2E8F0; }
            QLineEdit { border: 2px solid #E2E8F0; border-radius: 14px; padding: 14px; font-size: 11pt; background-color: #F8FAFC; color: #0F172A; }
            QLineEdit:focus { border: 2px solid #6366F1; background-color: white; }
            QPushButton#btnLogin { background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #6366F1, stop:1 #EC4899); color: white; font-weight: bold; border-radius: 14px; padding: 14px; font-size: 12pt; border: none; }
            QPushButton#btnLogin:hover { background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #4F46E5, stop:1 #DB2777); }
            QPushButton#btnExit { background-color: #FEF2F2; color: #EF4444; font-weight: bold; border-radius: 14px; padding: 10px; font-size: 10pt; border: none; }
            QPushButton#btnExit:hover { background-color: #EF4444; color: white; }
        """)
        box.setFixedSize(460, 570)
        terapkan_bayangan(box)
        
        ly_box = QVBoxLayout(box)
        ly_box.setContentsMargins(40, 35, 40, 35)
        ly_box.setSpacing(12)
        
        lbl_img = QLabel()
        lbl_img.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl_img.setStyleSheet("background: transparent; border: none;")
        ikon_path = dapatkan_path_file("logo.jpg")
        if os.path.exists(ikon_path):
            pix = QPixmap(ikon_path)
            lbl_img.setPixmap(pix.scaled(80, 80, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
            ly_box.addWidget(lbl_img)
            
        lbl_judul = QLabel("✨ CBT SISWA GEN-Z ✨\nSMA Islam Darussalam")
        lbl_judul.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl_judul.setFont(QFont("Segoe UI", 15, QFont.Weight.Bold))
        lbl_judul.setStyleSheet("color: #0F172A; border: none; background: transparent;")
        ly_box.addWidget(lbl_judul)
        
        ly_box.addSpacing(5)
        self.inp_ip = QLineEdit()
        self.inp_ip.setPlaceholderText("🌐 IP Server (Contoh: 192.168.1.10)")
        
        self.inp_nis = QLineEdit()
        self.inp_nis.setPlaceholderText("👤 NIS / Username")
        
        self.inp_pwd = QLineEdit()
        self.inp_pwd.setPlaceholderText("🔒 Password Siswa")
        self.inp_pwd.setEchoMode(QLineEdit.EchoMode.Password)
        
        ly_box.addWidget(self.inp_ip)
        ly_box.addWidget(self.inp_nis)
        ly_box.addWidget(self.inp_pwd)
        
        ly_box.addSpacing(10)
        btn_login = QPushButton("MASUK UJIAN 🚀")
        btn_login.setObjectName("btnLogin")
        btn_login.clicked.connect(self.proses_login)
        ly_box.addWidget(btn_login)
        
        btn_keluar = QPushButton("Keluar Aplikasi")
        btn_keluar.setObjectName("btnExit")
        btn_keluar.clicked.connect(self.keluar_dari_login)
        ly_box.addWidget(btn_keluar)
        
        ly.addWidget(box)
        self.w_utama.addWidget(w)

    def proses_login(self):
        ip = self.inp_ip.text().strip()
        nis = self.inp_nis.text().strip()
        pwd = self.inp_pwd.text().strip()
        if not ip or not nis or not pwd: return self.tampil_pesan("Oops! 🛑", "Semua kolom wajib diisi ya!")
        self.server_ip = f"http://{ip}:5000"
        self.active_worker = NetworkWorker(f"{self.server_ip}/api/login_siswa", {"nis": nis, "password": pwd})
        self.active_worker.finished.connect(self.setelah_login)
        self.active_worker.failed.connect(lambda err: self.tampil_pesan("Koneksi Gagal ⚠️", "Gagal terhubung ke Server Proktor."))
        self.active_worker.start()

    def setelah_login(self, data):
        if data.get('status') == 'sukses':
            self.nis = self.inp_nis.text().strip()
            self.nama = data['nama']
            self.kelas = data['kelas']
            self.w_utama.setCurrentIndex(1)
            self.timer_beranda.start(3000) 
        else: self.tampil_pesan("Gagal Login ❌", data.get('pesan', 'Kesalahan tidak diketahui'))

    def cek_kick_dari_beranda(self):
        if getattr(self, 'sedang_di_kick', False): return
        threading.Thread(target=self.proses_cek_kick_bg, daemon=True).start()

    def proses_cek_kick_bg(self):
        if not self.server_ip or not self.nis: return
        try:
            r = requests.post(f"{self.server_ip}/api/cek_status_siswa", json={"nis": self.nis, "token": "LOGIN"}, timeout=3)
            if r.json().get("status") == "kick":
                self.sinyal_kick.emit()
        except: pass

    # ================= 2. HALAMAN TOKEN =================
    def setup_token_ui(self):
        w = QWidget()
        ly = QVBoxLayout(w)
        ly.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        box = QWidget()
        box.setStyleSheet("""
            QWidget { background-color: white; border-radius: 28px; border: 1px solid #E2E8F0; }
            QLineEdit { border: 2px dashed #6366F1; border-radius: 16px; padding: 15px; font-size: 18pt; font-weight: bold; background-color: #EEF2FF; color: #4F46E5; }
            QLineEdit:focus { border: 2px solid #6366F1; background-color: white; }
            QPushButton#btnMulai { background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #10B981, stop:1 #06B6D4); color: white; font-weight: bold; border-radius: 14px; padding: 14px; font-size: 12pt; border: none; }
            QPushButton#btnMulai:hover { background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #059669, stop:1 #0891B2); }
            QPushButton#btnBack { background-color: #F1F5F9; color: #475569; font-weight: bold; border-radius: 14px; padding: 10px; font-size: 10pt; border: none; }
            QPushButton#btnBack:hover { background-color: #E2E8F0; }
        """)
        box.setFixedSize(460, 390)
        terapkan_bayangan(box)
        
        ly_box = QVBoxLayout(box)
        ly_box.setContentsMargins(40, 40, 40, 40)
        
        lbl = QLabel("🔑 Masukkan Token Ujian")
        lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
        lbl.setStyleSheet("color: #0F172A; border: none; background: transparent; margin-bottom: 5px;")
        ly_box.addWidget(lbl)
        
        self.inp_token = QLineEdit()
        self.inp_token.setAlignment(Qt.AlignmentFlag.AlignCenter)
        ly_box.addWidget(self.inp_token)
        
        ly_box.addSpacing(15)
        btn_mulai = QPushButton("MULAI UJIAN ⚡")
        btn_mulai.setObjectName("btnMulai")
        btn_mulai.clicked.connect(self.proses_token)
        ly_box.addWidget(btn_mulai)
        
        ly_box.addSpacing(5)
        btn_kembali = QPushButton("← Ganti Akun")
        btn_kembali.setObjectName("btnBack")
        btn_kembali.clicked.connect(self.reset_ke_login)
        ly_box.addWidget(btn_kembali)
        
        ly.addWidget(box)
        self.w_utama.addWidget(w)

    def proses_token(self):
        token = self.inp_token.text().strip().upper()
        if not token: return self.tampil_pesan("Oops! 🛑", "Token ujian wajib diisi!")
        self.active_worker = NetworkWorker(f"{self.server_ip}/api/auth_soal", {"token": token, "nis": self.nis})
        self.active_worker.finished.connect(lambda data: self.setelah_auth_soal(token, data))
        self.active_worker.failed.connect(lambda err: self.tampil_pesan("Koneksi Gagal ⚠️", "Gagal terhubung."))
        self.active_worker.start()

    def setelah_auth_soal(self, token, data):
        if data.get('status') == 'sukses':
            self.matikan_explorer() # Mematikan Windows Explorer untuk mencegah swipe desktop
            
            self.timer_beranda.stop() 
            
            self.token, self.mapel = token, data['mapel']
            self.proctor_pwd, self.soal_list = data.get('proctor_pwd', 'admin123'), data['soal']
            self.jawaban = data.get('jawaban_tersimpan', {}) 
            self.indeks_soal = 0
            self.soal_sudah_dipopup = set()
            self.buat_navigasi_soal()
            self.render_soal_aktif()
            self.w_utama.setCurrentIndex(2)
            
            self.timer_anti_cheat.start(500) 
            self.timer_autosave.start(10000) # Auto-save dikirim ke server setiap 10 detik
        else: self.tampil_pesan("Gagal ❌", data.get('pesan', 'Token tidak valid'))

    # ================= 3. HALAMAN UJIAN UTAMA =================
    def setup_ujian_ui(self):
        w = QWidget()
        ly_utama = QVBoxLayout(w)
        ly_utama.setContentsMargins(20, 20, 20, 20)
        ly_utama.setSpacing(15)
        
        w_header = QWidget()
        w_header.setStyleSheet("QWidget { background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #4F46E5, stop:1 #9333EA); border-radius: 16px; }")
        terapkan_bayangan(w_header, radius=20, y_offset=6, alpha=20)
        ly_h = QHBoxLayout(w_header)
        ly_h.setContentsMargins(25, 18, 25, 18)
        
        self.lbl_info_ujian = QLabel()
        self.lbl_info_ujian.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        self.lbl_info_ujian.setStyleSheet("color: white; border: none; background: transparent;")
        ly_h.addWidget(self.lbl_info_ujian)
        
        ly_h.addStretch()
        
        self.lbl_status_koneksi = QLabel("🟢 Terhubung ke Guru")
        self.lbl_status_koneksi.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        self.lbl_status_koneksi.setStyleSheet("background-color: #10B981; color: white; padding: 6px 12px; border-radius: 8px;")
        ly_h.addWidget(self.lbl_status_koneksi)
        
        ly_utama.addWidget(w_header)
        
        ly_konten = QHBoxLayout()
        ly_konten.setSpacing(15)
        
        w_kiri = QWidget()
        w_kiri.setStyleSheet("background-color: white; border-radius: 16px; border: 1px solid #E2E8F0;")
        terapkan_bayangan(w_kiri)
        ly_kiri = QVBoxLayout(w_kiri)
        ly_kiri.setContentsMargins(30, 25, 30, 25)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setStyleSheet("""
            QProgressBar { background-color: #F1F5F9; border-radius: 8px; height: 16px; text-align: center; color: #0F172A; font-weight: bold; font-size: 9pt; }
            QProgressBar::chunk { background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #6366F1, stop:1 #EC4899); border-radius: 8px; }
        """)
        self.progress_bar.setValue(0)
        ly_kiri.addWidget(self.progress_bar)
        
        self.scroll_soal = QScrollArea()
        self.scroll_soal.setWidgetResizable(True)
        self.scroll_soal.setStyleSheet("QScrollArea { border: none; background-color: transparent; }")
        
        self.w_konten_soal = QWidget()
        self.w_konten_soal.setStyleSheet("background-color: transparent;")
        self.ly_konten_soal = QVBoxLayout(self.w_konten_soal)
        self.ly_konten_soal.setSpacing(15)
        self.scroll_soal.setWidget(self.w_konten_soal)
        ly_kiri.addWidget(self.scroll_soal)
        
        ly_nav_bawah = QHBoxLayout()
        self.btn_prev = QPushButton("◀ Sebelumnya")
        self.btn_next = QPushButton("Selanjutnya ▶")
        
        nav_style = "QPushButton { background-color: #F1F5F9; color: #475569; font-weight: bold; border-radius: 14px; padding: 12px 24px; font-size: 11pt; border: none; } QPushButton:hover { background-color: #E2E8F0; } QPushButton:disabled { background-color: #F8FAFC; color: #CBD5E1; }"
        nav_style_next = "QPushButton { background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #6366F1, stop:1 #EC4899); color: white; font-weight: bold; border-radius: 14px; padding: 12px 24px; font-size: 11pt; border: none; } QPushButton:hover { background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #4F46E5, stop:1 #DB2777); } QPushButton:disabled { background-color: #C7D2FE; color: white; }"
        
        self.btn_prev.setStyleSheet(nav_style)
        self.btn_next.setStyleSheet(nav_style_next)
        
        self.btn_prev.clicked.connect(lambda: self.pindah_soal(-1))
        self.btn_next.clicked.connect(lambda: self.pindah_soal(1))
        ly_nav_bawah.addWidget(self.btn_prev)
        ly_nav_bawah.addStretch()
        ly_nav_bawah.addWidget(self.btn_next)
        ly_kiri.addLayout(ly_nav_bawah)
        
        w_kanan = QWidget()
        w_kanan.setFixedWidth(320)
        w_kanan.setStyleSheet("background-color: white; border-radius: 16px; border: 1px solid #E2E8F0;")
        terapkan_bayangan(w_kanan)
        ly_kanan = QVBoxLayout(w_kanan)
        ly_kanan.setContentsMargins(20, 20, 20, 20)
        
        lbl_nav = QLabel("📋 Peta Navigasi Soal")
        lbl_nav.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        lbl_nav.setStyleSheet("color: #0F172A; margin-bottom: 5px; border: none; background: transparent;")
        ly_kanan.addWidget(lbl_nav)
        
        self.grid_nav = QGridLayout()
        self.grid_nav.setSpacing(10)
        w_grid = QWidget()
        w_grid.setLayout(self.grid_nav)
        w_grid.setStyleSheet("background-color: transparent;")
        
        scroll_grid = QScrollArea()
        scroll_grid.setWidgetResizable(True)
        scroll_grid.setStyleSheet("border: none; background-color: transparent;")
        scroll_grid.setWidget(w_grid)
        ly_kanan.addWidget(scroll_grid)
        
        ly_kanan.addSpacing(10)
        self.btn_selesai = QPushButton("KUMPULKAN UJIAN ✔")
        self.btn_selesai.setStyleSheet("QPushButton { background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #EF4444, stop:1 #F43F5E); color: white; font-weight: bold; border-radius: 14px; padding: 14px; font-size: 11pt; border: none; } QPushButton:hover { background-color: #DC2626; } QPushButton:disabled { background-color: #FECACA; color: white; border: none; }")
        self.btn_selesai.clicked.connect(self.konfirmasi_selesai)
        ly_kanan.addWidget(self.btn_selesai)
        
        ly_kanan.addSpacing(5)
        self.btn_darurat = QPushButton("Keluar / Log Out (Darurat) 🚪")
        self.btn_darurat.setStyleSheet("QPushButton { background-color: white; color: #EF4444; font-weight: bold; border-radius: 14px; padding: 10px; font-size: 10pt; border: 2px solid #FECACA; } QPushButton:hover { background-color: #FEF2F2; border: 2px solid #EF4444; }")
        self.btn_darurat.clicked.connect(self.keluar_darurat)
        ly_kanan.addWidget(self.btn_darurat)
        
        ly_konten.addWidget(w_kiri)
        ly_konten.addWidget(w_kanan)
        ly_utama.addLayout(ly_konten)
        self.w_utama.addWidget(w)

    def render_soal_aktif(self):
        if not self.soal_list: return
        self.lbl_info_ujian.setText(f"🎓 {self.nama} ({self.kelas})   •   📚 Mapel: {self.mapel}")
        
        self.update_progres_bar_lokal()

        while self.ly_konten_soal.count():
            child = self.ly_konten_soal.takeAt(0)
            if child.widget(): child.widget().deleteLater()
            elif child.layout():
                while child.layout().count():
                    c2 = child.layout().takeAt(0)
                    if c2.widget(): c2.widget().deleteLater()
            
        soal = self.soal_list[self.indeks_soal]
        sid = str(soal['id'])
        tipe = soal['tipe']
        
        lbl_no = QLabel(f"SOAL NOMOR {self.indeks_soal + 1}")
        lbl_no.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        lbl_no.setStyleSheet("background-color: #EEF2FF; color: #6366F1; padding: 6px 12px; border-radius: 8px;")
        lbl_no.setFixedWidth(135)
        self.ly_konten_soal.addWidget(lbl_no)
        
        if soal.get('bacaan'):
            lbl_baca = QLabel(soal['bacaan'])
            lbl_baca.setWordWrap(True)
            lbl_baca.setStyleSheet("font-family: 'Times New Roman'; font-size: 13pt; background-color: #F8FAFC; padding: 15px; border-left: 4px solid #6366F1; border-radius: 8px; color: #1E293B;")
            self.ly_konten_soal.addWidget(lbl_baca)
            
        lbl_tanya = QLabel(soal['soal'])
        lbl_tanya.setWordWrap(True)
        lbl_tanya.setStyleSheet("font-family: 'Times New Roman'; font-size: 13pt; color: #0F172A; margin-top: 5px;")
        self.ly_konten_soal.addWidget(lbl_tanya)
        
        w_jawaban = QWidget()
        w_jawaban.setStyleSheet("""
            QRadioButton, QCheckBox { font-family: 'Times New Roman'; font-size: 13pt; padding: 14px 18px; border-radius: 12px; border: 2px solid #E2E8F0; background-color: #FFFFFF; color: #1E293B; margin-bottom: 8px; }
            QRadioButton:hover, QCheckBox:hover { border: 2px solid #6366F1; background-color: #F8FAFC; }
            QRadioButton:checked, QCheckBox:checked { background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #EEF2FF, stop:1 #FCE7F3); border: 2px solid #6366F1; color: #4F46E5; font-weight: bold; }
        """)
        ly_jwb = QVBoxLayout(w_jawaban)
        ly_jwb.setContentsMargins(0, 10, 0, 0)
        
        jwb_tersimpan = self.jawaban.get(sid)
        self.kontrol_input = [] 
        
        if tipe == 'PG':
            self.bg_pg = QButtonGroup(self)
            for k, v in soal.get('opsi', {}).items():
                rb = QRadioButton(f"{k}.   {v}")
                if jwb_tersimpan == k: rb.setChecked(True)
                rb.clicked.connect(lambda checked, kunci=k: self.simpan_jawaban(kunci))
                self.bg_pg.addButton(rb)
                ly_jwb.addWidget(rb)
                
        elif tipe == 'PGK':
            lbl_hint = QLabel("<i>✨ Pilih semua jawaban yang menurut Anda benar</i>")
            lbl_hint.setStyleSheet("color: #64748B; font-size: 11pt; margin-bottom: 5px;")
            ly_jwb.addWidget(lbl_hint)
            jwb_list = jwb_tersimpan if isinstance(jwb_tersimpan, list) else []
            for i, p in enumerate(soal.get('pernyataan', [])):
                chk = QCheckBox(p)
                if i in jwb_list: chk.setChecked(True)
                chk.stateChanged.connect(self.simpan_jawaban_list)
                self.kontrol_input.append(chk)
                ly_jwb.addWidget(chk)
                
        elif tipe == 'BS':
            lbl_hint = QLabel("<i>✨ Klik pilihan Benar (B) atau Salah (S) dengan jelas pada tiap baris di bawah ini</i>")
            lbl_hint.setStyleSheet("color: #64748B; font-size: 11pt; margin-bottom: 5px;")
            ly_jwb.addWidget(lbl_hint)
            jwb_list = jwb_tersimpan if isinstance(jwb_tersimpan, list) else []
            for i, p in enumerate(soal.get('pernyataan', [])):
                w_baris = QWidget()
                w_baris.setStyleSheet("background-color: #F8FAFC; border-radius: 12px; border: 1px solid #E2E8F0; margin-bottom: 8px;")
                ly_baris = QHBoxLayout(w_baris)
                ly_baris.setContentsMargins(15, 10, 15, 10)
                
                lbl_p = QLabel(p)
                lbl_p.setWordWrap(True)
                lbl_p.setStyleSheet("font-family: 'Times New Roman'; font-size: 13pt; background: transparent; color: #1E293B;")
                ly_baris.addWidget(lbl_p, stretch=1)
                
                bg = QButtonGroup(self)
                rb_b = QRadioButton("Benar ✔")
                rb_s = QRadioButton("Salah ❌")
                
                rb_b.setStyleSheet("QRadioButton { background-color: white; font-family: 'Segoe UI'; font-size: 10pt; font-weight: bold; color: #047857; padding: 10px 16px; border-radius: 8px; border: 2px solid #A7F3D0; } QRadioButton:hover { background-color: #ECFDF5; border: 2px solid #10B981; } QRadioButton:checked { background-color: #10B981; color: white; border: 2px solid #047857; }")
                rb_s.setStyleSheet("QRadioButton { background-color: white; font-family: 'Segoe UI'; font-size: 10pt; font-weight: bold; color: #B91C1C; padding: 10px 16px; border-radius: 8px; border: 2px solid #FECACA; } QRadioButton:hover { background-color: #FEF2F2; border: 2px solid #EF4444; } QRadioButton:checked { background-color: #EF4444; color: white; border: 2px solid #B91C1C; }")
                
                bg.addButton(rb_b)
                bg.addButton(rb_s)
                
                if i < len(jwb_list):
                    if jwb_list[i] == "B": rb_b.setChecked(True)
                    elif jwb_list[i] == "S": rb_s.setChecked(True)
                
                rb_b.clicked.connect(self.simpan_jawaban_list)
                rb_s.clicked.connect(self.simpan_jawaban_list)
                ly_baris.addWidget(rb_b)
                ly_baris.addWidget(rb_s)
                
                self.kontrol_input.append(bg)
                ly_jwb.addWidget(w_baris)
                
        elif tipe == 'ESSAY':
            self.txt_essay = QTextEdit()
            self.txt_essay.setStyleSheet("QTextEdit { font-family: 'Times New Roman'; font-size: 13pt; padding: 15px; border: 2px solid #E2E8F0; border-radius: 14px; background-color: #F8FAFC; color: #0F172A; } QTextEdit:focus { border: 2px solid #6366F1; background-color: white; }")
            if jwb_tersimpan: self.txt_essay.setText(jwb_tersimpan)
            self.txt_essay.textChanged.connect(lambda: self.simpan_jawaban(self.txt_essay.toPlainText()))
            ly_jwb.addWidget(self.txt_essay)
            
        self.ly_konten_soal.addWidget(w_jawaban)
        self.ly_konten_soal.addStretch()
        
        self.btn_prev.setEnabled(self.indeks_soal > 0)
        self.btn_next.setEnabled(self.indeks_soal < len(self.soal_list) - 1)
        self.update_warna_navigasi()

    def update_ui_koneksi(self, terhubung):
        if terhubung:
            self.lbl_status_koneksi.setText("🟢 Terhubung ke Guru")
            self.lbl_status_koneksi.setStyleSheet("background-color: #10B981; color: white; padding: 6px 12px; border-radius: 8px;")
            if hasattr(self, 'btn_selesai'): self.btn_selesai.setEnabled(True)
        else:
            self.lbl_status_koneksi.setText("🔴 KONEKSI TERPUTUS! Cek WiFi")
            self.lbl_status_koneksi.setStyleSheet("background-color: #EF4444; color: white; padding: 6px 12px; border-radius: 8px;")
            if hasattr(self, 'btn_selesai'): self.btn_selesai.setEnabled(False)

    def keluar_darurat(self):
        self.is_dialog_open = True
        self.timer_anti_cheat.stop()
        
        # 1. CEK KONEKSI KE SERVER GURU TERLEBIH DAHULU
        if self.server_ip:
            url_cek = f"{self.server_ip}/api/cek_status_siswa"
            try:
                respons = requests.post(url_cek, json={"nis": self.nis, "token": getattr(self, 'token', 'LOGIN')}, timeout=2)
                if respons.status_code == 200:
                    QMessageBox.warning(self, "Akses Ditolak 🛑", 
                        "Anda masih terhubung dengan Server Ujian!\n\nUntuk keluar dari soal, silakan angkat tangan dan minta izin kepada Guru/Proktor untuk di-KICK.")
                    self.is_dialog_open = False
                    self.timer_anti_cheat.start(500)
                    return
            except requests.exceptions.RequestException:
                pass

        # 2. JIKA OFFLINE/PUTUS
        pwd, ok = QInputDialog.getText(self, "Mode Darurat 🚪", 
            "Koneksi ke Server Proktor terputus!\nMasukkan Password Proktor untuk keluar paksa:", 
            QLineEdit.EchoMode.Password)
            
        if ok and (pwd == "admin123" or pwd == self.proctor_pwd):
            QMessageBox.information(self, "Aman ✅", "Sesi diakhiri oleh Proktor. Jawaban sebelumnya sudah aman tersimpan.")
            self.is_dialog_open = False
            self.reset_ke_login()
        elif ok:
            QMessageBox.warning(self, "Gagal ❌", "Password Proktor salah!")
            self.is_dialog_open = False
            self.timer_anti_cheat.start(500)
        else:
            self.is_dialog_open = False
            self.timer_anti_cheat.start(500)

    def update_progres_bar_lokal(self):
        jml_terjawab = len([k for k in self.jawaban.keys() if self.jawaban[k]])
        total_soal = len(self.soal_list)
        persen = int((jml_terjawab / total_soal) * 100) if total_soal > 0 else 0
        self.progress_bar.setValue(persen)
        self.progress_bar.setFormat(f"Progres Terjawab: {jml_terjawab} dari {total_soal} Soal ({persen}%)")

    def simpan_jawaban(self, nilai):
        sid = str(self.soal_list[self.indeks_soal]['id'])
        self.jawaban[sid] = nilai
        self.update_warna_navigasi()
        self.update_progres_bar_lokal()

    def simpan_jawaban_list(self, *args):
        sid = str(self.soal_list[self.indeks_soal]['id'])
        tipe = self.soal_list[self.indeks_soal]['tipe']
        
        if tipe == 'PGK': jwb = [i for i, chk in enumerate(self.kontrol_input) if chk.isChecked()]
        elif tipe == 'BS': jwb = [bg.checkedButton().text()[0] if bg.checkedButton() else "" for bg in self.kontrol_input]
            
        self.jawaban[sid] = jwb
        self.update_warna_navigasi()
        self.update_progres_bar_lokal()

    def kirim_autosave(self):
        jml_terjawab = len([k for k in self.jawaban.keys() if self.jawaban[k]])
        payload = {"nis": self.nis, "token": getattr(self, 'token', ''), "jawaban": self.jawaban, "terjawab": jml_terjawab}
        threading.Thread(target=self.proses_kirim_autosave_bg, args=(payload,), daemon=True).start()

    def proses_kirim_autosave_bg(self, payload):
        if getattr(self, 'sedang_di_kick', False): return
        if not self.server_ip or not self.nis: return
        try:
            r = requests.post(f"{self.server_ip}/api/autosave", json=payload, timeout=3)
            self.sinyal_koneksi.emit(True)
            if r.json().get("action") == "reset":
                self.sinyal_kick.emit()
        except requests.exceptions.RequestException:
            self.sinyal_koneksi.emit(False)

    # ================= FUNGSI RESET / KICK UTAMA =================
    def reset_ke_login_dari_server(self):
        if getattr(self, 'sedang_di_kick', False): return
        self.sedang_di_kick = True
        
        try:
            self.timer_anti_cheat.stop()
            self.timer_beranda.stop()
            self.timer_autosave.stop()
        except: pass
        
        self.is_dialog_open = True 
        
        QMessageBox.warning(self, "Sesi Berakhir ⚠️", "Akun Anda telah dikeluarkan (Force Logout) oleh Proktor.\n\nTenang saja, jawaban yang sudah Anda isi tersimpan dengan AMAN.\nSilakan Login kembali.")
        
        self.is_dialog_open = False
        self.reset_ke_login()
        self.sedang_di_kick = False

    def pindah_soal(self, delta):
        if delta > 0:
            sid = str(self.soal_list[self.indeks_soal]['id'])
            sudah_jawab = False
            if sid in self.jawaban:
                j = self.jawaban[sid]
                soal = self.soal_list[self.indeks_soal]
                if soal['tipe'] == 'PG' and j: sudah_jawab = True
                elif soal['tipe'] == 'ESSAY' and j.strip(): sudah_jawab = True
                elif soal['tipe'] == 'PGK' and len(j) > 0: sudah_jawab = True
                elif soal['tipe'] == 'BS' and isinstance(j, list) and any(val in ["B", "S"] for val in j): sudah_jawab = True
            
            if sudah_jawab and sid not in self.soal_sudah_dipopup:
                self.soal_sudah_dipopup.add(sid)
                self.buka_popup_transisi()

        self.indeks_soal += delta
        self.render_soal_aktif()

    def buka_popup_transisi(self):
        self.is_dialog_open = True
        self.timer_anti_cheat.stop()
        
        dlg = PopupTransisiDialog(self)
        dlg.exec()
        
        self.is_dialog_open = False
        self.timer_anti_cheat.start(500)

    def buat_navigasi_soal(self):
        while self.grid_nav.count():
            item = self.grid_nav.takeAt(0)
            if item.widget(): item.widget().deleteLater()
            
        baris, kolom = 0, 0
        self.btn_nav_list = []
        for i in range(len(self.soal_list)):
            btn = QPushButton(str(i + 1))
            btn.setFixedSize(50, 50)
            btn.clicked.connect(lambda checked, idx=i: self.lompat_soal(idx))
            self.grid_nav.addWidget(btn, baris, kolom)
            self.btn_nav_list.append(btn)
            kolom += 1
            if kolom > 4: 
                kolom = 0
                baris += 1

    def update_warna_navigasi(self):
        for i, soal in enumerate(self.soal_list):
            sid = str(soal['id'])
            sudah_dijawab = False
            if sid in self.jawaban:
                j = self.jawaban[sid]
                if soal['tipe'] == 'PG' and j: sudah_dijawab = True
                elif soal['tipe'] == 'ESSAY' and j.strip(): sudah_dijawab = True
                elif soal['tipe'] == 'PGK' and len(j) > 0: sudah_dijawab = True
                elif soal['tipe'] == 'BS' and isinstance(j, list) and any(val in ["B", "S"] for val in j): sudah_dijawab = True
                        
            btn = self.btn_nav_list[i]
            if i == self.indeks_soal:
                btn.setStyleSheet("background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #6366F1, stop:1 #8B5CF6); color: white; font-weight: bold; border-radius: 12px; font-size: 11pt;")
            elif sudah_dijawab:
                btn.setStyleSheet("background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #10B981, stop:1 #06B6D4); color: white; font-weight: bold; border-radius: 12px; font-size: 11pt;")
            else:
                btn.setStyleSheet("background-color: #F1F5F9; color: #475569; font-weight: bold; border-radius: 12px; border: 1px solid #E2E8F0; font-size: 11pt;")

    def lompat_soal(self, idx):
        self.indeks_soal = idx
        self.render_soal_aktif()

    def konfirmasi_selesai(self):
        dijawab = len([k for k in self.jawaban.keys() if self.jawaban[k]])
        total = len(self.soal_list)
        
        self.is_dialog_open = True
        self.timer_anti_cheat.stop() 
        
        tanya = QMessageBox.question(self, "Kumpulkan Ujian 🏁", 
            f"✨ Kamu telah menjawab {dijawab} dari {total} soal.\n\nApakah kamu yakin ingin mengumpulkan ujian sekarang?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        
        self.is_dialog_open = False
        if tanya == QMessageBox.StandardButton.Yes: self.proses_submit()
        else: self.timer_anti_cheat.start(500)

    def proses_submit(self):
        payload = {"token": self.token, "nama": self.nama, "jawaban": self.jawaban}
        self.active_worker = NetworkWorker(f"{self.server_ip}/api/submit", payload)
        self.active_worker.finished.connect(self.setelah_submit)
        self.active_worker.failed.connect(lambda err: self.tampil_pesan("Gagal ⚠️", "Gagal menyimpan ke server."))
        self.active_worker.start()

    def setelah_submit(self, data):
        if data.get('status') == 'sukses':
            self.timer_autosave.stop()
            self.timer_anti_cheat.stop()
            self.w_utama.setCurrentIndex(3) 
        else:
            self.tampil_pesan("Error ❌", "Gagal menyimpan ke server.")

    # ================= 4. HALAMAN SELESAI =================
    def setup_selesai_ui(self):
        w = QWidget()
        ly = QVBoxLayout(w)
        ly.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        box = QWidget()
        box.setStyleSheet("""
            QWidget { background-color: white; border-radius: 28px; border: 1px solid #E2E8F0; }
            QLineEdit { border: 2px solid #E2E8F0; border-radius: 14px; padding: 12px; font-size: 11pt; background-color: #F8FAFC; color: #0F172A; }
            QLineEdit:focus { border: 2px solid #10B981; background-color: white; }
            QPushButton { background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #10B981, stop:1 #06B6D4); color: white; font-weight: bold; border-radius: 14px; padding: 14px; font-size: 11pt; border: none; }
            QPushButton:hover { background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #059669, stop:1 #0891B2); }
        """)
        box.setFixedSize(460, 430)
        terapkan_bayangan(box)
        
        ly_box = QVBoxLayout(box)
        ly_box.setContentsMargins(40, 40, 40, 40)
        ly_box.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        lbl_ikon = QLabel("🎉🏆✨")
        lbl_ikon.setFont(QFont("Segoe UI", 32))
        lbl_ikon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl_ikon.setStyleSheet("background: transparent; border: none;")
        ly_box.addWidget(lbl_ikon)
        
        lbl = QLabel("Hebat, Ujian Selesai! 🚀")
        lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl.setFont(QFont("Segoe UI", 18, QFont.Weight.Bold))
        lbl.setStyleSheet("color: #10B981; margin-bottom: 2px; border: none; background: transparent;")
        ly_box.addWidget(lbl)
        
        lbl_sub = QLabel("Jawabanmu berhasil dikirim dengan aman ke server.")
        lbl_sub.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl_sub.setStyleSheet("color: #64748B; margin-bottom: 20px; border: none; background: transparent;")
        ly_box.addWidget(lbl_sub)
        
        self.inp_proctor = QLineEdit()
        self.inp_proctor.setPlaceholderText("🔑 Password Proktor...")
        self.inp_proctor.setEchoMode(QLineEdit.EchoMode.Password)
        self.inp_proctor.setAlignment(Qt.AlignmentFlag.AlignCenter)
        ly_box.addWidget(self.inp_proctor)
        
        ly_box.addSpacing(10)
        btn_kembali = QPushButton("KEMBALI KE LOGIN 👈")
        btn_kembali.clicked.connect(self.kembali_ke_login_dari_selesai)
        ly_box.addWidget(btn_kembali)
        
        ly.addWidget(box)
        self.w_utama.addWidget(w)

    def kembali_ke_login_dari_selesai(self):
        pwd = self.inp_proctor.text().strip()
        if not pwd: return

        # CEK ONLINE (Prioritas Pertama)
        if self.server_ip:
            url_cek = f"{self.server_ip}/api/cek_password"
            try:
                respons = requests.post(url_cek, json={"password": pwd}, timeout=3)
                data = respons.json()
                if data.get("status") == "sukses":
                    self.reset_ke_login()
                else:
                    self.tampil_pesan("Gagal ❌", "Password Proktor salah!")
                return
            except requests.exceptions.RequestException:
                pass # Lanjut ke mode offline jika gagal

        # CEK OFFLINE (Prioritas Kedua)
        if pwd == "admin123" or pwd == getattr(self, 'proctor_pwd', 'admin123'):
            self.reset_ke_login()
        else:
            self.tampil_pesan("Gagal ❌", "Koneksi ke Server terputus! Password offline salah.")

    def reset_ke_login(self):
        self.hidupkan_explorer() # Menghidupkan Windows Explorer kembali
        try:
            self.timer_beranda.stop()
            self.timer_autosave.stop()
            self.timer_anti_cheat.stop()
        except: pass
        
        self.nis, self.nama, self.kelas, self.token, self.mapel = "", "", "", "", ""
        self.soal_list, self.jawaban = [], {}
        self.soal_sudah_dipopup = set()
        self.inp_nis.clear(); self.inp_pwd.clear(); self.inp_token.clear(); self.inp_proctor.clear()
        self.w_utama.setCurrentIndex(0)

    def keluar_dari_login(self):
        self.is_dialog_open = True
        
        pwd, ok = QInputDialog.getText(self, "Tutup Aplikasi", "Masukkan Password Proktor:", QLineEdit.EchoMode.Password)
        self.is_dialog_open = False
        
        if not ok or not pwd:
            return 
            
        ip = self.inp_ip.text().strip()
        
        # CEK ONLINE (Prioritas Pertama)
        if ip:
            url_cek = f"http://{ip}:5000/api/cek_password"
            try:
                respons = requests.post(url_cek, json={"password": pwd}, timeout=3)
                data = respons.json()
                if data.get("status") == "sukses":
                    self.boleh_tutup = True 
                    self.buka_blokir_keyboard()
                    QApplication.quit()
                else:
                    self.tampil_pesan("Gagal ❌", "Password Proktor salah!")
                return 
            except requests.exceptions.RequestException:
                pass 

        # CEK OFFLINE (Prioritas Kedua)
        if pwd == "admin123":
            self.boleh_tutup = True 
            self.buka_blokir_keyboard()
            QApplication.quit()
        else: 
            self.tampil_pesan("Gagal ❌", "Koneksi ke Server terputus! Password mode darurat salah.")

    def tampil_pesan(self, judul, teks):
        self.is_dialog_open = True
        self.timer_anti_cheat.stop()
        QMessageBox.information(self, judul, teks)
        if self.w_utama.currentIndex() == 2: self.timer_anti_cheat.start(500)
        self.is_dialog_open = False

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = SiswaApp()
    window.show()
    sys.exit(app.exec())