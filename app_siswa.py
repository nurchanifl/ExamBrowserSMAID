import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
import requests
import base64
import io
import os
import sys
from PIL import Image, ImageTk

# --- FUNGSI BACA FILE INTERNAL EXE ---
def dapatkan_path_file(nama_file):
    """Membaca file dari dalam bungkus EXE atau dari folder lokal"""
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, nama_file)

# --- KONFIGURASI WARNA MODERN ---
BG_UTAMA = "#f4f7f6"
BG_KARTU = "#ffffff"
WARNA_PRIMER = "#0056b3"
WARNA_HEADER = "#1a252f"
WARNA_TEKS = "#333333"

class SiswaApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Exam Browser CBT")
        self.configure(bg=BG_UTAMA)
        
        self.attributes('-fullscreen', True) 
        self.attributes('-topmost', True)    
        self.protocol("WM_DELETE_WINDOW", self.cegah_tutup) 
        
        self.soal_data = []
        self.current_idx = 0
        self.jawaban_siswa = {}
        self.ip_server, self.nama_siswa, self.token_ujian, self.mapel_info = "", "", "", ""
        self.img_ref = None 
        
        self.frame_login = tk.Frame(self, bg=BG_UTAMA)
        self.frame_ujian = tk.Frame(self, bg=BG_UTAMA)
        self.setup_login()

    def cegah_tutup(self):
        messagebox.showwarning("Peringatan", "Anda sedang dalam mode ujian!\nAplikasi terkunci.", parent=self)

    def setup_login(self):
        self.frame_login.pack(expand=True)
        
        card = tk.Frame(self.frame_login, bg=BG_KARTU, padx=50, pady=40, relief="flat", bd=0)
        card.pack(pady=20)
        
        # --- KODE LOGO (Menggunakan logo.jpg) ---
        path_logo = dapatkan_path_file("logo.jpg")
        if os.path.exists(path_logo):
            try:
                img_logo = Image.open(path_logo)
                img_logo = img_logo.resize((120, 120))
                self.logo_img = ImageTk.PhotoImage(img_logo)
                tk.Label(card, image=self.logo_img, bg=BG_KARTU).pack(pady=(0, 15))
            except:
                pass
        # ----------------------------------------
        
        tk.Label(card, text="LOGIN UJIAN CBT", font=("Segoe UI", 28, "bold"), fg=WARNA_PRIMER, bg=BG_KARTU).pack(pady=(0, 30))
        
        def buat_input(label_teks):
            tk.Label(card, text=label_teks, font=("Segoe UI", 12, "bold"), fg="gray", bg=BG_KARTU).pack(anchor='w', pady=(10,2))
            ent = tk.Entry(card, width=35, font=("Segoe UI", 16), relief="solid", bd=1)
            ent.pack(pady=5, ipady=5)
            return ent
            
        self.ent_nama = buat_input("Nama Lengkap:")
        self.ent_token = buat_input("Token Ujian (Minta ke Proktor):")
        self.ent_token.config(justify='center', fg="blue")
        self.ent_ip = buat_input("IP Server Proktor:")
        
        tk.Button(card, text="MULAI MENGERJAKAN", font=("Segoe UI", 14, "bold"), bg="#28a745", fg="white", 
                  relief="flat", cursor="hand2", activebackground="#218838", activeforeground="white", 
                  command=self.mulai_ujian).pack(fill='x', pady=(30, 10), ipady=10)
        
        tk.Button(card, text="Keluar Aplikasi (Proktor)", font=("Segoe UI", 10, "underline"), fg="#dc3545", bg=BG_KARTU, 
                  relief="flat", cursor="hand2", activebackground=BG_KARTU, command=self.keluar_paksa).pack(pady=5)

    def keluar_paksa(self):
        pwd = simpledialog.askstring("Keamanan", "Password Proktor:", show='*', parent=self)
        if pwd is not None:
            ip = self.ent_ip.get().strip()
            if not ip: return messagebox.showerror("Error", "Masukkan IP Server terlebih dahulu!", parent=self)
            try:
                resp = requests.post(f"http://{ip}:5000/api/cek_password", json={"password": pwd}, timeout=3)
                if resp.json().get("status") == "sukses": self.destroy()
                else: messagebox.showerror("Akses Ditolak", "Password salah!", parent=self)
            except Exception as e: messagebox.showerror("Koneksi Gagal", f"Tidak terhubung ke server.\n{e}", parent=self)

    def mulai_ujian(self):
        self.nama_siswa = self.ent_nama.get().strip()
        self.token_ujian = self.ent_token.get().strip().upper()
        ip = self.ent_ip.get().strip()
        
        if not self.nama_siswa or not ip or not self.token_ujian:
            return messagebox.showerror("Error", "Semua data wajib diisi!", parent=self)
            
        self.ip_server = f"http://{ip}:5000"
        
        try:
            resp = requests.post(f"{self.ip_server}/api/auth_soal", json={"token": self.token_ujian}, timeout=5)
            data_resp = resp.json()
            if data_resp['status'] == "error": return messagebox.showwarning("Gagal", data_resp['pesan'], parent=self)
            
            self.soal_data = data_resp['soal']
            self.mapel_info = f"{data_resp['mapel']} (Kelas {data_resp['kelas']})"
            
            self.frame_login.pack_forget()
            self.frame_ujian.pack(fill='both', expand=True)
            self.tampilkan_soal()
        except Exception as e: messagebox.showerror("Koneksi Gagal", f"Pastikan IP benar.\n{e}", parent=self)

    def tampilkan_soal(self):
        for widget in self.frame_ujian.winfo_children(): widget.destroy()
        soal = self.soal_data[self.current_idx]
        sid = str(soal['id'])
        
        header = tk.Frame(self.frame_ujian, bg=WARNA_HEADER, padx=30, pady=15)
        header.pack(side='top', fill='x')
        tk.Label(header, text=f"👤 {self.nama_siswa}   |   📚 {self.mapel_info}", font=("Segoe UI", 14, "bold"), fg="white", bg=WARNA_HEADER).pack(side='left')
        tk.Label(header, text=f"Soal {self.current_idx + 1} / {len(self.soal_data)}", font=("Segoe UI", 16, "bold"), fg="#f1c40f", bg=WARNA_HEADER).pack(side='right')
        
        footer = tk.Frame(self.frame_ujian, bg=BG_UTAMA, padx=40, pady=20)
        footer.pack(side='bottom', fill='x')
        
        if self.current_idx > 0: 
            tk.Button(footer, text="⬅ Sebelumnya", command=self.simpan_dan_mundur, font=("Segoe UI", 13, "bold"), bg="#6c757d", fg="white", relief="flat", cursor="hand2", padx=20, pady=8).pack(side='left')
        
        if self.current_idx < len(self.soal_data) - 1: 
            tk.Button(footer, text="Selanjutnya ➡", command=self.simpan_dan_maju, font=("Segoe UI", 13, "bold"), bg=WARNA_PRIMER, fg="white", relief="flat", cursor="hand2", padx=20, pady=8).pack(side='right')
        else: 
            tk.Button(footer, text="Selesai & Kirim ✔", command=self.selesai, font=("Segoe UI", 14, "bold"), bg="#dc3545", fg="white", relief="flat", cursor="hand2", padx=20, pady=8).pack(side='right')

        container = tk.Frame(self.frame_ujian, bg=BG_UTAMA, padx=40, pady=10)
        container.pack(side='top', fill='both', expand=True)

        canvas = tk.Canvas(container, bg=BG_KARTU, highlightthickness=0)
        scrollbar = ttk.Scrollbar(container, orient="vertical", command=canvas.yview)
        scroll_frame = tk.Frame(canvas, bg=BG_KARTU, padx=30, pady=30)

        scroll_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas_win = canvas.create_window((0, 0), window=scroll_frame, anchor="nw")
        canvas.bind('<Configure>', lambda e: canvas.itemconfig(canvas_win, width=e.width))
        canvas.configure(yscrollcommand=scrollbar.set)
        
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        canvas.bind_all("<MouseWheel>", lambda e: canvas.yview_scroll(int(-1*(e.delta/120)), "units"))

        tk.Label(scroll_frame, text=soal['soal'], font=("Segoe UI", 16), fg=WARNA_TEKS, bg=BG_KARTU, wraplength=1000, justify='left').pack(anchor='w', pady=(0, 20))
        
        if soal.get('gambar'):
            try:
                img_data = base64.b64decode(soal['gambar'])
                image = Image.open(io.BytesIO(img_data))
                self.img_ref = ImageTk.PhotoImage(image) 
                tk.Label(scroll_frame, image=self.img_ref, bg=BG_KARTU).pack(anchor='w', pady=10)
            except: pass
                
        frame_jwb = tk.Frame(scroll_frame, bg=BG_KARTU)
        frame_jwb.pack(fill='both', expand=True)
        self.input_vars = []
        
        if soal['tipe'] == 'PG':
            var_pg = tk.StringVar(value=self.jawaban_siswa.get(sid, ""))
            for o_key, o_teks in soal['opsi'].items():
                tk.Radiobutton(frame_jwb, text=f"{o_key}. {o_teks}", variable=var_pg, value=o_key, font=("Segoe UI", 14), bg=BG_KARTU, activebackground=BG_KARTU, cursor="hand2").pack(anchor='w', pady=8)
            self.input_vars = var_pg
            
        elif soal['tipe'] == 'PGK':
            jawaban_sblm = self.jawaban_siswa.get(sid, [])
            for i, p in enumerate(soal['pernyataan']):
                var = tk.StringVar(value=str(i) if i in jawaban_sblm else "")
                tk.Checkbutton(frame_jwb, text=p, variable=var, onvalue=str(i), offvalue="", font=("Segoe UI", 14), bg=BG_KARTU, activebackground=BG_KARTU, cursor="hand2").pack(anchor='w', pady=6)
                self.input_vars.append(var)
                
        elif soal['tipe'] == 'BS':
            jawaban_sblm = self.jawaban_siswa.get(sid, [""]*4)
            for i, p in enumerate(soal['pernyataan']):
                row = tk.Frame(frame_jwb, bg=BG_KARTU)
                row.pack(fill='x', pady=6)
                tk.Label(row, text=p, width=65, anchor='w', font=("Segoe UI", 13), bg=BG_KARTU).pack(side='left')
                var = tk.StringVar(value=jawaban_sblm[i] if i < len(jawaban_sblm) else "")
                tk.Radiobutton(row, text="Benar", variable=var, value="B", font=("Segoe UI", 12), bg=BG_KARTU).pack(side='left', padx=15)
                tk.Radiobutton(row, text="Salah", variable=var, value="S", font=("Segoe UI", 12), bg=BG_KARTU).pack(side='left')
                self.input_vars.append(var)
                
        elif soal['tipe'] == 'ESSAY':
            self.txt_essay = tk.Text(frame_jwb, height=8, width=90, font=("Segoe UI", 14), relief="solid", bd=1)
            self.txt_essay.pack(anchor='w', pady=10)
            self.txt_essay.insert("1.0", self.jawaban_siswa.get(sid, ""))

    def catat_jawaban_saat_ini(self):
        soal, sid = self.soal_data[self.current_idx], str(self.soal_data[self.current_idx]['id'])
        if soal['tipe'] == 'PG': 
            if self.input_vars.get(): self.jawaban_siswa[sid] = self.input_vars.get()
        elif soal['tipe'] == 'PGK': self.jawaban_siswa[sid] = [int(v.get()) for v in self.input_vars if v.get() != ""]
        elif soal['tipe'] == 'BS': self.jawaban_siswa[sid] = [v.get() for v in self.input_vars]
        elif soal['tipe'] == 'ESSAY': self.jawaban_siswa[sid] = self.txt_essay.get("1.0", tk.END).strip()

    def simpan_dan_maju(self):
        self.catat_jawaban_saat_ini()
        self.current_idx += 1; self.tampilkan_soal()

    def simpan_dan_mundur(self):
        self.catat_jawaban_saat_ini()
        self.current_idx -= 1; self.tampilkan_soal()

    def selesai(self):
        self.catat_jawaban_saat_ini()
        if messagebox.askyesno("Konfirmasi", "Yakin ingin mengirim jawaban?", parent=self):
            try:
                requests.post(f"{self.ip_server}/api/submit", json={"nama": self.nama_siswa, "token": self.token_ujian, "jawaban": self.jawaban_siswa})
                for widget in self.frame_ujian.winfo_children(): widget.destroy()
                self.attributes('-topmost', False); self.protocol("WM_DELETE_WINDOW", self.destroy)
                self.frame_ujian.config(bg="#ffffff")
                tk.Label(self.frame_ujian, text="🎉\nJawaban Berhasil Terkirim!", font=("Segoe UI", 28, "bold"), fg="#28a745", bg="#ffffff").pack(pady=(150,30))
                tk.Button(self.frame_ujian, text="Tutup Aplikasi", font=("Segoe UI", 16, "bold"), bg=WARNA_PRIMER, fg="white", relief="flat", cursor="hand2", command=self.destroy, padx=30, pady=10).pack()
            except Exception as e: messagebox.showerror("Error", f"Gagal mengirim data.\n{e}", parent=self)

if __name__ == "__main__":
    app = SiswaApp()
    app.mainloop()