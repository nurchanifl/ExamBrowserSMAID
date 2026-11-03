import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import json
import base64
import threading
import io
import os
import csv
from flask import Flask, request, jsonify
from PIL import Image, ImageTk

app_flask = Flask(__name__)

# Variabel Global Database
PROCTOR_PASSWORD = "admin123"
DATA_UJIAN = {} 
HASIL_SISWA = {}
FILE_DB = "database_ujian_cbt.json"

def load_db():
    global PROCTOR_PASSWORD, DATA_UJIAN, FILE_DB
    if os.path.exists(FILE_DB):
        try:
            with open(FILE_DB, 'r') as f:
                d = json.load(f)
                PROCTOR_PASSWORD = d.get("proctor_password", "admin123")
                DATA_UJIAN = d.get("paket_ujian", {})
        except: 
            PROCTOR_PASSWORD = "admin123"
            DATA_UJIAN = {}
    else: 
        PROCTOR_PASSWORD = "admin123"
        DATA_UJIAN = {}

def save_db():
    with open(FILE_DB, 'w') as f: 
        json.dump({
            "proctor_password": PROCTOR_PASSWORD, 
            "paket_ujian": DATA_UJIAN
        }, f, indent=4)

# --- FLASK SERVER ---
@app_flask.route('/api/cek_password', methods=['POST'])
def cek_password(): 
    if request.json.get('password') == PROCTOR_PASSWORD:
        return jsonify({"status": "sukses"})
    return jsonify({"status": "error", "pesan": "Password salah!"})

@app_flask.route('/api/auth_soal', methods=['POST'])
def auth_soal():
    token = request.json.get('token')
    paket = next((p for p in DATA_UJIAN.values() if p.get('token') == token), None)
    
    if not paket: return jsonify({"status": "error", "pesan": "Token ujian tidak ditemukan!"})
    if not paket.get('aktif'): return jsonify({"status": "error", "pesan": "Ujian ini belum diaktifkan Proktor!"})
    if len(paket['soal']) == 0: return jsonify({"status": "error", "pesan": "Belum ada soal di dalam paket ini!"})
    
    return jsonify({
        "status": "sukses", 
        "mapel": paket['mapel'], 
        "kelas": paket['kelas'], 
        "soal": [{k:v for k,v in s.items() if k != 'kunci'} for s in paket['soal']]
    })

@app_flask.route('/api/submit', methods=['POST'])
def submit_jawaban():
    d = request.json
    token = d.get('token')
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
            
    HASIL_SISWA[f"{d['nama']}_{token}"] = {
        "nama": d['nama'], 
        "kelas": paket['kelas'], 
        "mapel": paket['mapel'], 
        "token": token, 
        "skor": skor, 
        "detail": d['jawaban']
    }
    
    if hasattr(app_flask, 'gui'): 
        app_flask.gui.update_proktor_hasil()
    return jsonify({"status": "sukses"})

def run_server(): 
    app_flask.run(host='0.0.0.0', port=5000, debug=False, use_reloader=False)

