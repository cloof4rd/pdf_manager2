import tkinter as tk
from tkinter import simpledialog, messagebox, filedialog
import json
import re
from pathlib import Path
from PyPDF2 import PdfMerger

CONFIG = "priority_config.json"
NUMBER_RE = re.compile(r"(\d+)")

def ask_multiline(title, prompt, example, parent):
    dlg = tk.Toplevel(parent)
    dlg.title(title)
    tk.Label(dlg, text=prompt).pack(fill=tk.X, padx=10, pady=5)
    tk.Label(dlg, text="Example:\n" + example, fg="gray").pack(fill=tk.X, padx=10, pady=(0,5))
    text = tk.Text(dlg, height=6, wrap="none")
    text.pack(fill=tk.BOTH, expand=True, padx=10)
    result = {}
    def on_ok():
        result['value'] = text.get("1.0", "end").strip()
        dlg.destroy()
    tk.Button(dlg, text="OK", command=on_ok).pack(pady=5)
    dlg.transient(parent)
    dlg.grab_set()
    parent.wait_window(dlg)
    return result.get('value', "")

def save_config(batch_order, keyword_order, numeric_sort="asc"):
    with open(CONFIG, "w") as f:
        json.dump({
            "batch_order":   batch_order,
            "keyword_order": keyword_order,
            "numeric_sort":  numeric_sort
        }, f, indent=2)
    messagebox.showinfo("Saved", "Configuration saved!")

def make_sort_key(batch_order, keyword_order, numeric_sort):
    prefix_map = {}
    numeric_map = {}
    for i, b in enumerate(batch_order):
        if b.isdigit():
            numeric_map[b] = i
        else:
            prefix_map[b] = i
    kw_index = {k: i for i, k in enumerate(keyword_order)}

    def key(path: Path):
        stem = path.stem
        parts = stem.split("_", 1)
        batch = parts[0]
        rest  = parts[1] if len(parts) > 1 else ""

        if batch in prefix_map:
            bpos = prefix_map[batch]
        else:
            m = NUMBER_RE.search(batch)
            num = m.group(1) if m else None
            bpos = numeric_map.get(num, len(batch_order))

        kpos = next((kw_index[k] for k in keyword_order if k in rest),
                    len(keyword_order))

        m2 = NUMBER_RE.search(stem)
        num2 = int(m2.group(1)) if m2 else 0
        nval = num2 if numeric_sort == "asc" else -num2

        return (bpos, kpos, nval, stem.lower())

    return key

