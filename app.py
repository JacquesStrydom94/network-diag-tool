#property of jacques strydom south african identification 9404145098088 phone +27782524669 for more info
import customtkinter as ctk
import tkinter as tk
from tkinter import messagebox, filedialog
import subprocess, re, platform, threading, socket, csv, datetime, requests

# Zoomable canvas with mouse-wheel zoom & scroll
class ZoomableCanvas(tk.Canvas):
    def __init__(self, parent, **kwargs):
        super().__init__(parent, **kwargs)
        self.scale_factor = 1.0
        self.bind('<MouseWheel>', self._on_mousewheel)
        self.bind('<Button-4>', self._on_mousewheel)
        self.bind('<Button-5>', self._on_mousewheel)

    def _on_mousewheel(self, event):
        delta = event.delta if hasattr(event, 'delta') else (120 if event.num == 4 else -120)
        factor = 1.1 if delta > 0 else 0.9
        self.scale_factor *= factor
        x = self.canvasx(event.x)
        y = self.canvasy(event.y)
        self.scale('all', x, y, factor, factor)
        self.configure(scrollregion=self.bbox('all'))

class TraceApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        # Default to dark mode
        ctk.set_appearance_mode('Dark')
        ctk.set_default_color_theme('dark-blue')
        self.title('Address & ASN Route Sketcher')
        self.geometry('1200x800')
        self.configure(padx=10, pady=10)

        # Data holders
        self.hops = []
        self.latencies = []
        self.asns = []

        # Make canvases expand
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)
        self.grid_rowconfigure(5, weight=1)

        # Top control frame
        ctrl = ctk.CTkFrame(self)
        ctrl.grid(row=0, column=0, sticky='ew', pady=(0,10))
        ctrl.grid_columnconfigure(1, weight=1)
        ctrl.grid_columnconfigure(3, weight=1)

        # Theme toggle
        self.theme_switch = ctk.CTkSwitch(ctrl, text='Light Theme', command=self.toggle_theme)
        self.theme_switch.select()  # start in dark mode
        self.theme_switch.grid(row=0, column=0, padx=5, sticky='w')

        # Start address entry
        ctk.CTkLabel(ctrl, text='Start Address:').grid(row=0, column=1, padx=5, sticky='e')
        self.src_ent = ctk.CTkEntry(ctrl)
        self.src_ent.grid(row=0, column=2, padx=5, sticky='ew')
        try:
            public_ip = requests.get('https://api.ipify.org', timeout=5).text
            self.src_ent.insert(0, public_ip)
        except:
            pass

        # End address entry
        ctk.CTkLabel(ctrl, text='End Address:').grid(row=0, column=3, padx=5, sticky='e')
        self.dst_ent = ctk.CTkEntry(ctrl)
        self.dst_ent.grid(row=0, column=4, padx=5, sticky='ew')

        # Buttons
        ctk.CTkButton(ctrl, text='Trace & Draw', command=self.on_trace).grid(row=0, column=5, padx=5)
        ctk.CTkButton(ctrl, text='Export Report', command=self.export_report).grid(row=0, column=6, padx=5)

        # IP canvas
        ctk.CTkLabel(self, text='IP Route Propagation', font=('Arial',14,'bold')).grid(row=1, column=0)
        self.canvas_ip = ZoomableCanvas(self, bg='#2b2b2b')
        vsb1 = ctk.CTkScrollbar(self, orientation='vertical', command=self.canvas_ip.yview)
        hsb1 = ctk.CTkScrollbar(self, orientation='horizontal', command=self.canvas_ip.xview)
        self.canvas_ip.configure(yscrollcommand=vsb1.set, xscrollcommand=hsb1.set)
        self.canvas_ip.grid(row=2, column=0, sticky='nsew')
        vsb1.grid(row=2, column=1, sticky='ns')
        hsb1.grid(row=3, column=0, sticky='ew')

        # ASN canvas
        ctk.CTkLabel(self, text='ASN Route Propagation', font=('Arial',14,'bold')).grid(row=4, column=0, pady=(10,0))
        self.canvas_asn = ZoomableCanvas(self, bg='#2b2b2b')
        vsb2 = ctk.CTkScrollbar(self, orientation='vertical', command=self.canvas_asn.yview)
        hsb2 = ctk.CTkScrollbar(self, orientation='horizontal', command=self.canvas_asn.xview)
        self.canvas_asn.configure(yscrollcommand=vsb2.set, xscrollcommand=hsb2.set)
        self.canvas_asn.grid(row=5, column=0, sticky='nsew')
        vsb2.grid(row=5, column=1, sticky='ns')
        hsb2.grid(row=6, column=0, sticky='ew')

        # High-latency lists
        lat_frame = ctk.CTkFrame(self)
        lat_frame.grid(row=7, column=0, sticky='ew', pady=(10,0))
        lat_frame.grid_columnconfigure(0, weight=1)
        lat_frame.grid_columnconfigure(1, weight=1)
        ctk.CTkLabel(lat_frame, text='High Latency (>20ms) IPs:').grid(row=0, column=0, sticky='w')
        self.high_ip_txt = ctk.CTkTextbox(lat_frame, height=80)
        self.high_ip_txt.grid(row=1, column=0, sticky='ew', padx=5, pady=5)
        ctk.CTkLabel(lat_frame, text='High Latency (>20ms) ASNs:').grid(row=0, column=1, sticky='w')
        self.high_asn_txt = ctk.CTkTextbox(lat_frame, height=80)
        self.high_asn_txt.grid(row=1, column=1, sticky='ew', padx=5, pady=5)

        # Status bar
        self.status_var = tk.StringVar(value='Ready')
        ctk.CTkLabel(self, textvariable=self.status_var, anchor='w').grid(row=8, column=0, sticky='ew', pady=(10,0))

    def toggle_theme(self):
        if self.theme_switch.get():
            ctk.set_appearance_mode('Dark')
            self.theme_switch.configure(text='Light Theme')
        else:
            ctk.set_appearance_mode('Light')
            self.theme_switch.configure(text='Dark Theme')

    def on_trace(self):
        dst = self.dst_ent.get().strip()
        if not dst:
            messagebox.showwarning('Input error', 'Enter End Address.')
            return
        self.status_var.set('Resolving...')
        try:
            src = self.src_ent.get().strip()
            src_ip = socket.gethostbyname(src) if src else ''
            dst_ip = socket.gethostbyname(dst)
        except Exception as e:
            messagebox.showerror('Resolution error', str(e))
            return
        self.status_var.set('Tracing...')
        threading.Thread(target=self.trace_and_draw, args=(src_ip, dst_ip), daemon=True).start()

    def trace_and_draw(self, src, dst):
        self.hops = self.perform_traceroute(src, dst)
        self.latencies = [self.get_latency(h) for h in self.hops]
        self.asns = [self.get_asn(h) for h in self.hops]
        self.status_var.set('Drawing...')
        # Draw propagation sketches
        self.draw_propagation(self.canvas_ip, [f"{h}\n{l} ms" for h,l in zip(self.hops,self.latencies)])
        self.draw_propagation(self.canvas_asn, [f"{a}\n{l} ms" for a,l in zip(self.asns,self.latencies)])
        # Populate high-latency lists
        high_ips = [f"{h}: {l} ms" for h,l in zip(self.hops,self.latencies) if l.replace('.','',1).isdigit() and float(l)>20]
        high_asns = [f"{a}: {l} ms" for a,l in zip(self.asns,self.latencies) if l.replace('.','',1).isdigit() and float(l)>20]
        for textbox, data in ((self.high_ip_txt, high_ips),(self.high_asn_txt, high_asns)):
            textbox.configure(state='normal')
            textbox.delete('0.0','end')
            textbox.insert('0.0', '\n'.join(data))
            textbox.configure(state='disabled')
        self.status_var.set('Done')

    def perform_traceroute(self, src, dst):
        if platform.system() == 'Windows':
            cmd = ['tracert','-d',dst]
        else:
            cmd = ['traceroute','-n','-s',src,dst] if src else ['traceroute','-n',dst]
        try:
            out = subprocess.run(cmd, capture_output=True, text=True, timeout=60).stdout
        except:
            return []
        hops = []
        for line in out.splitlines():
            m = re.findall(r"\b\d+\.\d+\.\d+\.\d+\b", line)
            if m:
                hops.append(m[-1])
        return hops

    def get_latency(self, ip):
        if platform.system() == 'Windows':
            cmd = ['ping','-n','1','-w','1000',ip]
        else:
            cmd = ['ping','-c','1','-W','1',ip]
        try:
            out = subprocess.run(cmd, capture_output=True, text=True, timeout=5).stdout
            m = re.search(r'time[=<](\d+\.?\d*) ?ms', out)
            return m.group(1) if m else 'N/A'
        except:
            return 'N/A'

    def get_asn(self, ip):
        try:
            with socket.create_connection(('whois.cymru.com', 43), timeout=10) as s:
                s.sendall(f"begin\nverbose\n{ip}\nend\n".encode())
                data = b''
                while True:
                    chunk = s.recv(4096)
                    if not chunk: break
                    data += chunk
            parts = data.decode(errors='ignore').splitlines()[1].split('|')
            return f"AS{parts[0].strip()} {parts[4].strip()}"
        except:
            return 'Unknown'

    def export_report(self):
        if not self.hops:
            messagebox.showinfo('No Data','Run trace first.')
            return
        fname = filedialog.asksaveasfilename(
            defaultextension='.csv',
            filetypes=[('CSV','.csv')],
            initialfile=f"report_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        )
        if not fname: return
        # Recompute high-latency lists for export
        high_ips = [f"{h}: {l} ms" for h,l in zip(self.hops,self.latencies) if l.replace('.','',1).isdigit() and float(l)>20]
        high_asns = [f"{a}: {l} ms" for a,l in zip(self.asns,self.latencies) if l.replace('.','',1).isdigit() and float(l)>20]
        try:
            with open(fname,'w',newline='') as f:
                w = csv.writer(f)
                w.writerow(['Hop','IP','Latency_ms','ASN'])
                for i,(ip,lat,asn) in enumerate(zip(self.hops,self.latencies,self.asns),1):
                    w.writerow([i,ip,lat,asn])
                w.writerow([])
                w.writerow(['High Latency IPs'])
                for item in high_ips:
                    w.writerow([item])
                w.writerow([])
                w.writerow(['High Latency ASNs'])
                for item in high_asns:
                    w.writerow([item])
            messagebox.showinfo('Export Complete',f'Saved to {fname}')
        except Exception as e:
            messagebox.showerror('Error',str(e))

    def draw_propagation(self, canvas, labels):
        canvas.delete('all')
        n = len(labels)
        if n == 0: return
        w, h = canvas.winfo_width(), canvas.winfo_height()
        r = 20
        xs = [(i+1)*w//(n+1) for i in range(n)]
        y = h//2
        # draw nodes
        for i, lbl in enumerate(labels):
            x = xs[i]
            canvas.create_oval(x-r, y-r, x+r, y+r, fill='#3e3e3e', outline='#6e6e6e', width=2)
            canvas.create_text(x, y, text=lbl, font=('Arial',8), fill='white')
        # draw mesh
        for i in range(n):
            for j in range(i+1, n):
                x1, x2 = xs[i]+r, xs[j]-r
                mid = (x1 + x2)//2
                ctrlY = y - 30 + 20*((i+j)%2)
                canvas.create_line(x1, y, mid, ctrlY, x2, y,
                                   smooth=True, splinesteps=50, fill='#555')
        # draw spokes
        for j in range(1, n):
            x1, x2 = xs[0]+r, xs[j]-r
            mid = (x1 + x2)//2
            ctrlY = y - 50
            canvas.create_line(x1, y, mid, ctrlY, x2, y,
                               smooth=True, splinesteps=50, fill='white', width=3, arrow='last')

if __name__ == '__main__':
    app = TraceApp()
    app.mainloop()
#property of jacques strydom south african identification 9404145098088 phone +27782524669 for more info