# --- GUI GURU MODERN ---
class GuruApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Server Proktor CBT Modern")
        self.geometry("950x900")
        self.configure(bg="#f4f6f9")
        app_flask.gui = self
        load_db()
        self.b64_image = ""
        
        # --- HEADER & LOGO ---
        header_frame = tk.Frame(self, bg="#ffffff", pady=10)
        header_frame.pack(fill='x', side='top')
        
        if os.path.exists("logo.jpg"):
            try:
                img_logo = Image.open("logo.jpg")
                img_logo = img_logo.resize((60, 60))
                self.logo_img = ImageTk.PhotoImage(img_logo)
                tk.Label(header_frame, image=self.logo_img, bg="#ffffff").pack(side='left', padx=(20, 10))
            except:
                pass
                
        tk.Label(header_frame, text="SERVER PROKTOR CBT - SMA ISLAM DARUSSALAM", font=("Segoe UI", 16, "bold"), fg="#1a252f", bg="#ffffff").pack(side='left')

        # --- AKTIFKAN TEMA MODERN ---
        style = ttk.Style(self)
        if 'clam' in style.theme_names():
            style.theme_use('clam')
            
        style.configure("TNotebook.Tab", font=("Segoe UI", 11, "bold"), padding=[15, 8])
        style.configure("Treeview.Heading", font=("Segoe UI", 10, "bold"), background="#e9ecef")
        style.configure("Treeview", font=("Segoe UI", 10), rowheight=28)
        style.configure("TLabelframe", background="#ffffff")
        style.configure("TLabelframe.Label", font=("Segoe UI", 10, "bold"), background="#ffffff", foreground="#333")
        
        notebook = ttk.Notebook(self)
        notebook.pack(fill='both', expand=True, padx=15, pady=15)
        
        self.tab_soal = tk.Frame(notebook, bg="#ffffff", padx=10, pady=10)
        self.tab_proktor = tk.Frame(notebook, bg="#ffffff", padx=10, pady=10)
        
        notebook.add(self.tab_soal, text="📝 Manajemen Soal")
        notebook.add(self.tab_proktor, text="🖥️ Kontrol Proktor & Hasil")
        
        self.setup_tab_soal()
        self.setup_tab_proktor()
        threading.Thread(target=run_server, daemon=True).start()

    def m_btn(self, parent, text, bg, fg, cmd):
        return tk.Button(parent, text=text, bg=bg, fg=fg, relief="flat", font=("Segoe UI", 10, "bold"), cursor="hand2", command=cmd, padx=10, pady=4)

    def get_list_paket(self): 
        return [f"{k} | {v['mapel']} (Kls: {v['kelas']}) - Token: {v['token']}" for k, v in DATA_UJIAN.items()]

    def setup_tab_soal(self):
        f_db = ttk.LabelFrame(self.tab_soal, text="📁 File Database (.json)")
        f_db.pack(fill='x', pady=5)
        self.lbl_db = tk.Label(f_db, text=f"File Aktif: {os.path.basename(FILE_DB)}", font=("Segoe UI", 11, "bold"), fg="#0d6efd", bg="white")
        self.lbl_db.pack(side='left', padx=15, pady=10)
        self.m_btn(f_db, "➕ Buat File Baru", "#17a2b8", "white", self.buat_file_db).pack(side='right', padx=10, pady=10)
        self.m_btn(f_db, "📂 Buka File Lain", "#6c757d", "white", self.buka_file_db).pack(side='right', padx=5, pady=10)

        f_pkt = ttk.LabelFrame(self.tab_soal, text="📦 Pilih / Buat Paket Ujian")
        f_pkt.pack(fill='x', pady=10)
        self.paket_var = tk.StringVar()
        self.cb_paket = ttk.Combobox(f_pkt, textvariable=self.paket_var, values=self.get_list_paket(), state="readonly", width=55, font=("Segoe UI", 11))
        self.cb_paket.pack(side='left', padx=15, pady=10)
        self.m_btn(f_pkt, "➕ Buat Paket Baru", "#28a745", "white", self.buat_paket).pack(side='left', padx=10)

        f_in = ttk.LabelFrame(self.tab_soal, text="✏️ Input Soal Baru")
        f_in.pack(fill='both', expand=True, pady=5)
        
        form = tk.Frame(f_in, bg="white", padx=10, pady=10)
        form.pack(fill='both', expand=True)

        tk.Label(form, text="Tipe Soal:", bg="white", font=("Segoe UI", 10)).grid(row=0, column=0, sticky='w', pady=5)
        self.tipe_var = tk.StringVar(value="PG")
        cb = ttk.Combobox(form, textvariable=self.tipe_var, values=["PG", "PGK", "BS", "ESSAY"], state="readonly", width=15)
        cb.grid(row=0, column=1, sticky='w')
        cb.bind("<<ComboboxSelected>>", self.ref_form)

        tk.Label(form, text="Bobot Poin:", bg="white", font=("Segoe UI", 10)).grid(row=1, column=0, sticky='w', pady=5)
        self.bobot_var = tk.DoubleVar(value=10.00)
        ttk.Spinbox(form, from_=0, to=100, increment=0.5, format="%.2f", textvariable=self.bobot_var, width=10).grid(row=1, column=1, sticky='w')

        tk.Label(form, text="Pertanyaan:", bg="white", font=("Segoe UI", 10)).grid(row=2, column=0, sticky='nw', pady=5)
        self.txt_soal = tk.Text(form, height=4, width=70, font=("Segoe UI", 11), relief="solid", bd=1)
        self.txt_soal.grid(row=2, column=1, pady=5)

        self.m_btn(form, "🖼️ Unggah Gambar", "#ffc107", "black", self.up_img).grid(row=3, column=1, sticky='w')
        self.lbl_img = tk.Label(form, text="Tidak ada gambar", fg="gray", bg="white", font=("Segoe UI", 9))
        self.lbl_img.grid(row=3, column=1, sticky='e', padx=10)

        self.f_dinamis = tk.Frame(form, bg="white")
        self.f_dinamis.grid(row=4, column=0, columnspan=2, pady=15, sticky='w')
        self.m_btn(form, "💾 SIMPAN SOAL", "#0d6efd", "white", self.simpan_soal).grid(row=5, column=1, sticky='e', pady=10)
        self.ref_form()

    # --- FUNGSI MANAJEMEN ---
    def buka_file_db(self):
        global FILE_DB
        fp = filedialog.askopenfilename(defaultextension=".json", filetypes=[("JSON", "*.json")])
        if fp:
            FILE_DB = fp
            HASIL_SISWA.clear()
            self.segarkan()
            self.lbl_db.config(text=f"File Aktif: {os.path.basename(FILE_DB)}")
            messagebox.showinfo("Sukses", f"Berhasil membuka database:\n{os.path.basename(FILE_DB)}")
            
    def buat_file_db(self):
        global FILE_DB, PROCTOR_PASSWORD, DATA_UJIAN
        fp = filedialog.asksaveasfilename(defaultextension=".json", filetypes=[("JSON", "*.json")], initialfile="soal_baru.json")
        if fp:
            FILE_DB = fp
            PROCTOR_PASSWORD = "admin123"
            DATA_UJIAN = {}
            HASIL_SISWA.clear()
            save_db()
            self.segarkan()
            self.lbl_db.config(text=f"File Aktif: {os.path.basename(FILE_DB)}")
            messagebox.showinfo("Sukses", "File database baru berhasil dibuat!")

    def segarkan(self):
        load_db()
        self.cb_paket['values'] = self.get_list_paket()
        self.paket_var.set("")
        self.upd_tree()
        self.update_proktor_hasil()
        self.ent_pwd.delete(0, tk.END)
        self.ent_pwd.insert(0, PROCTOR_PASSWORD)

    def buat_paket(self):
        w = tk.Toplevel(self)
        w.title("Paket Baru")
        w.geometry("350x250")
        w.configure(bg="white", padx=20, pady=20)
        
        tk.Label(w, text="Mapel:", bg="white").pack(anchor='w')
        e1 = ttk.Entry(w, width=35); e1.pack(pady=2)
        tk.Label(w, text="Kelas (Contoh: 10 IPA 1):", bg="white").pack(anchor='w', pady=(5,0))
        e2 = ttk.Entry(w, width=35); e2.pack(pady=2)
        tk.Label(w, text="Token Ujian:", bg="white").pack(anchor='w', pady=(5,0))
        e3 = ttk.Entry(w, width=35); e3.pack(pady=2)
        
        def simpan():
            if not e1.get() or not e2.get() or not e3.get(): 
                return messagebox.showwarning("Error", "Isi semua kolom!")
            p_id = f"paket_{len(DATA_UJIAN)+1}"
            DATA_UJIAN[p_id] = {
                "mapel": e1.get().strip(), 
                "kelas": e2.get().strip(), 
                "token": e3.get().strip().upper(), 
                "aktif": False, 
                "soal": []
            }
            save_db()
            self.cb_paket['values'] = self.get_list_paket()
            self.paket_var.set(f"{p_id} | {e1.get()} (Kls: {e2.get()}) - Token: {e3.get().upper()}")
            self.upd_tree()
            w.destroy()
            
        self.m_btn(w, "Simpan", "#28a745", "white", simpan).pack(pady=15)

    def up_img(self):
        fp = filedialog.askopenfilename(filetypes=[("Image", "*.png;*.jpg;*.jpeg")])
        if fp:
            img = Image.open(fp)
            img.thumbnail((500, 500))
            b = io.BytesIO()
            img.save(b, format="PNG")
            self.b64_image = base64.b64encode(b.getvalue()).decode('utf-8')
            self.lbl_img.config(text="Gambar siap!", fg="green")

    def ref_form(self, e=None):
        for w in self.f_dinamis.winfo_children(): w.destroy()
        t = self.tipe_var.get()
        self.i_data = []
        
        if t == "PG":
            for i, l in enumerate(['A','B','C','D','E']):
                tk.Label(self.f_dinamis, text=f"Opsi {l}:", bg="white").grid(row=i, column=0, sticky='w')
                en = ttk.Entry(self.f_dinamis, width=60)
                en.grid(row=i, column=1, padx=5, pady=3)
                self.i_data.append(en)
            tk.Label(self.f_dinamis, text="Kunci:", bg="white").grid(row=5, column=0, pady=10)
            self.k_pg = tk.StringVar(value="A")
            ttk.Combobox(self.f_dinamis, textvariable=self.k_pg, values=['A','B','C','D','E'], width=5, state="readonly").grid(row=5, column=1, sticky='w')
            
        elif t in ["PGK", "BS"]:
            self.k_v = []
            for i in range(4):
                en = ttk.Entry(self.f_dinamis, width=50)
                en.grid(row=i, column=0, pady=3)
                self.i_data.append(en)
                
                if t == "PGK":
                    v = tk.StringVar(value="")
                    tk.Checkbutton(self.f_dinamis, text="Benar", variable=v, onvalue=str(i), offvalue="", bg="white").grid(row=i, column=1, padx=10)
                else:
                    v = tk.StringVar(value="B")
                    ttk.Combobox(self.f_dinamis, textvariable=v, values=["B","S"], width=3, state="readonly").grid(row=i, column=1, padx=10)
                self.k_v.append(v)
                
        elif t == "ESSAY": 
            tk.Label(self.f_dinamis, text="(Soal Essay tidak dinilai otomatis)", fg="blue", bg="white").grid(row=0, column=0)

    def simpan_soal(self):
        if not self.paket_var.get(): 
            return messagebox.showwarning("Error", "Pilih atau buat paket ujian terlebih dahulu!")
            
        p_id = self.paket_var.get().split(" | ")[0]
        t = self.tipe_var.get()
        
        try: nilai_bobot = float(self.bobot_var.get())
        except ValueError: return messagebox.showwarning("Error", "Bobot harus angka!")
        
        ds = {
            "id": len(DATA_UJIAN[p_id]['soal'])+1, 
            "tipe": t, 
            "bobot": nilai_bobot, 
            "soal": self.txt_soal.get("1.0", tk.END).strip(), 
            "gambar": self.b64_image
        }
        
        if t == "PG": 
            ds["opsi"] = {chr(65+i): e.get() for i, e in enumerate(self.i_data)}
            ds["kunci"] = self.k_pg.get()
        elif t in ["PGK", "BS"]: 
            ds["pernyataan"] = [e.get() for e in self.i_data]
            if t == "PGK": ds["kunci"] = [int(v.get()) for v in self.k_v if v.get()!=""]
            else: ds["kunci"] = [v.get() for v in self.k_v]
        elif t == "ESSAY": 
            ds["kunci"] = ""
            
        DATA_UJIAN[p_id]['soal'].append(ds)
        save_db()
        self.upd_tree()
        
        self.txt_soal.delete("1.0", tk.END)
        self.lbl_img.config(text="Tidak ada gambar", fg="gray")
        self.b64_image = ""
        self.ref_form()
        messagebox.showinfo("Sukses", "Soal berhasil disimpan!")

    def setup_tab_proktor(self):
        import socket
        ip = socket.gethostbyname(socket.gethostname())
        tk.Label(self.tab_proktor, text=f"🌐 IP Server Proktor Anda: {ip}", font=("Segoe UI", 16, "bold"), fg="#dc3545", bg="white").pack(pady=10)
        
        f_pwd = tk.Frame(self.tab_proktor, bg="white")
        f_pwd.pack(pady=5)
        tk.Label(f_pwd, text="Password Keluar Siswa:", bg="white", font=("Segoe UI", 10)).pack(side='left')
        self.ent_pwd = ttk.Entry(f_pwd, width=20, show="*")
        self.ent_pwd.insert(0, PROCTOR_PASSWORD)
        self.ent_pwd.pack(side='left', padx=10)
        
        def simpan_pwd():
            global PROCTOR_PASSWORD
            PROCTOR_PASSWORD = self.ent_pwd.get().strip()
            save_db()
            messagebox.showinfo("Sukses", "Password berhasil disimpan!")
            
        self.m_btn(f_pwd, "Simpan", "#6c757d", "white", simpan_pwd).pack(side='left')

        tk.Label(self.tab_proktor, text="Status Paket Ujian", font=("Segoe UI", 12, "bold"), bg="white").pack(anchor='w', pady=(15,5))
        self.tree_p = ttk.Treeview(self.tab_proktor, columns=("ID", "Mapel", "Kls", "Token", "Soal", "Status"), show="headings", height=4)
        for c in ("ID", "Mapel", "Kls", "Token", "Soal", "Status"): 
            self.tree_p.heading(c, text=c)
        self.tree_p.column("ID", width=50); self.tree_p.column("Soal", width=50); self.tree_p.column("Status", width=80)
        self.tree_p.pack(fill='x')
        
        f_btn = tk.Frame(self.tab_proktor, bg="white")
        f_btn.pack(pady=10)
        self.m_btn(f_btn, "▶ AKTIFKAN", "#28a745", "white", lambda: self.tog_ujian(True)).pack(side='left', padx=5)
        self.m_btn(f_btn, "⏸ TUTUP UJIAN", "#dc3545", "white", lambda: self.tog_ujian(False)).pack(side='left', padx=5)
        self.m_btn(f_btn, "📥 UNDUH HASIL (CSV)", "#17a2b8", "white", self.unduh_hasil_csv).pack(side='left', padx=30)
        
        tk.Label(self.tab_proktor, text="Live Monitor Hasil Siswa (Klik Ganda untuk Detail Jawaban)", font=("Segoe UI", 12, "bold"), bg="white").pack(anchor='w', pady=(15,5))
        self.tree_h = ttk.Treeview(self.tab_proktor, columns=("Nama", "Kls", "Mapel", "Skor"), show="headings", height=8)
        for c in ("Nama", "Kls", "Mapel", "Skor"): 
            self.tree_h.heading(c, text=c)
        self.tree_h.pack(fill='both', expand=True)
        self.tree_h.bind("<Double-1>", self.cek_essay)
        
        self.upd_tree()

    def tog_ujian(self, aktif):
        s = self.tree_p.selection()
        if s: 
            p_id = self.tree_p.item(s[0])['values'][0]
            DATA_UJIAN[p_id]['aktif'] = aktif
            save_db()
            self.upd_tree()

    def upd_tree(self):
        for i in self.tree_p.get_children(): self.tree_p.delete(i)
        for k, v in DATA_UJIAN.items(): 
            status = "🟢 Aktif" if v.get('aktif') else "🔴 Tutup"
            self.tree_p.insert("", tk.END, values=(k, v['mapel'], v['kelas'], v['token'], len(v['soal']), status))

    def update_proktor_hasil(self):
        for i in self.tree_h.get_children(): self.tree_h.delete(i)
        for d in HASIL_SISWA.values(): 
            self.tree_h.insert("", tk.END, values=(d['nama'], d['kelas'], d['mapel'], f"{d['skor']:.2f}"))

    def cek_essay(self, ev):
        s = self.tree_h.selection()
        if not s: return
        v = self.tree_h.item(s[0])['values']
        
        d = next((x for x in HASIL_SISWA.values() if x['nama']==v[0] and str(x['kelas'])==str(v[1])), None)
        if not d: return
        p = next((x for x in DATA_UJIAN.values() if x['token']==d['token']), None)
        
        w = tk.Toplevel(self)
        w.title(f"Detail Jawaban - {v[0]}")
        w.geometry("700x600")
        w.configure(bg="#ffffff")
        
        tk.Label(w, text=f"Detail Jawaban: {v[0]}\nSkor Akhir: {d['skor']:.2f}", font=("Segoe UI", 14, "bold"), bg="#ffffff", fg="#1a252f").pack(pady=10)
        
        t = tk.Text(w, font=("Segoe UI", 11), wrap="word", bg="#f8f9fa", relief="solid", bd=1, padx=10, pady=10)
        t.pack(fill="both", expand=True, padx=20, pady=(0,20))
        
        for soal in (p['soal'] if p else []):
            tipe = soal['tipe']
            sid = str(soal['id'])
            jwb_siswa = d['detail'].get(sid, '[Tidak Dijawab]')
            kunci = soal.get('kunci', '')
            
            t.insert(tk.END, f"Soal No {soal['id']} ({tipe}) - Poin: {soal.get('bobot', 10):.2f}\n", "bold")
            t.insert(tk.END, f"Tanya: {soal['soal']}\n")
            
            if tipe == 'ESSAY':
                t.insert(tk.END, f"Jawaban Siswa:\n{jwb_siswa}\n")
            else:
                t.insert(tk.END, f"Jawab Siswa: {jwb_siswa}\n")
                t.insert(tk.END, f"Kunci Benar: {kunci}\n")
                
                benar = False
                if tipe == 'PG' and jwb_siswa == kunci: benar = True
                elif tipe == 'PGK' and isinstance(jwb_siswa, list) and sorted(jwb_siswa) == sorted(kunci): benar = True
                elif tipe == 'BS' and isinstance(jwb_siswa, list) and jwb_siswa == kunci: benar = True
                
                if benar: t.insert(tk.END, "Status: ✅ BENAR\n")
                else: t.insert(tk.END, "Status: ❌ SALAH\n")
                    
            t.insert(tk.END, f"\n{'-'*60}\n\n")
            
        t.tag_configure("bold", font=("Segoe UI", 11, "bold"))
        t.config(state="disabled")

    def unduh_hasil_csv(self):
        if not HASIL_SISWA:
            return messagebox.showwarning("Peringatan", "Belum ada data hasil ujian siswa yang masuk!")

        fp = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV/Excel Files", "*.csv")], initialfile="Rekap_Hasil_CBT.csv")
        if not fp: return

        try:
            with open(fp, mode='w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f, delimiter=',')
                writer.writerow(["Nama Siswa", "Kelas", "Mata Pelajaran", "Token", "Skor Akhir", "Rincian Jawaban Siswa"])
                
                for d in HASIL_SISWA.values():
                    rincian = []
                    for id_soal, jwb in d['detail'].items():
                        rincian.append(f"Soal {id_soal}: {jwb}")
                    teks_rincian = " | ".join(rincian)
                    
                    writer.writerow([d['nama'], d['kelas'], d['mapel'], d['token'], f"{d['skor']:.2f}", teks_rincian])
                    
            messagebox.showinfo("Sukses", f"Hasil ujian berhasil diunduh!\n\nFile tersimpan di:\n{fp}\n\nSilakan upload ke Google Drive dan buka dengan Google Sheets.")
        except Exception as e:
            messagebox.showerror("Error", f"Gagal mengunduh file:\n{e}")

if __name__ == "__main__": 
    app = GuruApp()
    app.mainloop()