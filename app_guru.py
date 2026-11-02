import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import json
import base64
import threading
from flask import Flask, request, jsonify
from PIL import Image, ImageTk
import io
import os

app_flask = Flask(__name__)

# Variabel Global Database
PROCTOR_PASSWORD = "admin123"
DATA_UJIAN = {} 
HASIL_SISWA = {}
FILE_DB = "database_ujian_cbt.json" # File default saat pertama kali dibuka

def load_db():
    global PROCTOR_PASSWORD, DATA_UJIAN, FILE_DB
    if os.path.exists(FILE_DB):
        try:
            with open(FILE_DB, 'r') as f:
                data = json.load(f)
                PROCTOR_PASSWORD = data.get("proctor_password", "admin123")
                DATA_UJIAN = data.get("paket_ujian", {})
        except:
            PROCTOR_PASSWORD = "admin123"
            DATA_UJIAN = {}
    else:
        PROCTOR_PASSWORD = "admin123"
        DATA_UJIAN = {}

def save_db():
    global FILE_DB
    data = {
        "proctor_password": PROCTOR_PASSWORD,
        "paket_ujian": DATA_UJIAN
    }
    with open(FILE_DB, 'w') as f:
        json.dump(data, f, indent=4)

# --- FLASK SERVER ---
@app_flask.route('/api/cek_password', methods=['POST'])
def cek_password():
    pwd = request.json.get('password')
    if pwd == PROCTOR_PASSWORD:
        return jsonify({"status": "sukses"})
    else:
        return jsonify({"status": "error", "pesan": "Password salah!"})

@app_flask.route('/api/auth_soal', methods=['POST'])
def auth_soal():
    token = request.json.get('token')
    paket_terpilih = None
    for p_id, p_data in DATA_UJIAN.items():
        if p_data.get('token') == token:
            paket_terpilih = p_data
            break
            
    if not paket_terpilih:
        return jsonify({"status": "error", "pesan": "Token ujian tidak ditemukan!"})
    if not paket_terpilih.get('aktif', False):
        return jsonify({"status": "error", "pesan": "Ujian ini belum diaktifkan oleh Proktor!"})
    if len(paket_terpilih['soal']) == 0:
        return jsonify({"status": "error", "pesan": "Belum ada soal di dalam paket ini!"})
        
    soal_siswa = []
    for s in paket_terpilih['soal']:
        item = s.copy()
        item.pop('kunci', None) 
        soal_siswa.append(item)
        
    return jsonify({
        "status": "sukses", 
        "mapel": paket_terpilih['mapel'], 
        "kelas": paket_terpilih['kelas'], 
        "soal": soal_siswa
    })

@app_flask.route('/api/submit', methods=['POST'])
def submit_jawaban():
    data = request.json
    nama = data.get('nama')
    token = data.get('token')
    jawaban = data.get('jawaban')
    
    paket = None
    for p_id, p_data in DATA_UJIAN.items():
        if p_data.get('token') == token:
            paket = p_data
            break
            
    if not paket: return jsonify({"status": "error"})
    
    skor_total = 0.0
    for soal in paket['soal']:
        sid = str(soal['id'])
        if sid not in jawaban: continue
        
        jawab = jawaban[sid]
        bobot = float(soal.get('bobot', 10.0))
        
        if soal['tipe'] == 'PG' and jawab == soal['kunci']:
            skor_total += bobot
        elif soal['tipe'] == 'PGK' and isinstance(jawab, list) and sorted(jawab) == sorted(soal['kunci']):
            skor_total += bobot
        elif soal['tipe'] == 'BS' and isinstance(jawab, list) and jawab == soal['kunci']:
            skor_total += bobot
            
    kunci_hasil = f"{nama}_{token}"
    HASIL_SISWA[kunci_hasil] = {
        "nama": nama,
        "kelas": paket['kelas'],
        "mapel": paket['mapel'],
        "token": token,
        "skor": skor_total, 
        "detail": jawaban
    }
    
    if hasattr(app_flask, 'gui'):
        app_flask.gui.update_proktor_hasil()
    return jsonify({"status": "sukses"})

