import sys
import os
import requests
import base64
import keyboard
import ctypes
import threading
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                             QLabel, QLineEdit, QPushButton, QMessageBox, QStackedWidget,
                             QScrollArea, QRadioButton, QCheckBox, QButtonGroup, QGridLayout,
                             QTextEdit, QComboBox, QInputDialog)
from PyQt6.QtGui import QFont, QPixmap, QIcon
from PyQt6.QtCore import Qt, QTimer, QThread, pyqtSignal

# ================= FUNGSI PATH LOGO =================
def dapatkan_path_file(nama_file):
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, nama_file)

# ================= WORKER REGULER =================
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
    def __init__(self):
        super().__init__()
        self.setWindowTitle("ExamBrowser Siswa - SMA Islam Darussalam")
        
        # ================= SETUP LOGO & TASKBAR =================
        ikon_path = dapatkan_path_file("logo.jpg")
        if os.path.exists(ikon_path):
            self.setWindowIcon(QIcon(ikon_path))
            
        try:
            myappid = 'smaid.cbt.siswa.1.0'
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
        except:
            pass
        # ========================================================
        
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint | 
            Qt.WindowType.WindowStaysOnTopHint
        )
        self.showFullScreen()
        
        self.setStyleSheet("background-color: #f4f6f9; color: black; font-family: 'Segoe UI'; font-size: 11pt;")
        
        self.is_warning_active = False 
        self.boleh_tutup = False 
        self.blokir_keyboard() 
        
        self.server_ip = ""
        self.nis = ""
        self.nama = ""
        self.kelas = ""
        self.token = ""
        self.mapel = ""
        self.soal_list = []
        self.jawaban = {}
        self.indeks_soal = 0
        self.proctor_pwd = ""
        
        self.active_worker = None

        self.w_utama = QStackedWidget()
        self.setCentralWidget(self.w_utama)
        
        self.setup_login_ui()
        self.setup_token_ui()
        self.setup_ujian_ui()
        self.setup_selesai_ui()
        
        self.w_utama.setCurrentIndex(0)

        self.timer_anti_cheat = QTimer()
        self.timer_anti_cheat.timeout.connect(self.patroli_fokus)

    def changeEvent(self, event):
        if event.type() == event.Type.ActivationChange:
            if not self.isActiveWindow() and not self.is_warning_active and self.w_utama.currentIndex() == 2:
                self.hukum_siswa_curang()
        super().changeEvent(event)

    def patroli_fokus(self):
        if self.w_utama.currentIndex() == 2:
            if not self.isActiveWindow() and not self.is_warning_active:
                self.hukum_siswa_curang()
            
            self.setWindowState(self.windowState() & ~Qt.WindowState.WindowMinimized | Qt.WindowState.WindowActive)
            self.activateWindow()
            self.raise_()

    def hukum_siswa_curang(self):
        self.is_warning_active = True
        self.activateWindow()
        self.raise_()
        
        QMessageBox.critical(
            self, 
            "⛔ PELANGGARAN TERDETEKSI! ⛔", 
            "Anda terdeteksi berpindah aplikasi, membuka Virtual Desktop, atau menggunakan gesture Touchpad!\n\n"
            "Tindakan ini telah dicatat. Jika diulangi, Anda dapat didiskualifikasi dari ujian."
        )
        self.is_warning_active = False

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
        except:
            pass 

    def buka_blokir_keyboard(self):
        try:
            keyboard.unhook_all()
        except:
            pass

    def closeEvent(self, event):
        if getattr(self, 'boleh_tutup', False):
            event.accept()
        else:
            event.ignore()

    # ================= HALAMAN LOGIN =================
    def setup_login_ui(self):
        w = QWidget()
        ly = QVBoxLayout(w)
        ly.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        box = QWidget()
        box.setStyleSheet("background-color: white; border-radius: 10px; border: 1px solid #ccc;")
        box.setFixedSize(450, 480) 
        ly_box = QVBoxLayout(box)
        ly_box.setContentsMargins(30, 30, 30, 30)
        
        lbl_img = QLabel()
        lbl_img.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl_img.setMinimumHeight(80) 
        
        ikon_path = dapatkan_path_file("logo.jpg")
        if os.path.exists(ikon_path):
            pix = QPixmap(ikon_path)
            lbl_img.setPixmap(pix.scaled(85, 85, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
            ly_box.addWidget(lbl_img)
            
        lbl_judul = QLabel("🔐 LOGIN CBT SISWA\nSMA Islam Darussalam")
        lbl_judul.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl_judul.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
        lbl_judul.setStyleSheet("border: none; color: #1a252f;")
        ly_box.addWidget(lbl_judul)
        
        ly_box.addSpacing(15)
        
        self.inp_ip = QLineEdit()
        self.inp_ip.setPlaceholderText("IP Server Proktor (Misal: 192.168.1.10)")
        self.inp_ip.setStyleSheet("padding: 10px; border: 1px solid gray;")
        
        self.inp_nis = QLineEdit()
        self.inp_nis.setPlaceholderText("NIS / Username")
        self.inp_nis.setStyleSheet("padding: 10px; border: 1px solid gray;")
        
        self.inp_pwd = QLineEdit()
        self.inp_pwd.setPlaceholderText("Password Siswa")
        self.inp_pwd.setEchoMode(QLineEdit.EchoMode.Password)
        self.inp_pwd.setStyleSheet("padding: 10px; border: 1px solid gray;")
        
        ly_box.addWidget(self.inp_ip)
        ly_box.addWidget(self.inp_nis)
        ly_box.addWidget(self.inp_pwd)
        
        ly_box.addSpacing(15)
        
        btn_login = QPushButton("LOGIN")
        btn_login.setStyleSheet("background-color: #0d6efd; color: white; font-weight: bold; padding: 12px; border-radius: 5px;")
        btn_login.clicked.connect(self.proses_login)
        ly_box.addWidget(btn_login)
        
        btn_keluar = QPushButton("Keluar Aplikasi (Tutup Total)")
        btn_keluar.setStyleSheet("background-color: #dc3545; color: white; padding: 8px; border-radius: 5px;")
        btn_keluar.clicked.connect(self.keluar_dari_login)
        ly_box.addWidget(btn_keluar)
        
        ly.addWidget(box)
        self.w_utama.addWidget(w)

    def proses_login(self):
        ip = self.inp_ip.text().strip()
        nis = self.inp_nis.text().strip()
        pwd = self.inp_pwd.text().strip()
        
        if not ip or not nis or not pwd:
            return self.tampil_pesan("Error", "Semua kolom wajib diisi!")
            
        self.server_ip = f"http://{ip}:5000"
        
        self.active_worker = NetworkWorker(f"{self.server_ip}/api/login_siswa", {"nis": nis, "password": pwd})
        self.active_worker.finished.connect(self.setelah_login)
        self.active_worker.failed.connect(self.gagal_koneksi)
        self.active_worker.start()

    def setelah_login(self, data):
        if data.get('status') == 'sukses':
            self.nis = self.inp_nis.text().strip()
            self.nama = data['nama']
            self.kelas = data['kelas']
            self.w_utama.setCurrentIndex(1)
        else:
            self.tampil_pesan("Gagal Login", data.get('pesan', 'Kesalahan tidak diketahui'))

    def gagal_koneksi(self, err):
        self.tampil_pesan("Koneksi Gagal", "Tidak dapat terhubung ke Server Proktor. Periksa IP Server dan koneksi.")

    # ================= HALAMAN TOKEN =================
    def setup_token_ui(self):
        w = QWidget()
        ly = QVBoxLayout(w)
        ly.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        box = QWidget()
        box.setStyleSheet("background-color: white; border-radius: 10px; border: 1px solid #ccc;")
        box.setFixedSize(400, 320)
        ly_box = QVBoxLayout(box)
        ly_box.setContentsMargins(30, 30, 30, 30)
        
        lbl = QLabel("🔑 MASUKKAN TOKEN UJIAN")
        lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
        lbl.setStyleSheet("border: none;")
        ly_box.addWidget(lbl)
        
        self.inp_token = QLineEdit()
        self.inp_token.setPlaceholderText("Ketik token ujian dari Proktor...")
        self.inp_token.setStyleSheet("padding: 10px; border: 1px solid gray; font-size: 14pt; font-weight: bold;")
        self.inp_token.setAlignment(Qt.AlignmentFlag.AlignCenter)
        ly_box.addWidget(self.inp_token)
        
        btn_mulai = QPushButton("MULAI / RESUME UJIAN")
        btn_mulai.setStyleSheet("background-color: #28a745; color: white; font-weight: bold; padding: 12px; border-radius: 5px;")
        btn_mulai.clicked.connect(self.proses_token)
        ly_box.addWidget(btn_mulai)
        
        ly_box.addSpacing(10)
        
        btn_kembali = QPushButton("Keluar / Ganti Akun")
        btn_kembali.setStyleSheet("background-color: #6c757d; color: white; padding: 8px; border-radius: 5px;")
        btn_kembali.clicked.connect(self.reset_ke_login)
        ly_box.addWidget(btn_kembali)
        
        ly.addWidget(box)
        self.w_utama.addWidget(w)

    def proses_token(self):
        token = self.inp_token.text().strip().upper()
        if not token: return self.tampil_pesan("Error", "Token tidak boleh kosong!")
        
        self.active_worker = NetworkWorker(f"{self.server_ip}/api/auth_soal", {"token": token, "nis": self.nis})
        self.active_worker.finished.connect(lambda data: self.setelah_auth_soal(token, data))
        self.active_worker.failed.connect(self.gagal_koneksi)
        self.active_worker.start()

    def setelah_auth_soal(self, token, data):
        if data.get('status') == 'sukses':
            self.token = token
            self.mapel = data['mapel']
            self.proctor_pwd = data.get('proctor_pwd', 'admin123')
            self.soal_list = data['soal']
            self.jawaban = data.get('jawaban_tersimpan', {}) 
            self.indeks_soal = 0
            
            self.buat_navigasi_soal()
            self.render_soal_aktif()
            
            self.w_utama.setCurrentIndex(2)
            self.timer_anti_cheat.start(500) 
        else:
            self.tampil_pesan("Gagal", data.get('pesan', 'Token tidak valid'))

    # ================= HALAMAN UJIAN (UTAMA) =================
    def setup_ujian_ui(self):
        w = QWidget()
        ly_utama = QHBoxLayout(w)
        
        w_kiri = QWidget()
        ly_kiri = QVBoxLayout(w_kiri)
        
        self.lbl_info_ujian = QLabel()
        self.lbl_info_ujian.setStyleSheet("font-weight: bold; font-size: 12pt; padding: 10px; background-color: white; border: 1px solid #ccc;")
        ly_kiri.addWidget(self.lbl_info_ujian)
        
        self.scroll_soal = QScrollArea()
        self.scroll_soal.setWidgetResizable(True)
        self.scroll_soal.setStyleSheet("background-color: white; border: 1px solid #ccc;")
        
        self.w_konten_soal = QWidget()
        self.ly_konten_soal = QVBoxLayout(self.w_konten_soal)
        self.scroll_soal.setWidget(self.w_konten_soal)
        ly_kiri.addWidget(self.scroll_soal)
        
        ly_nav_bawah = QHBoxLayout()
        self.btn_prev = QPushButton("◀ SEBELUMNYA")
        self.btn_prev.setStyleSheet("background-color: #6c757d; color: white; padding: 10px; font-weight: bold;")
        self.btn_prev.clicked.connect(lambda: self.pindah_soal(-1))
        
        self.btn_next = QPushButton("SELANJUTNYA ▶")
        self.btn_next.setStyleSheet("background-color: #0d6efd; color: white; padding: 10px; font-weight: bold;")
        self.btn_next.clicked.connect(lambda: self.pindah_soal(1))
        
        ly_nav_bawah.addWidget(self.btn_prev)
        ly_nav_bawah.addStretch()
        ly_nav_bawah.addWidget(self.btn_next)
        ly_kiri.addLayout(ly_nav_bawah)
        
        w_kanan = QWidget()
        w_kanan.setFixedWidth(300)
        ly_kanan = QVBoxLayout(w_kanan)
        
        lbl_nav = QLabel("📋 NAVIGASI SOAL")
        lbl_nav.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl_nav.setStyleSheet("font-weight: bold; background-color: white; padding: 10px; border: 1px solid #ccc;")
        ly_kanan.addWidget(lbl_nav)
        
        self.grid_nav = QGridLayout()
        w_grid = QWidget()
        w_grid.setLayout(self.grid_nav)
        w_grid.setStyleSheet("background-color: white; border: 1px solid #ccc;")
        
        scroll_grid = QScrollArea()
        scroll_grid.setWidgetResizable(True)
        scroll_grid.setWidget(w_grid)
        ly_kanan.addWidget(scroll_grid)
        
        btn_selesai = QPushButton("KUMPULKAN UJIAN ✔")
        btn_selesai.setStyleSheet("background-color: #dc3545; color: white; font-weight: bold; padding: 15px;")
        btn_selesai.clicked.connect(self.konfirmasi_selesai)
        ly_kanan.addWidget(btn_selesai)
        
        ly_utama.addWidget(w_kiri)
        ly_utama.addWidget(w_kanan)
        self.w_utama.addWidget(w)

    def render_soal_aktif(self):
        if not self.soal_list: return
        self.lbl_info_ujian.setText(f"Peserta: {self.nama} ({self.kelas}) | Mapel: {self.mapel}")
        
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
        
        lbl_no = QLabel(f"<b>SOAL NOMOR {self.indeks_soal + 1}</b>")
        lbl_no.setStyleSheet("font-size: 14pt; color: #0d6efd;")
        self.ly_konten_soal.addWidget(lbl_no)
        
        if soal.get('bacaan'):
            lbl_baca = QLabel(soal['bacaan'])
            lbl_baca.setWordWrap(True)
            lbl_baca.setStyleSheet("background-color: #e9ecef; padding: 10px; border-left: 4px solid #0d6efd;")
            self.ly_konten_soal.addWidget(lbl_baca)
            
        if soal.get('gambar'):
            lbl_img = QLabel()
            pix = QPixmap()
            pix.loadFromData(base64.b64decode(soal['gambar']))
            lbl_img.setPixmap(pix.scaled(500, 500, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
            self.ly_konten_soal.addWidget(lbl_img)
            
        lbl_tanya = QLabel(soal['soal'])
        lbl_tanya.setWordWrap(True)
        lbl_tanya.setStyleSheet("font-size: 12pt; margin-top: 10px;")
        self.ly_konten_soal.addWidget(lbl_tanya)
        
        self.ly_konten_soal.addSpacing(15)
        
        jwb_tersimpan = self.jawaban.get(sid)
        self.kontrol_input = [] 
        
        if tipe == 'PG':
            self.bg_pg = QButtonGroup(self)
            for k, v in soal.get('opsi', {}).items():
                rb = QRadioButton(f"{k}. {v}")
                rb.setStyleSheet("font-size: 12pt; padding: 5px;")
                if jwb_tersimpan == k: rb.setChecked(True)
                rb.clicked.connect(lambda checked, kunci=k: self.simpan_jawaban(kunci))
                self.bg_pg.addButton(rb)
                self.ly_konten_soal.addWidget(rb)
                
        elif tipe == 'PGK':
            lbl_petunjuk = QLabel("<i>*Pilih semua pernyataan yang benar (Jawaban bisa lebih dari satu)</i>")
            lbl_petunjuk.setStyleSheet("color: gray;")
            self.ly_konten_soal.addWidget(lbl_petunjuk)
            jwb_list = jwb_tersimpan if isinstance(jwb_tersimpan, list) else []
            for i, p in enumerate(soal.get('pernyataan', [])):
                chk = QCheckBox(p)
                chk.setStyleSheet("font-size: 12pt; padding: 5px;")
                if i in jwb_list: chk.setChecked(True)
                chk.stateChanged.connect(self.simpan_jawaban_list)
                self.kontrol_input.append(chk)
                self.ly_konten_soal.addWidget(chk)
                
        elif tipe == 'BS':
            lbl_petunjuk = QLabel("<i>*Tentukan Benar (B) atau Salah (S) untuk setiap pernyataan</i>")
            lbl_petunjuk.setStyleSheet("color: gray;")
            self.ly_konten_soal.addWidget(lbl_petunjuk)
            
            jwb_list = jwb_tersimpan if isinstance(jwb_tersimpan, list) else []
            
            for i, p in enumerate(soal.get('pernyataan', [])):
                ly_baris = QHBoxLayout()
                lbl_p = QLabel(f"- {p}")
                lbl_p.setWordWrap(True)
                lbl_p.setStyleSheet("font-size: 11pt;")
                ly_baris.addWidget(lbl_p, stretch=1)
                
                bg = QButtonGroup(self)
                rb_b = QRadioButton("B")
                rb_s = QRadioButton("S")
                rb_b.setStyleSheet("padding-right: 15px;")
                
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
                self.ly_konten_soal.addLayout(ly_baris)
                
        elif tipe == 'ESSAY':
            self.txt_essay = QTextEdit()
            self.txt_essay.setStyleSheet("font-size: 12pt; padding: 10px; border: 1px solid gray;")
            if jwb_tersimpan: self.txt_essay.setText(jwb_tersimpan)
            self.txt_essay.textChanged.connect(lambda: self.simpan_jawaban(self.txt_essay.toPlainText()))
            self.ly_konten_soal.addWidget(self.txt_essay)
            
        self.ly_konten_soal.addStretch()
        self.btn_prev.setEnabled(self.indeks_soal > 0)
        self.btn_next.setEnabled(self.indeks_soal < len(self.soal_list) - 1)
        self.update_warna_navigasi()

    def simpan_jawaban(self, nilai):
        sid = str(self.soal_list[self.indeks_soal]['id'])
        self.jawaban[sid] = nilai
        self.update_warna_navigasi()
        self.kirim_autosave()

    def simpan_jawaban_list(self, *args):
        sid = str(self.soal_list[self.indeks_soal]['id'])
        tipe = self.soal_list[self.indeks_soal]['tipe']
        
        if tipe == 'PGK':
            jwb = [i for i, chk in enumerate(self.kontrol_input) if chk.isChecked()]
        elif tipe == 'BS':
            jwb = []
            for bg in self.kontrol_input:
                btn = bg.checkedButton()
                jwb.append(btn.text() if btn else "")
                
        self.jawaban[sid] = jwb
        self.update_warna_navigasi()
        self.kirim_autosave() 

    # Multithreading Murni (Agar tidak crash saat AutoSave sibuk)
    def kirim_autosave(self):
        payload = {
            "nis": self.nis,
            "token": self.token,
            "jawaban": self.jawaban
        }
        threading.Thread(target=self.proses_kirim_autosave_bg, args=(payload,), daemon=True).start()

    def proses_kirim_autosave_bg(self, payload):
        try:
            requests.post(f"{self.server_ip}/api/autosave", json=payload, timeout=3)
        except:
            pass

    def pindah_soal(self, delta):
        self.indeks_soal += delta
        self.render_soal_aktif()

    def buat_navigasi_soal(self):
        while self.grid_nav.count():
            item = self.grid_nav.takeAt(0)
            if item.widget(): item.widget().deleteLater()
            
        baris, kolom = 0, 0
        self.btn_nav_list = []
        for i in range(len(self.soal_list)):
            btn = QPushButton(str(i + 1))
            btn.setFixedSize(45, 45)
            btn.clicked.connect(lambda checked, idx=i: self.lompat_soal(idx))
            self.grid_nav.addWidget(btn, baris, kolom)
            self.btn_nav_list.append(btn)
            kolom += 1
            if kolom > 4:
                kolom = 0
                baris += 1

    def lompat_soal(self, idx):
        self.indeks_soal = idx
        self.render_soal_aktif()

    def update_warna_navigasi(self):
        for i, soal in enumerate(self.soal_list):
            sid = str(soal['id'])
            sudah_dijawab = False
            
            if sid in self.jawaban:
                j = self.jawaban[sid]
                if soal['tipe'] == 'PG' and j: sudah_dijawab = True
                elif soal['tipe'] == 'ESSAY' and j.strip(): sudah_dijawab = True
                elif soal['tipe'] == 'PGK' and len(j) > 0: sudah_dijawab = True
                elif soal['tipe'] == 'BS':
                    if isinstance(j, list) and any(val in ["B", "S"] for val in j):
                        sudah_dijawab = True
                        
            btn = self.btn_nav_list[i]
            if i == self.indeks_soal:
                btn.setStyleSheet("background-color: #ffc107; color: black; font-weight: bold; border: 2px solid black;")
            elif sudah_dijawab:
                btn.setStyleSheet("background-color: #28a745; color: white; font-weight: bold;")
            else:
                btn.setStyleSheet("background-color: white; color: black; border: 1px solid gray;")

    def konfirmasi_selesai(self):
        dijawab = len([k for k in self.jawaban.keys() if self.jawaban[k]])
        total = len(self.soal_list)
        
        self.is_warning_active = True
        tanya = QMessageBox.question(
            self, "Kumpulkan Ujian", 
            f"Anda telah menjawab {dijawab} dari {total} soal.\n\nApakah Anda yakin ingin mengumpulkan ujian sekarang?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        self.is_warning_active = False
        
        if tanya == QMessageBox.StandardButton.Yes:
            self.proses_submit()

    def proses_submit(self):
        payload = {"token": self.token, "nama": self.nama, "jawaban": self.jawaban}
        self.active_worker = NetworkWorker(f"{self.server_ip}/api/submit", payload)
        self.active_worker.finished.connect(self.setelah_submit)
        self.active_worker.failed.connect(lambda err: self.tampil_pesan("Koneksi Gagal", "Gagal menyimpan ke server. Pastikan aplikasi guru sedang menyala, lalu coba kumpulkan lagi."))
        self.active_worker.start()

    def setelah_submit(self, data):
        if data.get('status') == 'sukses':
            self.timer_anti_cheat.stop() 
            self.w_utama.setCurrentIndex(3) 
        else:
            self.tampil_pesan("Error", "Gagal menyimpan ke server. Pesan server: " + data.get("pesan", ""))

    # ================= HALAMAN SELESAI & KELUAR =================
    def setup_selesai_ui(self):
        w = QWidget()
        ly = QVBoxLayout(w)
        ly.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        lbl = QLabel("✅ UJIAN SELESAI\nJawaban Anda berhasil dikirim ke server.")
        lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
        lbl.setStyleSheet("color: green;")
        ly.addWidget(lbl)
        
        ly.addSpacing(30)
        
        lbl_izin = QLabel("Panggil Proktor untuk memasukkan password agar dapat kembali ke halaman login.")
        lbl_izin.setAlignment(Qt.AlignmentFlag.AlignCenter)
        ly.addWidget(lbl_izin)
        
        self.inp_proctor = QLineEdit()
        self.inp_proctor.setPlaceholderText("Password Proktor...")
        self.inp_proctor.setEchoMode(QLineEdit.EchoMode.Password)
        self.inp_proctor.setStyleSheet("padding: 10px; border: 1px solid gray;")
        self.inp_proctor.setFixedWidth(300)
        
        ly_inp = QHBoxLayout()
        ly_inp.setAlignment(Qt.AlignmentFlag.AlignCenter)
        ly_inp.addWidget(self.inp_proctor)
        ly.addLayout(ly_inp)
        
        btn_kembali = QPushButton("KEMBALI KE MENU LOGIN")
        btn_kembali.setStyleSheet("background-color: #0d6efd; color: white; font-weight: bold; padding: 10px;")
        btn_kembali.setFixedWidth(300)
        btn_kembali.clicked.connect(self.kembali_ke_login_dari_selesai)
        
        ly_btn = QHBoxLayout()
        ly_btn.setAlignment(Qt.AlignmentFlag.AlignCenter)
        ly_btn.addWidget(btn_kembali)
        ly.addLayout(ly_btn)
        
        self.w_utama.addWidget(w)

    def kembali_ke_login_dari_selesai(self):
        pwd = self.inp_proctor.text().strip()
        if not pwd:
            return self.tampil_pesan("Info", "Masukkan password proktor terlebih dahulu.")

        ip = self.inp_ip.text().strip()
        url_target = self.server_ip if self.server_ip else (f"http://{ip}:5000" if ip else None)
        
        if url_target:
            self.active_worker = NetworkWorker(f"{url_target}/api/cek_password", {"password": pwd})
            self.active_worker.finished.connect(self.eksekusi_kembali_login)
            self.active_worker.failed.connect(lambda err: self.kembali_login_darurat(pwd))
            self.active_worker.start()
        else:
            self.kembali_login_darurat(pwd)

    def eksekusi_kembali_login(self, data):
        if data.get('status') == 'sukses':
            self.reset_ke_login()
        else:
            self.tampil_pesan("Gagal", "Password Proktor salah!")

    def kembali_login_darurat(self, pwd):
        if pwd == "admin123":
            self.reset_ke_login()
        else:
            self.tampil_pesan("Gagal", "Password salah atau server Offline.\nGunakan password: admin123")

    def reset_ke_login(self):
        self.nis = ""
        self.nama = ""
        self.kelas = ""
        self.token = ""
        self.mapel = ""
        self.soal_list = []
        self.jawaban = {}
        self.indeks_soal = 0
        
        self.inp_nis.clear()
        self.inp_pwd.clear()
        self.inp_token.clear()
        self.inp_proctor.clear()
        
        self.w_utama.setCurrentIndex(0)

    def keluar_dari_login(self):
        pwd, ok = QInputDialog.getText(self, "Tutup Aplikasi Total", "Masukkan Password Proktor\n(Gunakan 'admin123' jika offline/belum terhubung server):", QLineEdit.EchoMode.Password)
        if ok and pwd:
            self.proses_keluar_global(pwd)

    def proses_keluar_global(self, pwd):
        ip = self.inp_ip.text().strip()
        url_target = self.server_ip if self.server_ip else (f"http://{ip}:5000" if ip else None)
        
        if url_target:
            self.active_worker = NetworkWorker(f"{url_target}/api/cek_password", {"password": pwd})
            self.active_worker.finished.connect(self.eksekusi_keluar)
            self.active_worker.failed.connect(lambda err: self.keluar_darurat_lokal(pwd))
            self.active_worker.start()
        else:
            self.keluar_darurat_lokal(pwd)

    def eksekusi_keluar(self, data):
        if data.get('status') == 'sukses':
            self.boleh_tutup = True 
            self.buka_blokir_keyboard()
            QApplication.quit()
        else:
            self.tampil_pesan("Gagal", "Password Proktor salah!")

    def keluar_darurat_lokal(self, pwd):
        if pwd == "admin123":
            self.boleh_tutup = True 
            self.buka_blokir_keyboard()
            QApplication.quit()
        else:
            self.tampil_pesan("Gagal", "Password salah atau server tidak terjangkau (Offline).\n\nGunakan password darurat: admin123")

    def tampil_pesan(self, judul, teks):
        self.is_warning_active = True
        QMessageBox.information(self, judul, teks)
        self.is_warning_active = False


if __name__ == '__main__':
    app = QApplication(sys.argv)
    app.setStyle("Fusion") 
    window = SiswaApp()
    window.show()
    sys.exit(app.exec())