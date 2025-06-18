import tkinter as tk
from tkinter import simpledialog, messagebox, filedialog
import re
from pathlib import Path
from PyPDF2 import PdfMerger

NUMBER_RE = re.compile(r"(\d+)")

def ask_multiline(title, prompt, example, parent):
    dlg = tk.Toplevel(parent)
    dlg.title(title)
    tk.Label(dlg, text=prompt, justify="left").pack(fill=tk.X, padx=10, pady=(10,2))
    tk.Label(dlg, text=example, justify="left", fg="gray").pack(fill=tk.X, padx=10, pady=(0,5))
    txt = tk.Text(dlg, height=6, wrap="none")
    txt.pack(fill=tk.BOTH, expand=True, padx=10)
    result = {}
    def on_ok():
        result['value'] = txt.get("1.0", "end").strip()
        dlg.destroy()
    tk.Button(dlg, text="OK", command=on_ok).pack(pady=5)
    dlg.transient(parent); dlg.grab_set()
    parent.wait_window(dlg)
    return result.get('value', "")

def make_sort_key(batch_order, keyword_order, numeric_sort="asc"):
    prefix_map  = {b:i for i,b in enumerate(batch_order)}
    numeric_map = {b:i for i,b in enumerate(batch_order) if b.isdigit()}
    kw_index    = {k:i for i,k in enumerate(keyword_order)}

    def key(path: Path):
        stem = path.stem
        batch, rest = (stem.split("_",1) + [""])[:2]

        # batch position
        if batch in prefix_map:
            bpos = prefix_map[batch]
        else:
            m = NUMBER_RE.search(batch)
            num = m.group(1) if m else None
            bpos = numeric_map.get(num, len(batch_order))

        # keyword position
        kpos = next((kw_index[k] for k in keyword_order
                     if k.lower() in rest.lower()),
                    len(keyword_order))

        # numeric sub-sort
        m2 = NUMBER_RE.search(stem)
        nval = int(m2.group(1)) if m2 else 0
        if numeric_sort == "desc":
            nval = -nval

        return (bpos, kpos, nval, stem.lower())

    return key

