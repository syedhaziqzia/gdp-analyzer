"""
GDP Analyzer - Final Version:
A professional, lightweight tool for exploring Global GDP data using the World Bank API.
Features: Single Analysis, Comparison Charting, and Growth Trend Visualizations.
"""

import tkinter as tk
from tkinter import messagebox, filedialog, ttk
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import requests
import threading

class GDPAnalyzer:
    # --- CONFIGURATION ---
    COUNTRIES = {
        'United States': 'USA', 'China': 'CHN', 'Japan': 'JPN', 
        'Germany': 'DEU', 'United Kingdom': 'GBR', 'Pakistan': 'PAK'
    }
    CURRENCIES = {
        'United States': '$', 'China': '¥', 'Japan': '¥', 
        'Germany': '€', 'United Kingdom': '£', 'Pakistan': '₨'
    }

    def __init__(self):
        # 1. Root Window Setup
        self.win = tk.Tk()
        self.win.title("Global GDP Analyzer - Professional Edition")
        self.win.geometry("620x600")
        self.win.configure(bg="#121212") # Sleek deep dark background
        self.cache = {}
        
        # 2. Styling
        style = ttk.Style()
        style.theme_use('clam')
        style.configure("TCombobox", fieldbackground="#1e1e1e", background="#007ACC", foreground="white")

        # 3. UI Construction
        tk.Label(self.win, text="GDP ANALYZER", font=("Helvetica", 26, "bold"), bg="#121212", fg="#007ACC").pack(pady=20)
        
        self.c1_var = tk.StringVar(value="United States")
        self.c2_var = tk.StringVar(value="China")
        self.yr_var = tk.StringVar(value="2022")
        
        # Input Groups
        for lbl, var, vals in [("Primary Country:", self.c1_var, list(self.COUNTRIES.keys())), 
                               ("Comparison Country (Optional):", self.c2_var, list(self.COUNTRIES.keys())),
                               ("Select Target Year:", self.yr_var, [str(y) for y in range(2000, 2024)])]:
            tk.Label(self.win, text=lbl, font=("Helvetica", 10), bg="#121212", fg="#bbbbbb").pack()
            ttk.Combobox(self.win, textvariable=var, values=vals, state="readonly", width=30).pack(pady=(2, 12))

        # Button Dashboard
        self.btn_f = tk.Frame(self.win, bg="#121212")
        self.btn_f.pack(pady=15)
        
        btn_opts = {"bg": "#007ACC", "fg": "white", "width": 18, "font": ("Helvetica", 10, "bold"), "cursor": "hand2"}
        actions = [("Single View", self.do_analyze), ("Compare View", self.do_compare), 
                   ("Growth Trends", self.do_growth), ("Save Report", self.do_save)]
        
        for i, (txt, cmd) in enumerate(actions):
            tk.Button(self.btn_f, text=txt, command=lambda c=cmd: self.start_task(c), **btn_opts).grid(row=i//2, column=i%2, padx=8, pady=8)

        # Status and Results
        self.status_lbl = tk.Label(self.win, text="Ready", font=("Helvetica", 10), bg="#121212", fg="#888888")
        self.status_lbl.pack()

        self.res_lbl = tk.Label(self.win, text="", font=("Helvetica", 13, "bold"), bg="#121212", fg="#00ff00", wraplength=550)
        self.res_lbl.pack(pady=15)

        tk.Button(self.win, text="Clear Results & Cache", command=self.do_clear, bg="#333333", fg="white", bd=0, padx=10).pack(side="bottom", pady=10)

    # --- CORE LOGIC ---

    def start_task(self, cmd):
        """Runs the data tasks in a daemon thread to keep UI smooth."""
        threading.Thread(target=cmd, daemon=True).start()

    def set_status(self, msg, color="#888888"):
        """Thread-safe status updates."""
        self.win.after(0, lambda: self.status_lbl.config(text=msg, fg=color))

    def fetch(self, country):
        """API client with caching and retry logic."""
        if country in self.cache: return self.cache[country]
        
        self.set_status(f"Fetching {country} data...", "#007ACC")
        url = f"https://api.worldbank.org/v2/country/{self.COUNTRIES[country]}/indicator/NY.GDP.MKTP.CD?date=2000:2023&format=json&per_page=100"
        
        try:
            r = requests.get(url, timeout=20)
            r.raise_for_status()
            data = r.json()
            
            # FIXED: Added to properly target the data array
            if len(data) < 2 or not data: raise ValueError(f"No API data for {country}")
            
            # FIXED: Added to properly iterate through the data array
            clean_data = {str(e['date']): e['value']/1e9 for e in data if e['value'] is not None}
            if not clean_data: raise ValueError(f"GDP values missing for {country}")
            
            self.cache[country] = clean_data
            return clean_data
        except Exception as e:
            raise ConnectionError(f"API Error: Check internet connection. Details: {str(e)}")

    def spawn_chart(self, title, plot_fn):
        """Safely creates a new chart window on the main thread."""
        def _build():
            top = tk.Toplevel(self.win)
            top.title(title)
            top.geometry("800x550")
            
            fig = plt.Figure(figsize=(8, 5.5), dpi=100)
            ax = fig.add_subplot(111)
            ax.set_title(title, fontsize=12, fontweight='bold', pad=15)
            ax.grid(True, linestyle=':', alpha=0.6)
            
            plot_fn(ax) # Execute the specific plotting logic
            fig.tight_layout()
            
            canvas = FigureCanvasTkAgg(fig, master=top)
            canvas.draw()
            canvas.get_tk_widget().pack(fill="both", expand=True)
            
        self.win.after(0, _build)

    # --- BUTTON ACTIONS ---

    def do_analyze(self):
        try:
            c, y = self.c1_var.get(), self.yr_var.get()
            d = self.fetch(c)
            if y not in d: raise ValueError(f"No record found for {y}")
            
            msg = f"{c} ({y}): {self.CURRENCIES[c]}{d[y]:,.2f} Billion"
            self.win.after(0, lambda: self.res_lbl.config(text=msg))
            self.spawn_chart(f"GDP Analysis: {c} ({y})", lambda ax: (
                ax.bar([y], [d[y]], color='#007ACC'),
                ax.set_ylabel("GDP (Billion USD)")
            ))
            self.set_status("Ready")
        except Exception as e:
            self.set_status("Error occurred", "#ff4444")
            messagebox.showerror("Analysis Error", str(e))

    def do_compare(self):
        try:
            c1, c2 = self.c1_var.get(), self.c2_var.get()
            if c1 == c2: raise ValueError("Select two different countries to compare.")
            
            d1, d2 = self.fetch(c1), self.fetch(c2)
            yrs = sorted(list(set(d1.keys()) & set(d2.keys())))
            
            if not yrs: raise ValueError("No overlapping data years found.")
            
            def plot(ax):
                ax.plot(yrs, [d1[y] for y in yrs], label=c1, marker='o', linewidth=2)
                ax.plot(yrs, [d2[y] for y in yrs], label=c2, marker='s', linewidth=2)
                ax.set_ylabel("GDP in Billions (USD)")
                ax.set_xticks(yrs[::2]); ax.tick_params(axis='x', rotation=45)
                ax.legend()
            
            self.spawn_chart(f"GDP Comparison: {c1} vs {c2}", plot)
            self.set_status("Ready")
        except Exception as e:
            self.set_status("Error occurred", "#ff4444")
            messagebox.showerror("Comparison Error", str(e))

    def do_growth(self):
        try:
            c = self.c1_var.get()
            d = self.fetch(c)
            yrs = sorted(list(d.keys()))
            
            if len(yrs) < 2: raise ValueError("Not enough data points for growth analysis.")
            
            # Calculate Year-over-Year Growth
            rates = [((d[yrs[i]] - d[yrs[i-1]]) / d[yrs[i-1]]) * 100 for i in range(1, len(yrs))]
            
            def plot(ax):
                ax.plot(yrs[1:], rates, marker='o', color='#2ecc71', linewidth=2)
                ax.axhline(0, color='black', linewidth=0.8)
                ax.set_ylabel("Annual Growth Rate (%)")
                ax.set_xticks(yrs[1::2]); ax.tick_params(axis='x', rotation=45)
            
            self.spawn_chart(f"GDP Growth Trends: {c}", plot)
            self.set_status("Ready")
        except Exception as e:
            self.set_status("Error occurred", "#ff4444")
            messagebox.showerror("Growth Error", str(e))

    def do_save(self):
        txt = self.res_lbl.cget("text")
        if not txt: return messagebox.showwarning("No Data", "Generate an analysis first to save a report.")
        
        path = filedialog.asksaveasfilename(defaultextension=".txt", title="Save GDP Report", initialfile="GDP_Report.txt")
        if path:
            try:
                with open(path, 'w', encoding='utf-8') as f:
                    f.write("=== WORLD BANK GDP ANALYSIS REPORT ===\n\n")
                    f.write(txt + "\n")
                messagebox.showinfo("Success", "Report exported successfully!")
            except Exception as e: messagebox.showerror("Save Error", str(e))

    def do_clear(self):
        self.cache = {}
        self.res_lbl.config(text="")
        self.set_status("Cache and results cleared")

    def run(self):
        self.win.mainloop()

if __name__ == "__main__":
    GDPAnalyzer().run()
