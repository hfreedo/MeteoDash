"""
MeteoDash Launcher - Panel de Despliegue
GUI con Tkinter | Dark theme | Ngrok + Cloudflare + Local
"""
import ctypes, json, os, re, shutil, socket, subprocess, sys, threading, time
import tkinter as tk
from pathlib import Path
from datetime import datetime
from tkinter import scrolledtext, messagebox

try: ctypes.windll.shcore.SetProcessDpiAwareness(2)
except: pass

# Colors
BG,CARD,ACCENT,GREEN,BLUE,ORANGE,PURPLE = "#0b1016","#141c26","#ff4655","#1ce783","#3b82f6","#ffaa00","#8b5cf6"
WHITE,GRAY,MUTED,DARKIN,BORDER,LOGBG = "#e8e9f0","#8899a6","#556670","#0d1520","#1d2a36","#080e14"

def base(): return Path(sys.argv[0]).resolve().parent if getattr(sys,'frozen',False) else Path(__file__).resolve().parent
BASE,BACKEND,CONFIG = base(), base()/"backend", base()/"launcher_config.json"

def python_runtime():
    venv_python = BASE / ".venv" / "Scripts" / "python.exe"
    if venv_python.exists():
        return str(venv_python)
    return shutil.which("python") or shutil.which("python3") or sys.executable

PYTHON = python_runtime()

def tool(n): return shutil.which(n) is not None
def ip(): 
    try: s=socket.socket(2,2);s.settimeout(.5);s.connect(("8.8.8.8",80));r=s.getsockname()[0];s.close();return r
    except: return "127.0.0.1"
def browser():
    for e in["brave.exe","chrome.exe","msedge.exe"]:
        p=shutil.which(e)
        if p:return p
    return None
def cfg_load():
    d={"ngrok_token":"","ngrok_domain":"","auto_start":False}
    try:
        if CONFIG.exists():d.update(json.loads(CONFIG.read_text("utf-8")))
    except:pass
    return d
def cfg_save(d):
    try:CONFIG.write_text(json.dumps(d,indent=2),"utf-8")
    except:pass