class PDFManagerGUI(tk.Frame):
    def __init__(self, master):
        super().__init__(master)
        self.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        self.numeric_sort = "asc"
        self.selected_files = []

        # --- Prompt for Batch Order & Keyword Priority (with examples) ---
        btxt = ask_multiline(
            "Batch Order",
            "Enter batch prefixes (comma- or newline-separated):",
            "For example:\nYAX69,YAX420 \nor  \nYAX69\nYAX420",
            master
        )
        self.batch_order   = [s.strip() for s in re.split(r"[,\n]+", btxt) if s.strip()]

        ktxt = ask_multiline(
            "Keyword Priority",
            "Enter keywords (comma- or newline-separated):",
            "For example:\nTAM,MY  \nor  \nTAM\nMY",
            master
        )
        self.keyword_order = [s.strip() for s in re.split(r"[,\n]+", ktxt) if s.strip()]

        # --- Batch Editor ---
        bf = tk.LabelFrame(self, text="Batch Order", padx=5, pady=5)
        bf.pack(fill=tk.X, pady=5)
        self.lb_batch = tk.Listbox(bf, height=4)
        self.lb_batch.pack(side=tk.LEFT, fill=tk.X, expand=True)
        pb = tk.Frame(bf); pb.pack(side=tk.RIGHT, padx=5)
        for txt, cmd in [("Add", self._add_batch),
                         ("Delete", self._rm_batch),
                         ("Up", self._up_batch),
                         ("Down", self._dn_batch)]:
            tk.Button(pb, text=txt, width=6, command=cmd).pack(pady=2)
        self._refresh(self.lb_batch, self.batch_order)

        # --- Keyword Editor ---
        kf = tk.LabelFrame(self, text="Keyword Priority", padx=5, pady=5)
        kf.pack(fill=tk.X, pady=5)
        self.lb_key = tk.Listbox(kf, height=4)
        self.lb_key.pack(side=tk.LEFT, fill=tk.X, expand=True)
        pk = tk.Frame(kf); pk.pack(side=tk.RIGHT, padx=5)
        for txt, cmd in [("Add", self._add_key),
                         ("Delete", self._rm_key),
                         ("Up", self._up_key),
                         ("Down", self._dn_key)]:
            tk.Button(pk, text=txt, width=6, command=cmd).pack(pady=2)
        self._refresh(self.lb_key, self.keyword_order)

        # --- Merge PDFs & Manual Controls ---
        mf = tk.LabelFrame(self, text="Merge PDFs", padx=5, pady=5)
        mf.pack(fill=tk.BOTH, expand=True, pady=5)
        self.lb_files = tk.Listbox(mf, height=8)
        self.lb_files.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        pf = tk.Frame(mf); pf.pack(side=tk.RIGHT, padx=5, fill=tk.Y)

        tk.Button(pf, text="Select PDFs…", width=12, command=self._pick_files).pack(pady=4)
        tk.Button(pf, text="Add File…",    width=12, command=self._add_file).pack(pady=4)
        tk.Button(pf, text="Delete File",  width=12, command=self._rm_file).pack(pady=4)
        tk.Button(pf, text="Move Up",      width=12, command=self._up_file).pack(pady=4)
        tk.Button(pf, text="Move Down",    width=12, command=self._dn_file).pack(pady=4)
        tk.Button(pf, text="Merge PDFs",   width=12, command=self._merge).pack(pady=6)

    def _refresh(self, lb, items):
        lb.delete(0, tk.END)
        for it in items:
            lb.insert(tk.END, it)

    # --- Batch handlers ---
    def _add_batch(self):
        s = simpledialog.askstring("Add batch", "Batch prefix:")
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
            self.batch_order[i-1], self.batch_order[i] = self.batch_order[i], self.batch_order[i-1]
            self._refresh(self.lb_batch, self.batch_order)
            self.lb_batch.select_set(i-1)

    def _dn_batch(self):
        sel = self.lb_batch.curselection()
        if sel and sel[0] < len(self.batch_order)-1:
            i = sel[0]
            self.batch_order[i+1], self.batch_order[i] = self.batch_order[i], self.batch_order[i+1]
            self._refresh(self.lb_batch, self.batch_order)
            self.lb_batch.select_set(i+1)

    # --- Keyword handlers ---
    def _add_key(self):
        s = simpledialog.askstring("Add keyword", "Keyword:")
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
            self.keyword_order[i-1], self.keyword_order[i] = self.keyword_order[i], self.keyword_order[i-1]
            self._refresh(self.lb_key, self.keyword_order)
            self.lb_key.select_set(i-1)

    def _dn_key(self):
        sel = self.lb_key.curselection()
        if sel and sel[0] < len(self.keyword_order)-1:
            i = sel[0]
            self.keyword_order[i+1], self.keyword_order[i] = self.keyword_order[i], self.keyword_order[i+1]
            self._refresh(self.lb_key, self.keyword_order)
            self.lb_key.select_set(i+1)

    # --- File selection & manual edits ---
    def _pick_files(self):
        files = filedialog.askopenfilenames(title="Select PDFs", filetypes=[("PDFs","*.pdf")])
        for f in files:
            p = Path(f)
            if p not in self.selected_files:
                self.selected_files.append(p)
        # **restore auto-sorting on load**
        self.selected_files.sort(key=make_sort_key(
            self.batch_order, self.keyword_order, self.numeric_sort))
        self._refresh_file_list()

    def _add_file(self):
        f = filedialog.askopenfilename(title="Add single PDF", filetypes=[("PDF","*.pdf")])
        if f:
            p = Path(f)
            if p not in self.selected_files:
                self.selected_files.append(p)
        self._refresh_file_list()

    def _rm_file(self):
        sel = self.lb_files.curselection()
        if sel:
            self.selected_files.pop(sel[0])
        self._refresh_file_list()

    def _up_file(self):
        sel = self.lb_files.curselection()
        if sel and sel[0] > 0:
            i = sel[0]
            self.selected_files[i-1], self.selected_files[i] = \
                self.selected_files[i], self.selected_files[i-1]
            self._refresh_file_list()
            self.lb_files.select_set(i-1)

    def _dn_file(self):
        sel = self.lb_files.curselection()
        if sel and sel[0] < len(self.selected_files)-1:
            i = sel[0]
            self.selected_files[i+1], self.selected_files[i] = \
                self.selected_files[i], self.selected_files[i+1]
            self._refresh_file_list()
            self.lb_files.select_set(i+1)

    def _refresh_file_list(self):
        self.lb_files.delete(0, tk.END)
        for p in self.selected_files:
            self.lb_files.insert(tk.END, p.name)

    # --- Final merge ---
    def _merge(self):
        if not self.selected_files:
            return messagebox.showwarning("No files", "Select PDFs first")
        out = filedialog.asksaveasfilename(defaultextension=".pdf",
                                           filetypes=[("PDF","*.pdf")])
        if not out:
            return
        merger = PdfMerger()
        for p in self.selected_files:
            merger.append(str(p))
        merger.write(out)
        merger.close()
        messagebox.showinfo("Done", f"Merged {len(self.selected_files)} files")

if __name__ == "__main__":
    root = tk.Tk()
    root.title("PDF Manager 2: Dynamic Batch & Keyword Sort")
    PDFManagerGUI(root)
    root.mainloop()
