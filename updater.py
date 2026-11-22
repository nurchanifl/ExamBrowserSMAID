import os
import sys
import shutil
import zipfile
import tempfile
import subprocess
import requests
from PyQt6.QtWidgets import QApplication, QWidget, QVBoxLayout, QLabel, QProgressBar
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont

# GANTI DENGAN LINK RAW GITHUB MILIKMU
URL_VERSI_GIT = "https://raw.githubusercontent.com/nurchanifl/ExamBrowserSMAID/main/versi.json"


class JendelaLoadingUpdate(QWidget):
    """Kotak kecil pemberitahuan agar pengguna tahu aplikasi sedang mengunduh update."""
    def __init__(self, versi_baru):
        super().__init__()
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint)
        self.setFixedSize(360, 130)
        self.setStyleSheet("background-color: #ffffff; border: 2px solid #4F46E5; border-radius: 12px;")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)

        lbl_judul = QLabel(f"Memperbarui ke Versi {versi_baru}...")
        lbl_judul.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        lbl_judul.setStyleSheet("color: #1E293B; border: none;")
        lbl_judul.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        self.progress.setValue(0)
        self.progress.setTextVisible(True)
        self.progress.setStyleSheet("""
            QProgressBar { border: 1px solid #CBD5E1; border-radius: 6px; text-align: center; height: 22px; }
            QProgressBar::chunk { background-color: #4F46E5; border-radius: 5px; }
        """)

        lbl_info = QLabel("Mohon tunggu, aplikasi akan terbuka otomatis.")
        lbl_info.setFont(QFont("Segoe UI", 9))
        lbl_info.setStyleSheet("color: #64748B; border: none;")
        lbl_info.setAlignment(Qt.AlignmentFlag.AlignCenter)

        layout.addWidget(lbl_judul)
        layout.addWidget(self.progress)
        layout.addWidget(lbl_info)


def cek_dan_update_otomatis(peran, versi_lokal):
    """
    peran       : isi "siswa" atau "guru"
    versi_lokal : angka versi aplikasi saat ini, misal "1.0.0"
    """
    # 1. Pastikan hanya jalan jika sudah berbentuk .exe (tidak jalan saat testing di VS Code)
    if not getattr(sys, 'frozen', False):
        return

    try:
        # 2. Tanya ke GitHub apakah ada versi baru (batas tunggu 4 detik)
        respon = requests.get(URL_VERSI_GIT, timeout=4)
        if respon.status_code != 200:
            return

        data_git = respon.json().get(peran, {})
        versi_git = data_git.get("versi", versi_lokal)
        link_zip = data_git.get("url_zip", "")

        # 3. Jika versi sama atau link kosong, langsung keluar dan lanjut buka aplikasi
        if versi_git == versi_lokal or not link_zip:
            return

        # 4. Tampilkan jendela loading & progress bar
        app_sementara = QApplication.instance() or QApplication(sys.argv)
        loading = JendelaLoadingUpdate(versi_git)
        loading.show()
        app_sementara.processEvents()

        # 5. Siapkan lokasi penyimpanan sementara di folder %TEMP% Windows
        folder_temp = tempfile.gettempdir()
        path_zip = os.path.join(folder_temp, f"update_{peran}.zip")
        folder_ekstrak = os.path.join(folder_temp, f"ekstrak_{peran}")

        # 6. Unduh file .zip sambil menggerakkan progress bar
        unduhan = requests.get(link_zip, stream=True, timeout=60)
        ukuran_total = int(unduhan.headers.get('content-length', 0))
        sudah_diunduh = 0

        with open(path_zip, "wb") as f:
            for potongan in unduhan.iter_content(chunk_size=8192):
                if potongan:
                    f.write(potongan)
                    sudah_diunduh += len(potongan)
                    if ukuran_total > 0:
                        persen = int((sudah_diunduh / ukuran_total) * 100)
                        loading.progress.setValue(persen)
                        app_sementara.processEvents()

        loading.close()

        # 7. Bongkar (ekstrak) isi .zip ke folder sementara
        if os.path.exists(folder_ekstrak):
            shutil.rmtree(folder_ekstrak)
        with zipfile.ZipFile(path_zip, 'r') as arsip:
            arsip.extractall(folder_ekstrak)

        # 8. Buat skrip .bat tersembunyi untuk menukar .exe + _internal lalu membuka ulang
        folder_aplikasi = os.path.dirname(sys.executable)
        nama_exe = os.path.basename(sys.executable)
        path_bat = os.path.join(folder_temp, f"jalankan_update_{peran}.bat")

        perintah_bat = f"""@echo off
timeout /t 2 /nobreak > nul
xcopy "{folder_ekstrak}\\*" "{folder_aplikasi}\\" /E /Y /I > nul
rmdir /s /q "{folder_ekstrak}"
del "{path_zip}"
start "" "{os.path.join(folder_aplikasi, nama_exe)}"
del "%~f0"
"""
        with open(path_bat, "w") as file_bat:
            file_bat.write(perintah_bat)

        # Jalankan skrip .bat tanpa memunculkan jendela hitam CMD, lalu matikan aplikasi lama
        subprocess.Popen(["cmd.exe", "/c", path_bat], creationflags=subprocess.CREATE_NO_WINDOW)
        sys.exit(0)

    except Exception:
        # Jika lab sedang offline / Wi-Fi lokal tanpa internet, abaikan dan lanjut ujian normal
        pass