class PDFManagerGUI(tk.Frame):
    def __init__(self, master):
        super().__init__(master)
        self.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        self.numeric_sort = "asc"

        # Prompt for batch order
        batch_input = ask_multiline(
            "Batch Order",
            "Enter batch prefixes (comma- or newline-separated)",
            "YAX69,YAX420\nor\nYAX69\nYAX420",
            master
        )
        if batch_input:
            self.batch_order = [
                s.strip()
                for s in re.split(r"[,\n]+", batch_input)
                if s.strip()
            ]
        else:
            self.batch_order = []

        # Prompt for keyword priority
        keyword_input = ask_multiline(
            "Keyword Priority",
            "Enter keywords (comma- or newline-separated)",
            "TAM,MY\nor\nTAM\nMY",
            master
        )
        if keyword_input:
            self.keyword_order = [
                s.strip()
                for s in re.split(r"[,\n]+", keyword_input)
                if s.strip()
            ]
        else:
            self.keyword_order = []

        self.selected_files = []

        # Batch Order Editor
        bf = tk.LabelFrame(self, text="Batch Order", padx=5, pady=5)
        bf.pack(fill=tk.X, pady=5)
        self.lb_batch = tk.Listbox(bf, height=5)
        self.lb_batch.pack(side=tk.LEFT, fill=tk.X, expand=True)
        btns_b = tk.Frame(bf); btns_b.pack(side=tk.RIGHT, padx=5)
        for txt, cmd in [("Add", self._add_batch),
                         ("Delete", self._rm_batch),
                         ("Up", self._up_batch),
                         ("Down", self._dn_batch)]:
            b = tk.Button(btns_b, text=txt, width=8, command=cmd)
            b.pack(pady=2)
        self._refresh(self.lb_batch, self.batch_order)

        # Keyword Priority Editor
        kf = tk.LabelFrame(self, text="Keyword Priority", padx=5, pady=5)
        kf.pack(fill=tk.X, pady=5)
        self.lb_key = tk.Listbox(kf, height=5)
        self.lb_key.pack(side=tk.LEFT, fill=tk.X, expand=True)
        btns_k = tk.Frame(kf); btns_k.pack(side=tk.RIGHT, padx=5)
        for txt, cmd in [("Add", self._add_key),
                         ("Delete", self._rm_key),
                         ("Up", self._up_key),
                         ("Down", self._dn_key)]:
            b = tk.Button(btns_k, text=txt, width=8, command=cmd)
            b.pack(pady=2)
        self._refresh(self.lb_key, self.keyword_order)

        # File List & Merge
        ff = tk.LabelFrame(self, text="Merge PDFs", padx=5, pady=5)
        ff.pack(fill=tk.BOTH, expand=True, pady=5)
        self.lb_files = tk.Listbox(ff, height=8)
        self.lb_files.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        fb = tk.Frame(ff); fb.pack(side=tk.RIGHT, padx=5, fill=tk.Y)
        tk.Button(fb, text="Select PDFs…", width=12, command=self._pick_files).pack(pady=5)
        tk.Button(fb, text="Save Config", width=12,
                  command=lambda: save_config(self.batch_order, self.keyword_order, self.numeric_sort)
        ).pack(pady=5)
        tk.Button(fb, text="Merge PDFs", width=12, command=self._merge).pack(pady=5)

    def _refresh(self, lb, items):
        lb.delete(0, tk.END)
        for it in items:
            lb.insert(tk.END, it)

    # Batch handlers
    def _add_batch(self):
        s = simpledialog.askstring("Add batch", "Enter new batch prefix:")
        if s:
            self.batch_order.append(s.strip())
            self._refresh(self.lb_batch, self.batch_order)

    def _rm_batch(self):
        sel = self.lb_batch.curselection()
        if sel:
            self.batch_order.pop(sel[0])
            self._refresh(self.lb_batch, self.batch_order)

    def _up_batch(self):
        sel = self.lb_batch.curselection()
        if sel and sel[0] > 0:
            i = sel[0]
            self.batch_order[i-1], self.batch_order[i] = (
                self.batch_order[i], self.batch_order[i-1]
            )
            self._refresh(self.lb_batch, self.batch_order)
            self.lb_batch.select_set(i-1)

    def _dn_batch(self):
        sel = self.lb_batch.curselection()
        if sel and sel[0] < len(self.batch_order)-1:
            i = sel[0]
            self.batch_order[i+1], self.batch_order[i] = (
                self.batch_order[i], self.batch_order[i+1]
            )
            self._refresh(self.lb_batch, self.batch_order)
            self.lb_batch.select_set(i+1)

    # Keyword handlers
    def _add_key(self):
        s = simpledialog.askstring("Add keyword", "Enter new keyword:")
        if s:
            self.keyword_order.append(s.strip())
            self._refresh(self.lb_key, self.keyword_order)

    def _rm_key(self):
        sel = self.lb_key.curselection()
        if sel:
            self.keyword_order.pop(sel[0])
            self._refresh(self.lb_key, self.keyword_order)

    def _up_key(self):
        sel = self.lb_key.curselection()
        if sel and sel[0] > 0:
            i = sel[0]
            self.keyword_order[i-1], self.keyword_order[i] = (
                self.keyword_order[i], self.keyword_order[i-1]
            )
            self._refresh(self.lb_key, self.keyword_order)
            self.lb_key.select_set(i-1)

    def _dn_key(self):
        sel = self.lb_key.curselection()
        if sel and sel[0] < len(self.keyword_order)-1:
            i = sel[0]
            self.keyword_order[i+1], self.keyword_order[i] = (
                self.keyword_order[i], self.keyword_order[i+1]
            )
            self._refresh(self.lb_key, self.keyword_order)
            self.lb_key.select_set(i+1)

    # File selection & merge
    def _pick_files(self):
        files = filedialog.askopenfilenames(
            title="Select PDF files", filetypes=[("PDFs", "*.pdf")]
        )
        for f in files:
            p = Path(f)
            if p not in self.selected_files:
                self.selected_files.append(p)
        sorted_files = sorted(
            self.selected_files,
            key=make_sort_key(self.batch_order, self.keyword_order, self.numeric_sort)
        )
        self._refresh(self.lb_files, [p.name for p in sorted_files])

    def _merge(self):
        if not self.selected_files:
            return messagebox.showwarning("No files", "Select PDFs first")
        out = filedialog.asksaveasfilename(
            defaultextension=".pdf", filetypes=[("PDF","*.pdf")]
        )
        if not out:
            return
        merger = PdfMerger()
        for p in sorted(
            self.selected_files,
            key=make_sort_key(self.batch_order, self.keyword_order, self.numeric_sort)
        ):
            merger.append(str(p))
        merger.write(out)
        merger.close()
        messagebox.showinfo("Done", f"Merged {len(self.selected_files)} files")

if __name__ == "__main__":
    root = tk.Tk()
    root.title("PDF Manager 2: Dynamic Batch & Keyword Sort")
    PDFManagerGUI(root)
    root.mainloop()