class L:
    def __init__(self):
        self.cfg=cfg_load();self.srv=None;self.tun=None;self.watch=False
        self._q=[]  # cola de mensajes para log (thread-safe)
        self._zombies()
        self.root=tk.Tk();self.root.title("MeteoDash - Panel de Despliegue")
        self.root.geometry("860x780");self.root.minsize(700,650);self.root.configure(bg=BG)
        self._ui();self._refresh()
        self._log("Launcher iniciado\n")
        self.root.protocol("WM_DELETE_WINDOW",self._close)
        self.root.after(100,self._drain)
        if self.cfg.get("auto_start"):self.root.after(800,self._srv_start)
        self.root.mainloop()

    def _drain(self):
        while self._q:
            m=self._q.pop(0)
            self.lg.configure(state="normal");self.lg.insert("end",m);self.lg.see("end");self.lg.configure(state="disabled")
        self.root.after(250,self._drain)

    def _zombies(self):
        for n in["ngrok.exe","cloudflared.exe"]:
            try:subprocess.run(["taskkill","/f","/im",n],capture_output=True,timeout=3,creationflags=0x08000000 if sys.platform=="win32"else 0)
            except:pass

    def _ui(self):
        tk.Label(self.root,text="METEODASH",font=("Rajdhani",22,"bold"),fg=WHITE,bg=BG).pack(pady=(14,0))
        tk.Label(self.root,text="Sistema Meteorologico - Panel de Despliegue",font=("Rajdhani",9),fg=ACCENT,bg=BG).pack(pady=(0,10))
        tk.Frame(self.root,height=1,bg=BORDER).pack(fill="x",padx=28)
        bd=tk.Frame(self.root,bg=BG);bd.pack(fill="both",expand=True,padx=22,pady=8)
        Lf=tk.Frame(bd,bg=BG,width=300);Lf.pack(side="left",fill="y",padx=(0,10));Lf.pack_propagate(False)
        Rf=tk.Frame(bd,bg=BG);Rf.pack(side="right",fill="both",expand=True)
        self._status(Lf);self._server(Lf);self._modes(Lf);self._log_ui(Rf)

    def _status(self,p):
        c=tk.Frame(p,bg=CARD,padx=14,pady=10,highlightthickness=1,highlightbackground=BORDER);c.pack(fill="x",pady=(0,8))
        tk.Label(c,text="ESTADO",font=("Rajdhani",9,"bold"),fg=GRAY,bg=CARD).pack(anchor="w",pady=(0,6))
        r=tk.Frame(c,bg=CARD);r.pack(fill="x",pady=1)
        tk.Label(r,text="IP:",font=("Consolas",9),fg=MUTED,bg=CARD).pack(side="left")
        self.lip=tk.Label(r,text="...",font=("Consolas",9,"bold"),fg=GRAY,bg=CARD);self.lip.pack(side="left",padx=4)
        tk.Button(r,text="Copiar",font=("Consolas",7),fg=MUTED,bg=CARD,relief="flat",bd=0,padx=4,cursor="hand2",command=lambda:self._cp(ip())).pack(side="right")
        for lb,da,la in[("Servidor","ds","ls"),("Cloudflared","dc","lc"),("Ngrok","dn","ln")]:
            r=tk.Frame(c,bg=CARD);r.pack(fill="x",pady=2)
            setattr(self,da,tk.Canvas(r,width=10,height=10,bg=CARD,highlightthickness=0));getattr(self,da).pack(side="left",padx=(0,6))
            getattr(self,da).create_oval(1,1,9,9,fill=GRAY,outline="")
            setattr(self,la,tk.Label(r,text=lb,font=("Consolas",9),fg=GRAY,bg=CARD));getattr(self,la).pack(side="left")

    def _server(self,p):
        self.bs=tk.Button(p,text="INICIAR SERVIDOR",font=("Rajdhani",12,"bold"),fg=GREEN,bg=CARD,activeforeground=WHITE,activebackground="#1c2a3d",relief="flat",bd=0,padx=14,pady=10,cursor="hand2",command=self._ts);self.bs.pack(fill="x",pady=(0,8))
        self._hv(self.bs,CARD,"#1c2a3d")

    def _modes(self,p):
        c=tk.Frame(p,bg=CARD,padx=14,pady=10,highlightthickness=1,highlightbackground=BORDER);c.pack(fill="x",pady=(0,8))
        tk.Label(c,text="DESPLIEGUE",font=("Rajdhani",9,"bold"),fg=GRAY,bg=CARD).pack(anchor="w",pady=(0,6))
        for tx,co,cm in[("Local / WiFi Hotspot",GREEN,self._ml),("Cloudflare Tunnel",BLUE,self._mc),("Ngrok",PURPLE,self._mn),("Serveo (SSH)",ORANGE,self._ms)]:
            r=tk.Frame(c,bg=CARD);r.pack(fill="x",pady=1)
            b=tk.Button(r,text=tx,font=("Rajdhani",10,"bold"),fg=co,bg=DARKIN,activeforeground=WHITE,activebackground="#1c2a3d",relief="flat",bd=0,padx=12,pady=7,cursor="hand2",command=cm,anchor="w")
            b.pack(side="left",fill="x",expand=True);self._hv(b,DARKIN,"#1c2a3d")
            if"Ngrok"in tx:tk.Button(r,text="\u2699",font=("Consolas",10),fg=MUTED,bg=CARD,relief="flat",bd=0,padx=6,cursor="hand2",command=self._cfg).pack(side="right")
            if"Cloudflare"in tx:tk.Button(r,text="?",font=("Consolas",9,"bold"),fg=MUTED,bg=CARD,relief="flat",bd=0,padx=6,cursor="hand2",command=lambda:messagebox.showinfo("Cloudflare","URL aleatoria gratuita. No requiere configuracion.\nPara URL fija: cuenta cloudflare.com + dominio.")).pack(side="right")
        # URL frame
        self.uf=tk.Frame(p,bg=CARD,padx=12,pady=8,highlightthickness=1,highlightbackground=BORDER);self.uf.pack(fill="x",pady=(0,8))
        self.ul=tk.Label(self.uf,text="Inicia un tunel para ver la URL aqui",font=("Consolas",8),fg=MUTED,bg=CARD,anchor="w",wraplength=260);self.ul.pack(fill="x")
        self.ub=tk.Frame(self.uf,bg=CARD);self.ub.pack(fill="x",pady=(6,0))
        # Dashboard
        tk.Button(p,text="ABRIR DASHBOARD",font=("Rajdhani",11,"bold"),fg=WHITE,bg=ACCENT,activeforeground=WHITE,activebackground="#cc0000",relief="flat",bd=0,padx=14,pady=10,cursor="hand2",command=lambda:self._op("http://localhost:8000")).pack(fill="x",pady=(0,4))

    def _log_ui(self,p):
        h=tk.Frame(p,bg=BG);h.pack(fill="x")
        tk.Label(h,text="REGISTRO",font=("Rajdhani",9,"bold"),fg=GRAY,bg=BG).pack(side="left")
        tk.Button(h,text="Limpiar",font=("Consolas",8),fg=MUTED,bg=BG,relief="flat",bd=0,cursor="hand2",command=self._lc).pack(side="right")
        self.lg=scrolledtext.ScrolledText(p,font=("Consolas",9),bg=LOGBG,fg="#6a7d8c",insertbackground=WHITE,relief="flat",bd=0,padx=10,pady=6,wrap="word")
        self.lg.pack(fill="both",expand=True);self.lg.configure(state="disabled")

    def _hv(self,w,n,h):w.bind("<Enter>",lambda e:w.configure(bg=h));w.bind("<Leave>",lambda e:w.configure(bg=n))
    def _log(self,m):
        self._q.append(f"[{datetime.now().strftime('%H:%M:%S')}] {m}\n")
    def _lc(self):self._q.clear();self.lg.configure(state="normal");self.lg.delete("1.0","end");self.lg.configure(state="disabled")
    def _refresh(self):
        self.lip.configure(text=ip());cf=tool("cloudflared");ng=tool("ngrok")
        if self.srv:self.ls.configure(text="Servidor ACTIVO",fg=GREEN);self._dot(self.ds,GREEN)
        else:self.ls.configure(text="Servidor DETENIDO",fg=GRAY);self._dot(self.ds,GRAY)
        self.lc.configure(text=f"Cloudflared: {'OK' if cf else 'NO INSTALADO'}",fg=GREEN if cf else ACCENT);self._dot(self.dc,GREEN if cf else ACCENT)
        self.ln.configure(text=f"Ngrok: {'OK' if ng else 'NO INSTALADO'}",fg=GREEN if ng else ACCENT);self._dot(self.dn,GREEN if ng else ACCENT)
    def _dot(self,c,co):c.delete("all");c.create_oval(1,1,9,9,fill=co,outline="")
    def _cp(self,tx):self.root.clipboard_clear();self.root.clipboard_append(tx);self._log(f"Copiado: {tx}\n")
    def _op(self,url):
        b=browser()
        if b:subprocess.Popen([b,url])
        else:import webbrowser;webbrowser.open(url)

    def _close(self):
        self.watch=False;self.cfg["auto_start"]=False;cfg_save(self.cfg);self._ks();self._kt();self.root.destroy()

    def _ts(self):
        if self.srv:self._ss()
        else:self._s0()

    def _s0(self):
        if not(BACKEND/"main.py").is_file():messagebox.showerror("Error",f"No se encontro backend/main.py");return
        try:out=subprocess.check_output('netstat -ano | findstr :8000 | findstr LISTENING',shell=True,text=True,timeout=5,creationflags=0x08000000 if sys.platform=="win32"else 0)
        except:out=""
        for ln in out.strip().split('\n'):
            ps=ln.strip().split()
            if ps:
                try:subprocess.run(["taskkill","/f","/pid",ps[-1]],capture_output=True,timeout=3,creationflags=0x08000000 if sys.platform=="win32"else 0)
                except:pass
        try:
            env={**os.environ,"PYTHONUNBUFFERED":"1"}
            self.srv=subprocess.Popen([PYTHON,"main.py"],cwd=str(BACKEND),stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,bufsize=1,env=env,creationflags=0x08000000 if sys.platform=="win32"else 0)
        except Exception as e:self._log(f"ERROR servidor: {e}\n");return
        self.watch=True;self._rd(self.srv,"SRV")
        self.bs.configure(text="DETENER SERVIDOR",fg=ACCENT);self._log("Servidor iniciado en :8000\n");self._refresh()

    def _ss(self):
        self.watch=False;self._kt();self._ks()
        self.bs.configure(text="INICIAR SERVIDOR",fg=GREEN);self._log("Servidor detenido\n");self._refresh()

    def _ks(self):
        if self.srv:
            try:self.srv.terminate();self.srv.wait(timeout=3)
            except:
                try:self.srv.kill()
                except:pass
            self.srv=None

    def _kt(self):
        if self.tun:
            try:self.tun.terminate();self.tun.wait(timeout=2)
            except:
                try:self.tun.kill()
                except:pass
            self.tun=None

    def _rd(self,pr,tg):
        def _r():
            try:
                for ln in iter(pr.stdout.readline,""):
                    if not self.watch:break
                    if ln.strip():self._log(f"[{tg}] {ln}")
            except:pass
        threading.Thread(target=_r,daemon=True).start()

    def _chk(self,cb):
        def _c():
            import urllib.request
            for i in range(3):
                try:urllib.request.urlopen("http://127.0.0.1:8000",timeout=1.5);self.root.after(0,lambda:cb(True));return
                except:time.sleep(0.8)
            self.root.after(0,lambda:cb(False))
        threading.Thread(target=_c,daemon=True).start()

    def _ml(self):
        self._chk(lambda ok:self._log(f"\n{'='*50}\n  MODO LOCAL\n  http://{ip()}:8000\n{'='*50}\n\n")if ok else self._log("ERROR: Servidor no responde\n"))

    def _mc(self):
        if not tool("cloudflared"):messagebox.showwarning("No instalado","winget install Cloudflare.cloudflared");return
        self._chk(lambda ok:self._go(["cloudflared","tunnel","--url","http://localhost:8000"],"CF")if ok else self._log("ERROR: Servidor no responde\n"))

    def _mn(self):
        if not tool("ngrok"):messagebox.showwarning("No instalado","winget install ngrok.ngrok");return
        t=self.cfg.get("ngrok_token","")
        if not t:
            if messagebox.askyesno("Configurar","Ngrok necesita token. Configurar ahora?"):self._cfg()
            return
        self._chk(lambda ok:(
            lambda:self._go(["ngrok","http","--url="+self.cfg.get("ngrok_domain","").strip(),"--log=stdout","8000"],"NG")if self.cfg.get("ngrok_domain","").strip()else self._go(["ngrok","http","--log=stdout","8000"],"NG")
        )()if ok else self._log("ERROR: Servidor no responde\n"))

    def _ms(self):
        self._chk(lambda ok:self._go(["ssh","-o","StrictHostKeyChecking=no","-R","80:localhost:8000","serveo.net"],"SV")if ok else self._log("ERROR: Servidor no responde\n"))

    def _go(self,cmd,tg):
        self._kt()
        def _r():
            try:
                self.tun=subprocess.Popen(cmd,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,bufsize=1,creationflags=0x08000000 if sys.platform=="win32"else 0)
                self._log(f"[{tg}] Iniciado\n")
            except FileNotFoundError:self._log(f"[{tg}] ERROR: {cmd[0]} no encontrado\n");return
            except Exception as e:self._log(f"[{tg}] ERROR: {e}\n");return
            try:
                for ln in iter(self.tun.stdout.readline,""):
                    if not self.watch:break
                    ln=ln.rstrip('\r\n')
                    if ln.strip():self._log(f"[{tg}] {ln}\n")
                    m=re.search(r'(https://[^\s,;]+)',ln)
                    if m:
                        u=m.group(1).rstrip('.,;')
                        if any(d in u for d in['ngrok','trycloudflare','serveo']):
                            self._log(f">>> URL: {u}\n")
                            self.root.after(0,lambda url=u:self._su(url))
            except Exception as e:self._log(f"[{tg}] Error: {e}\n")
            self.tun=None
        threading.Thread(target=_r,daemon=True).start()

    def _su(self,url):
        self.ul.configure(text=url,fg=GREEN)
        for w in self.ub.winfo_children():w.destroy()
        tk.Button(self.ub,text="ABRIR URL",font=("Rajdhani",9,"bold"),fg=WHITE,bg=GREEN,activeforeground=WHITE,activebackground="#0fa968",relief="flat",bd=0,padx=12,pady=5,cursor="hand2",command=lambda:self._op(url)).pack(side="left",padx=(0,6))
        tk.Button(self.ub,text="COPIAR",font=("Rajdhani",9,"bold"),fg=WHITE,bg=BLUE,activeforeground=WHITE,activebackground="#2278e0",relief="flat",bd=0,padx=12,pady=5,cursor="hand2",command=lambda:self._cp(url)).pack(side="left")

    def _cfg(self):
        d=tk.Toplevel(self.root);d.title("Configurar Ngrok");d.geometry("500x480");d.configure(bg=BG);d.transient(self.root);d.grab_set();d.resizable(False,False)
        tk.Label(d,text="CONFIGURACION NGROK",font=("Rajdhani",16,"bold"),fg=WHITE,bg=BG).pack(pady=(20,2))
        inf=tk.Frame(d,bg="#0d2818",padx=12,pady=8,highlightthickness=1,highlightbackground="#1a4a2a");inf.pack(fill="x",padx=24,pady=(4,10))
        tk.Label(inf,text="Como obtener tu token:",font=("Rajdhani",9,"bold"),fg=GREEN,bg="#0d2818").pack(anchor="w")
        for s in["1. Crea cuenta gratis en ngrok.com","2. Copia el token de dashboard.ngrok.com"]:tk.Label(inf,text=s,font=("Consolas",8),fg="#6aaa7a",bg="#0d2818",anchor="w").pack(fill="x")
        f=tk.Frame(d,bg=CARD,padx=18,pady=16,highlightthickness=1,highlightbackground=BORDER);f.pack(fill="x",padx=24)
        tk.Label(f,text="Auth Token (obligatorio)",font=("Rajdhani",10,"bold"),fg=WHITE,bg=CARD).pack(anchor="w")
        e1=tk.Entry(f,font=("Consolas",9),bg=DARKIN,fg=WHITE,insertbackground=WHITE,relief="flat",bd=0);e1.pack(fill="x",pady=(2,8),ipady=4);e1.insert(0,self.cfg.get("ngrok_token",""))
        tk.Label(f,text="Dominio fijo (opcional)",font=("Rajdhani",10,"bold"),fg=WHITE,bg=CARD).pack(anchor="w")
        tk.Label(f,text="Crearlo en dashboard.ngrok.com > Domains",font=("Consolas",8),fg=MUTED,bg=CARD).pack(anchor="w");tk.Label(f,text="Dejar vacio = URL aleatoria",font=("Consolas",8),fg=GREEN,bg=CARD).pack(anchor="w",pady=(0,8))
        e2=tk.Entry(f,font=("Consolas",9),bg=DARKIN,fg=WHITE,insertbackground=WHITE,relief="flat",bd=0);e2.pack(fill="x",pady=(0,8),ipady=4);e2.insert(0,self.cfg.get("ngrok_domain",""))
        def _sv():
            self.cfg["ngrok_token"]=e1.get().strip();self.cfg["ngrok_domain"]=e2.get().strip();cfg_save(self.cfg);self._log("Config Ngrok guardada\n");d.destroy()
        bf=tk.Frame(d,bg=BG);bf.pack(pady=(10,18))
        sb=tk.Button(bf,text="GUARDAR CONFIGURACION",font=("Rajdhani",12,"bold"),fg=WHITE,bg=ACCENT,activeforeground=WHITE,activebackground="#cc0000",relief="flat",bd=0,padx=28,pady=10,cursor="hand2",command=_sv);sb.pack()
        self._hv(sb,ACCENT,"#cc0000")

if __name__=="__main__":L()
