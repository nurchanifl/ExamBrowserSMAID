import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
import requests
import base64
import io
from PIL import Image, ImageTk

class SiswaApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Exam Browser CBT")
        
        # MODE EXAM BROWSER
        self.attributes('-fullscreen', True) 
        self.attributes('-topmost', True)    
        self.protocol("WM_DELETE_WINDOW", self.cegah_tutup) 
        
        self.soal_data = []
        self.current_idx = 0
        self.jawaban_siswa = {}
        self.ip_server = ""
        self.nama_siswa = ""
        self.token_ujian = ""
        self.mapel_info = ""
        self.img_ref = None 
        
        self.frame_login = tk.Frame(self)
        self.frame_ujian = tk.Frame(self)
        
        self.setup_login()

    def cegah_tutup(self):
        messagebox.showwarning("Peringatan", "Anda sedang dalam mode ujian!\nAplikasi terkunci.", parent=self)

    def setup_login(self):
        self.frame_login.pack(expand=True)
        tk.Label(self.frame_login, text="LOGIN UJIAN CBT", font=("Arial", 26, "bold"), fg="blue").pack(pady=20)
        
        tk.Label(self.frame_login, text="Nama Lengkap:").pack(pady=(10,0))
        self.ent_nama = tk.Entry(self.frame_login, width=35, font=("Arial", 16))
        self.ent_nama.pack(pady=5)
        
        tk.Label(self.frame_login, text="Token Ujian (Minta ke Proktor):").pack(pady=(10,0))
        self.ent_token = tk.Entry(self.frame_login, width=35, font=("Arial", 16), justify='center')
        self.ent_token.pack(pady=5)
        
        tk.Label(self.frame_login, text="IP Server Proktor:").pack(pady=(10,0))
        self.ent_ip = tk.Entry(self.frame_login, width=35, font=("Arial", 16))
        self.ent_ip.pack(pady=5)
        
        tk.Button(self.frame_login, text="Mulai Mengerjakan", font=("Arial", 14, "bold"), bg="green", fg="white", command=self.mulai_ujian, width=25, height=2).pack(pady=40)
        
        tk.Button(self.frame_login, text="Keluar Aplikasi (Proktor)", fg="red", command=self.keluar_paksa).pack(pady=10)

    def keluar_paksa(self):
        pwd = simpledialog.askstring("Keamanan", "Password Proktor:", show='*', parent=self)
        if pwd is not None:
            ip = self.ent_ip.get().strip()
            if not ip:
                return messagebox.showerror("Error", "Masukkan IP Server terlebih dahulu untuk verifikasi password!", parent=self)
            try:
                ip_server_temp = f"http://{ip}:5000"
                resp = requests.post(f"{ip_server_temp}/api/cek_password", json={"password": pwd}, timeout=3)
                res_data = resp.json()
                if res_data.get("status") == "sukses":
                    self.destroy()
                else:
                    messagebox.showerror("Akses Ditolak", "Password salah!", parent=self)
            except Exception as e:
                messagebox.showerror("Koneksi Gagal", f"Tidak dapat terhubung ke server.\nPastikan IP benar.\nDetail: {e}", parent=self)

    def mulai_ujian(self):
        self.nama_siswa = self.ent_nama.get().strip()
        self.token_ujian = self.ent_token.get().strip().upper()
        ip = self.ent_ip.get().strip()
        
        if not self.nama_siswa or not ip or not self.token_ujian:
            return messagebox.showerror("Error", "Semua data (Nama, Token, IP) wajib diisi!", parent=self)
            
        self.ip_server = f"http://{ip}:5000"
        
        try:
            resp = requests.post(f"{self.ip_server}/api/auth_soal", json={"token": self.token_ujian}, timeout=5)
            data_resp = resp.json()
            
            if data_resp['status'] == "error":
                return messagebox.showwarning("Gagal", data_resp['pesan'], parent=self)
                
            self.soal_data = data_resp['soal']
            self.mapel_info = f"{data_resp['mapel']} (Kelas {data_resp['kelas']})"
            
            self.frame_login.pack_forget()
            self.frame_ujian.pack(fill='both', expand=True, padx=40, pady=40)
            self.tampilkan_soal()
            
        except Exception as e:
            messagebox.showerror("Koneksi Gagal", f"Tidak bisa terhubung ke server.\nPastikan IP benar.\nDetail: {e}", parent=self)

    def tampilkan_soal(self):
        for widget in self.frame_ujian.winfo_children(): widget.destroy()
            
        soal = self.soal_data[self.current_idx]
        sid = str(soal['id'])
        
        header = tk.Frame(self.frame_ujian)
        header.pack(fill='x', pady=5)
        tk.Label(header, text=f"Peserta: {self.nama_siswa} | Mapel: {self.mapel_info}", font=("Arial", 14, "bold"), fg="blue").pack(side='left')
        tk.Label(header, text=f"Soal {self.current_idx + 1} / {len(self.soal_data)}", font=("Arial", 14, "bold")).pack(side='right')
        
        tk.Label(self.frame_ujian, text=soal['soal'], font=("Arial", 16), wraplength=1000, justify='left').pack(anchor='w', pady=15)
        
        if soal.get('gambar'):
            try:
                img_data = base64.b64decode(soal['gambar'])
                image = Image.open(io.BytesIO(img_data))
                self.img_ref = ImageTk.PhotoImage(image)
                tk.Label(self.frame_ujian, image=self.img_ref).pack(anchor='w', pady=5)
            except: pass
                
        frame_jwb = tk.Frame(self.frame_ujian)
        frame_jwb.pack(fill='both', expand=True, pady=10)
        self.input_vars = []
        
        if soal['tipe'] == 'PG':
            var_pg = tk.StringVar(value=self.jawaban_siswa.get(sid, ""))
            for opsi_key, opsi_teks in soal['opsi'].items():
                tk.Radiobutton(frame_jwb, text=f"{opsi_key}. {opsi_teks}", variable=var_pg, value=opsi_key, font=("Arial", 14)).pack(anchor='w', pady=3)
            self.input_vars = var_pg
            
        elif soal['tipe'] == 'PGK':
            tk.Label(frame_jwb, text="*Pilih lebih dari satu pernyataan yang benar", fg="gray", font=("Arial", 12)).pack(anchor='w', pady=5)
            jawaban_sblm = self.jawaban_siswa.get(sid, [])
            for i, p in enumerate(soal['pernyataan']):
                var = tk.StringVar(value=str(i) if i in jawaban_sblm else "")
                tk.Checkbutton(frame_jwb, text=p, variable=var, onvalue=str(i), offvalue="", font=("Arial", 14)).pack(anchor='w', pady=3)
                self.input_vars.append(var)
                
        elif soal['tipe'] == 'BS':
            jawaban_sblm = self.jawaban_siswa.get(sid, [""]*4)
            for i, p in enumerate(soal['pernyataan']):
                row_frame = tk.Frame(frame_jwb)
                row_frame.pack(fill='x', pady=5)
                tk.Label(row_frame, text=p, width=60, anchor='w', font=("Arial", 13)).pack(side='left')
                var = tk.StringVar(value=jawaban_sblm[i] if i < len(jawaban_sblm) else "")
                tk.Radiobutton(row_frame, text="Benar", variable=var, value="B", font=("Arial", 12)).pack(side='left', padx=15)
                tk.Radiobutton(row_frame, text="Salah", variable=var, value="S", font=("Arial", 12)).pack(side='left')
                self.input_vars.append(var)
                
        elif soal['tipe'] == 'ESSAY':
            self.txt_essay = tk.Text(frame_jwb, height=8, width=90, font=("Arial", 14))
            self.txt_essay.pack(anchor='w')
            self.txt_essay.insert("1.0", self.jawaban_siswa.get(sid, ""))

        footer = tk.Frame(self.frame_ujian)
        footer.pack(fill='x', pady=30)
        
        if self.current_idx > 0: tk.Button(footer, text="<< Sebelumnya", command=self.simpan_dan_mundur, font=("Arial", 14), width=15).pack(side='left')
        if self.current_idx < len(self.soal_data) - 1: tk.Button(footer, text="Selanjutnya >>", command=self.simpan_dan_maju, font=("Arial", 14), bg="lightblue", width=15).pack(side='right')
        else: tk.Button(footer, text="Selesai & Kirim", command=self.selesai, font=("Arial", 14, "bold"), bg="red", fg="white", width=20).pack(side='right')

    def catat_jawaban_saat_ini(self):
        soal = self.soal_data[self.current_idx]
        sid = str(soal['id'])
        if soal['tipe'] == 'PG':
            if self.input_vars.get(): self.jawaban_siswa[sid] = self.input_vars.get()
        elif soal['tipe'] == 'PGK': self.jawaban_siswa[sid] = [int(v.get()) for v in self.input_vars if v.get() != ""]
        elif soal['tipe'] == 'BS': self.jawaban_siswa[sid] = [v.get() for v in self.input_vars]
        elif soal['tipe'] == 'ESSAY': self.jawaban_siswa[sid] = self.txt_essay.get("1.0", tk.END).strip()

    def simpan_dan_maju(self):
        self.catat_jawaban_saat_ini()
        self.current_idx += 1
        self.tampilkan_soal()

    def simpan_dan_mundur(self):
        self.catat_jawaban_saat_ini()
        self.current_idx -= 1
        self.tampilkan_soal()

    def selesai(self):
        self.catat_jawaban_saat_ini()
        if messagebox.askyesno("Konfirmasi", "Yakin ingin mengirim jawaban?", parent=self):
            try:
                requests.post(f"{self.ip_server}/api/submit", json={
                    "nama": self.nama_siswa,
                    "token": self.token_ujian,
                    "jawaban": self.jawaban_siswa
                })
                for widget in self.frame_ujian.winfo_children(): widget.destroy()
                self.attributes('-topmost', False)
                self.protocol("WM_DELETE_WINDOW", self.destroy)
                
                tk.Label(self.frame_ujian, text="Jawaban Tersimpan!", font=("Arial", 28, "bold"), fg="green").pack(pady=100)
                tk.Button(self.frame_ujian, text="Tutup Aplikasi", font=("Arial", 16, "bold"), bg="blue", fg="white", command=self.destroy, width=20, height=2).pack(pady=20)
            except Exception as e: messagebox.showerror("Error", f"Gagal mengirim data.\n{e}", parent=self)

if __name__ == "__main__":
    app = SiswaApp()
    app.mainloop()