def run_server():
    app_flask.run(host='0.0.0.0', port=5000, debug=False, use_reloader=False)

# --- GUI APLIKASI GURU ---
class GuruApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Server Proktor CBT (Multi-Kelas & Token)")
        self.geometry("900x850")
        app_flask.gui = self
        
        load_db()
        self.b64_image = ""
        
        notebook = ttk.Notebook(self)
        notebook.pack(fill='both', expand=True, padx=10, pady=10)
        
        self.tab_soal = ttk.Frame(notebook)
        self.tab_proktor = ttk.Frame(notebook)
        
        notebook.add(self.tab_soal, text="📝 Manajemen & Buat Soal")
        notebook.add(self.tab_proktor, text="🖥️ Kontrol Ujian & Proktor")
        
        self.setup_tab_soal()
        self.setup_tab_proktor()
        
        threading.Thread(target=run_server, daemon=True).start()

    def get_list_paket(self):
        return [f"{k} | {v['mapel']} (Kls: {v['kelas']}) - Token: {v['token']}" for k, v in DATA_UJIAN.items()]

    def setup_tab_soal(self):
        # 1. PANEL MANAJEMEN FILE DATABASE
        frame_db = tk.LabelFrame(self.tab_soal, text="Manajemen File Database (.json)", padx=10, pady=5)
        frame_db.pack(fill='x', padx=10, pady=5)

        self.lbl_db_aktif = tk.Label(frame_db, text=f"File Aktif: {os.path.basename(FILE_DB)}", font=("Arial", 11, "bold"), fg="blue")
        self.lbl_db_aktif.pack(side='left', padx=5)

        tk.Button(frame_db, text="📂 Buka File Lain", command=self.buka_file_db).pack(side='right', padx=5)
        tk.Button(frame_db, text="➕ Buat File Baru", bg="yellow", command=self.buat_file_db).pack(side='right', padx=5)

        # 2. PANEL PILIH PAKET
        frame_paket = tk.LabelFrame(self.tab_soal, text="Pilih / Buat Paket Ujian di File Ini", padx=10, pady=10)
        frame_paket.pack(fill='x', padx=10, pady=5)
        
        self.paket_var = tk.StringVar()
        self.cb_paket = ttk.Combobox(frame_paket, textvariable=self.paket_var, values=self.get_list_paket(), state="readonly", width=50)
        self.cb_paket.pack(side='left', padx=5)
        
        tk.Button(frame_paket, text="+ Buat Paket Baru", bg="lightgreen", command=self.buat_paket_baru).pack(side='left', padx=5)

        # 3. PANEL INPUT SOAL
        frame_input = tk.LabelFrame(self.tab_soal, text="Input Soal Baru", padx=10, pady=10)
        frame_input.pack(fill='both', expand=True, padx=10, pady=5)

        tk.Label(frame_input, text="Tipe Soal:").grid(row=0, column=0, sticky='w', pady=5)
        self.tipe_var = tk.StringVar(value="PG")
        cb_tipe = ttk.Combobox(frame_input, textvariable=self.tipe_var, values=["PG", "PGK", "BS", "ESSAY"], state="readonly")
        cb_tipe.grid(row=0, column=1, sticky='w')
        cb_tipe.bind("<<ComboboxSelected>>", self.refresh_form)

        tk.Label(frame_input, text="Bobot Poin:").grid(row=1, column=0, sticky='w', pady=5)
        self.bobot_var = tk.DoubleVar(value=10.00)
        tk.Spinbox(frame_input, from_=0.00, to=100.00, increment=0.5, format="%.2f", textvariable=self.bobot_var, width=10).grid(row=1, column=1, sticky='w')

        tk.Label(frame_input, text="Pertanyaan:").grid(row=2, column=0, sticky='nw', pady=5)
        self.txt_soal = tk.Text(frame_input, height=4, width=65)
        self.txt_soal.grid(row=2, column=1, pady=5)

        tk.Button(frame_input, text="Unggah Gambar", command=self.upload_gambar).grid(row=3, column=1, sticky='w')
        self.lbl_img_status = tk.Label(frame_input, text="Tidak ada gambar", fg="gray")
        self.lbl_img_status.grid(row=3, column=1, sticky='e', padx=10)

        self.frame_dinamis = tk.Frame(frame_input)
        self.frame_dinamis.grid(row=4, column=0, columnspan=2, pady=10, sticky='w')
        
        tk.Button(frame_input, text="💾 Simpan Soal", bg="lightblue", font=("Arial", 10, "bold"), command=self.simpan_soal).grid(row=5, column=1, sticky='e', pady=10)
        self.refresh_form()

    # --- FUNGSI MANAJEMEN DATABASE ---
    def buka_file_db(self):
        global FILE_DB, HASIL_SISWA
        filepath = filedialog.askopenfilename(defaultextension=".json", filetypes=[("JSON Files", "*.json")])
        if filepath:
            FILE_DB = filepath
            self.lbl_db_aktif.config(text=f"File Aktif: {os.path.basename(FILE_DB)}")
            HASIL_SISWA.clear() # Kosongkan hasil siswa lama karena pindah file
            self.segarkan_semua_data()
            messagebox.showinfo("Sukses", f"Berhasil membuka database:\n{os.path.basename(FILE_DB)}")

    def buat_file_db(self):
        global FILE_DB, PROCTOR_PASSWORD, DATA_UJIAN, HASIL_SISWA
        filepath = filedialog.asksaveasfilename(defaultextension=".json", filetypes=[("JSON Files", "*.json")], initialfile="soal_baru.json")
        if filepath:
            FILE_DB = filepath
            # Reset isi memori untuk file baru
            PROCTOR_PASSWORD = "admin123"
            DATA_UJIAN = {}
            HASIL_SISWA.clear()
            save_db() # Langsung ciptakan file fisik kosongnya
            
            self.lbl_db_aktif.config(text=f"File Aktif: {os.path.basename(FILE_DB)}")
            self.segarkan_semua_data()
            messagebox.showinfo("Sukses", f"File database baru berhasil dibuat:\n{os.path.basename(FILE_DB)}\n\nSilakan 'Buat Paket Baru' untuk mulai memasukkan soal.")

    def segarkan_semua_data(self):
        load_db()
        self.cb_paket['values'] = self.get_list_paket()
        self.paket_var.set("") # Reset pilihan combobox
        self.update_proktor_paket()
        self.update_proktor_hasil()
        self.ent_pwd.delete(0, tk.END)
        self.ent_pwd.insert(0, PROCTOR_PASSWORD)

    # --- SISA FUNGSI BAWAAN ---
    def buat_paket_baru(self):
        win = tk.Toplevel(self)
        win.title("Buat Paket Ujian Baru")
        win.geometry("350x250")
        
        tk.Label(win, text="Mata Pelajaran:").pack(pady=2)
        ent_mapel = tk.Entry(win, width=30)
        ent_mapel.pack(pady=2)
        
        tk.Label(win, text="Kelas (Misal: 10 IPA 1 / 11 IPS):").pack(pady=2)
        ent_kelas = tk.Entry(win, width=30)
        ent_kelas.pack(pady=2)
        
        tk.Label(win, text="Token Ujian (Kombinasi Huruf/Angka):").pack(pady=2)
        ent_token = tk.Entry(win, width=30)
        ent_token.pack(pady=2)
        
        def simpan_paket():
            mapel = ent_mapel.get().strip()
            kelas = ent_kelas.get().strip()
            token = ent_token.get().strip().upper()
            
            if not mapel or not kelas or not token:
                return messagebox.showwarning("Error", "Semua kolom wajib diisi!", parent=win)
                
            for v in DATA_UJIAN.values():
                if v['token'] == token:
                    return messagebox.showwarning("Error", f"Token '{token}' sudah dipakai paket lain!", parent=win)
            
            p_id = f"paket_{len(DATA_UJIAN) + 1}"
            DATA_UJIAN[p_id] = {"mapel": mapel, "kelas": kelas, "token": token, "aktif": False, "soal": []}
            save_db()
            
            self.cb_paket['values'] = self.get_list_paket()
            self.paket_var.set(f"{p_id} | {mapel} (Kls: {kelas}) - Token: {token}")
            self.update_proktor_paket()
            messagebox.showinfo("Sukses", "Paket Ujian berhasil dibuat!", parent=win)
            win.destroy()
            
        tk.Button(win, text="Simpan Paket", bg="green", fg="white", command=simpan_paket).pack(pady=15)

    def upload_gambar(self):
        filepath = filedialog.askopenfilename(filetypes=[("Image Files", "*.png;*.jpg;*.jpeg")])
        if filepath:
            try:
                img = Image.open(filepath)
                img.thumbnail((500, 500))
                buffered = io.BytesIO()
                img.save(buffered, format="PNG")
                self.b64_image = base64.b64encode(buffered.getvalue()).decode('utf-8')
                self.lbl_img_status.config(text="Gambar siap!", fg="green")
            except Exception as e:
                messagebox.showerror("Error", str(e))

    def refresh_form(self, event=None):
        for widget in self.frame_dinamis.winfo_children(): widget.destroy()
        tipe = self.tipe_var.get()
        self.input_data = []
        
        if tipe == "PG":
            lbls = ['A', 'B', 'C', 'D', 'E']
            for i, l in enumerate(lbls):
                tk.Label(self.frame_dinamis, text=f"Opsi {l}:").grid(row=i, column=0, sticky='w')
                e = tk.Entry(self.frame_dinamis, width=50)
                e.grid(row=i, column=1, padx=5, pady=2)
                self.input_data.append(e)
            tk.Label(self.frame_dinamis, text="Kunci:").grid(row=5, column=0, pady=10)
            self.kunci_pg = tk.StringVar(value="A")
            ttk.Combobox(self.frame_dinamis, textvariable=self.kunci_pg, values=lbls, width=5, state="readonly").grid(row=5, column=1, sticky='w')
        elif tipe in ["PGK", "BS"]:
            tk.Label(self.frame_dinamis, text="4 Pernyataan:").grid(row=0, column=0, sticky='w')
            tk.Label(self.frame_dinamis, text="Kunci").grid(row=0, column=2, padx=10)
            self.kunci_vars = []
            for i in range(4):
                e = tk.Entry(self.frame_dinamis, width=45)
                e.grid(row=i+1, column=0, columnspan=2, pady=2)
                self.input_data.append(e)
                if tipe == "PGK":
                    var = tk.StringVar(value="")
                    tk.Checkbutton(self.frame_dinamis, text="Benar", variable=var, onvalue=str(i), offvalue="").grid(row=i+1, column=2)
                    self.kunci_vars.append(var)
                else:
                    var = tk.StringVar(value="B")
                    ttk.Combobox(self.frame_dinamis, textvariable=var, values=["B", "S"], width=3, state="readonly").grid(row=i+1, column=2)
                    self.kunci_vars.append(var)
        elif tipe == "ESSAY":
            tk.Label(self.frame_dinamis, text="Keterangan:\nSoal Essay tidak dinilai otomatis.", fg="blue", justify="left").grid(row=0, column=0, columnspan=2, sticky='w', pady=10)

    def simpan_soal(self):
        paket_str = self.paket_var.get()
        if not paket_str: return messagebox.showwarning("Peringatan", "Pilih atau Buat Paket Ujian terlebih dahulu!")
        p_id = paket_str.split(" | ")[0]
        tipe = self.tipe_var.get()
        soal_teks = self.txt_soal.get("1.0", tk.END).strip()
        if not soal_teks: return messagebox.showwarning("Peringatan", "Soal tidak boleh kosong")
        
        try: nilai_bobot = float(self.bobot_var.get())
        except ValueError: return messagebox.showwarning("Peringatan", "Bobot harus angka")
            
        data_soal = {
            "id": len(DATA_UJIAN[p_id]['soal']) + 1, 
            "tipe": tipe, 
            "bobot": nilai_bobot,
            "soal": soal_teks, 
            "gambar": self.b64_image
        }
        
        if tipe == "PG":
            data_soal["opsi"] = {chr(65+i): e.get() for i, e in enumerate(self.input_data)}
            data_soal["kunci"] = self.kunci_pg.get()
        elif tipe in ["PGK", "BS"]:
            data_soal["pernyataan"] = [e.get() for e in self.input_data]
            if tipe == "PGK": data_soal["kunci"] = [int(v.get()) for v in self.kunci_vars if v.get() != ""]
            else: data_soal["kunci"] = [v.get() for v in self.kunci_vars]
        elif tipe == "ESSAY":
            data_soal["kunci"] = ""

        DATA_UJIAN[p_id]['soal'].append(data_soal)
        save_db()
        self.update_proktor_paket()
        
        self.txt_soal.delete("1.0", tk.END)
        self.b64_image = ""
        self.lbl_img_status.config(text="Tidak ada gambar", fg="gray")
        self.refresh_form()
        messagebox.showinfo("Sukses", f"Soal berhasil ditambahkan ke paket {DATA_UJIAN[p_id]['mapel']}!")

    def setup_tab_proktor(self):
        import socket
        ip_address = socket.gethostbyname(socket.gethostname())
        tk.Label(self.tab_proktor, text=f"🌐 IP Server Proktor: {ip_address}", font=("Arial", 12, "bold"), fg="blue").pack(pady=5)
        
        frame_pwd = tk.LabelFrame(self.tab_proktor, text="Pengaturan Password Keluar Aplikasi Siswa", padx=10, pady=8)
        frame_pwd.pack(fill='x', padx=20, pady=5)
        tk.Label(frame_pwd, text="Password Proktor Baru:").pack(side='left', padx=5)
        self.ent_pwd = tk.Entry(frame_pwd, width=25, show="*")
        self.ent_pwd.insert(0, PROCTOR_PASSWORD)
        self.ent_pwd.pack(side='left', padx=5)
        tk.Button(frame_pwd, text="Simpan Password", bg="lightblue", command=self.simpan_password_proktor).pack(side='left', padx=5)

        tk.Label(self.tab_proktor, text="Kontrol Paket Ujian (Mapel & Token)", font=("Arial", 11, "bold")).pack(anchor='w', padx=20, pady=(10,0))
        cols_paket = ("ID", "Mapel", "Kelas", "Token", "Soal", "Status")
        self.tree_paket = ttk.Treeview(self.tab_proktor, columns=cols_paket, show="headings", height=4)
        for c in cols_paket: self.tree_paket.heading(c, text=c)
        self.tree_paket.column("ID", width=50); self.tree_paket.column("Soal", width=50); self.tree_paket.column("Status", width=100)
        self.tree_paket.pack(fill='x', padx=20, pady=5)
        
        frame_btn = tk.Frame(self.tab_proktor)
        frame_btn.pack(fill='x', padx=20)
        tk.Button(frame_btn, text="🟢 Aktifkan Ujian", bg="lightgreen", command=lambda: self.toggle_ujian(True)).pack(side='left', padx=5)
        tk.Button(frame_btn, text="🔴 Nonaktifkan Ujian", bg="pink", command=lambda: self.toggle_ujian(False)).pack(side='left', padx=5)
        
        tk.Label(self.tab_proktor, text="Live Monitor Hasil Siswa (Klik Ganda untuk koreksi Essay)", font=("Arial", 11, "bold")).pack(anchor='w', padx=20, pady=(10,0))
        cols_hasil = ("Nama", "Kelas", "Mapel", "Skor")
        self.tree_hasil = ttk.Treeview(self.tab_proktor, columns=cols_hasil, show="headings", height=8)
        for c in cols_hasil: self.tree_hasil.heading(c, text=c)
        self.tree_hasil.pack(fill='both', expand=True, padx=20, pady=5)
        self.tree_hasil.bind("<Double-1>", self.lihat_detail_siswa)
        
        self.update_proktor_paket()

    def simpan_password_proktor(self):
        global PROCTOR_PASSWORD
        pwd_baru = self.ent_pwd.get().strip()
        if not pwd_baru: return messagebox.showwarning("Error", "Password tidak boleh kosong!")
        PROCTOR_PASSWORD = pwd_baru
        save_db()
        messagebox.showinfo("Sukses", "Password proktor berhasil diperbarui!")

    def toggle_ujian(self, aktifkan):
        selected = self.tree_paket.selection()
        if not selected: return
        p_id = self.tree_paket.item(selected[0])['values'][0]
        DATA_UJIAN[p_id]['aktif'] = aktifkan
        save_db()
        self.update_proktor_paket()
        status = "Diaktifkan" if aktifkan else "Dinonaktifkan"
        messagebox.showinfo("Update", f"Ujian {DATA_UJIAN[p_id]['mapel']} telah {status}!")

    def update_proktor_paket(self):
        for item in self.tree_paket.get_children(): self.tree_paket.delete(item)
        for p_id, v in DATA_UJIAN.items():
            status = "🟢 AKTIF" if v.get('aktif') else "🔴 Tutup"
            self.tree_paket.insert("", tk.END, values=(p_id, v['mapel'], v['kelas'], v['token'], len(v['soal']), status))

    def update_proktor_hasil(self):
        for item in self.tree_hasil.get_children(): self.tree_hasil.delete(item)
        for key, data in HASIL_SISWA.items():
            self.tree_hasil.insert("", tk.END, values=(data['nama'], data['kelas'], data['mapel'], f"{data['skor']:.2f}"))

    def lihat_detail_siswa(self, event):
        selected = self.tree_hasil.selection()
        if not selected: return
        item_vals = self.tree_hasil.item(selected[0])['values']
        nama, kelas, mapel = item_vals[0], str(item_vals[1]), item_vals[2]
        
        data_siswa = None
        for data in HASIL_SISWA.values():
            if data['nama'] == nama and str(data['kelas']) == kelas and data['mapel'] == mapel:
                data_siswa = data; break
        if not data_siswa: return
        
        paket_soal = None
        for v in DATA_UJIAN.values():
            if v['token'] == data_siswa['token']: paket_soal = v; break
        
        win = tk.Toplevel(self)
        win.title(f"Koreksi Essay - {nama}")
        win.geometry("600x500")
        tk.Label(win, text=f"{nama} | {mapel} | Skor PG: {data_siswa['skor']:.2f}", font=("Arial", 14, "bold"), fg="blue").pack(pady=10)
        
        txt = tk.Text(win, wrap="word", font=("Arial", 11))
        txt.pack(fill="both", expand=True, padx=15, pady=10)
        
        ada_essay = False
        if paket_soal:
            for soal in paket_soal['soal']:
                if soal['tipe'] == 'ESSAY':
                    ada_essay = True
                    sid = str(soal['id'])
                    jwb = data_siswa['detail'].get(sid, "[Kosong]")
                    txt.insert(tk.END, f"Soal (Maks {soal.get('bobot', 10.0):.2f}): {soal['soal']}\nJawaban: {jwb}\n\n")
                    txt.insert(tk.END, "-"*50 + "\n\n")
        
        if not ada_essay: txt.insert(tk.END, "Ujian ini tidak memiliki soal essay.")
        txt.config(state="disabled")

if __name__ == "__main__":
    app = GuruApp()
    app.mainloop()