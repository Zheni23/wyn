import tkinter as tk
from tkinter import colorchooser, ttk
import threading, time, json, os, re
from PIL import ImageGrab, Image, ImageTk
import pytesseract
import cv2
import numpy as np
import ctypes

# ================= SETTINGS =================
SETTINGS_FILE = "settings.json"
default_settings = {
    "bg_color": "#0a0a0c",
    "topbar_color": "#121217",
    "text_color": "#87ceeb",
    "yes_color": "#00ff9f",
    "no_color": "#ff0055",
    "both_color": "#87ceeb",
}

if os.path.exists(SETTINGS_FILE):
    with open(SETTINGS_FILE, "r") as f:
        settings = json.load(f)
else:
    settings = default_settings.copy()

def save_settings():
    with open(SETTINGS_FILE, "w") as f:
        json.dump(settings, f)

def reset_theme():
    global settings
    settings = default_settings.copy()
    save_settings()
    update_ui_colors()

# ================= OCR =================
pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
OCR_CONFIG = "--oem 3 --psm 6"

# ================= GLOBALS =================
wallets = {}
last_text = None
last_key = None
running = False
app_hidden = False
vote_index = 0  


BOX_WIDTH, BOX_HEIGHT = 180, 45
split_mode = "vertical"
split_ratio = 0.65
mouse_mode = None
catcher_icon = None
ICON_SIZE = 32
sort_mode = "most"
btn_style = {"relief": "flat", "font": ("Segoe UI", 9, "bold"), "bd": 0, "cursor": "hand2"}

# ================= OCR HELPERS =================
def preprocess(img):
    img = np.array(img)
    g = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    g = cv2.resize(g, None, fx=1.5, fy=1.5)
    _, g = cv2.threshold(g, 160, 255, cv2.THRESH_BINARY)
    return g

def parse_line(clean):
    clean = clean.strip()
    if not clean:
        return None
    m = re.search(r'([SO])\s*$', clean, re.I)
    if not m:
        return None
    vote = "YES" if m.group(1).upper() == "S" else "NO"
    wallet_raw = re.sub(r'\s*[SO]\s*$', '', clean)
    wallet_raw = re.sub(r'\s+', '', wallet_raw)
    wallet = wallet_raw.strip()[:6]
    return wallet, vote

# ================= FUZZY WALLET MATCH =================
def is_same_wallet(a, b):
    """
    Compare first 4 characters of wallets.
    Return True if they differ by at most 1 character.
    """
    a, b = a[:4], b[:4]
    if len(a) != 4 or len(b) != 4:
        return False
    diff_count = sum(1 for x, y in zip(a, b) if x != y)
    return diff_count <= 1


def find_existing_wallet(wallet):
    """
    Find a wallet in wallets dict that matches fuzzily.
    If none matches, return None.
    """
    for w in wallets:
        if is_same_wallet(w, wallet):
            return w
    return None


# ================= OCR LOOP =================
def ocr_loop():
    global wallets, last_text, last_key, vote_index
    while running:
        try:
            x, y = catcher.winfo_x(), catcher.winfo_y()
            w, h = BOX_WIDTH, BOX_HEIGHT
            if split_mode == "horizontal":
                sp = int(h * split_ratio)
                imgA = preprocess(ImageGrab.grab((x, y, x+w, y+sp)))
                imgB = preprocess(ImageGrab.grab((x, y+sp, x+w, y+h)))
            else:
                sp = int(w * split_ratio)
                imgA = preprocess(ImageGrab.grab((x, y, x+sp, y+h)))
                imgB = preprocess(ImageGrab.grab((x+sp, y, x+w, y+h)))

            textA = pytesseract.image_to_string(imgA, config=OCR_CONFIG).strip()
            textB = pytesseract.image_to_string(imgB, config=OCR_CONFIG).strip()
            parsed = parse_line(f"{textA} {textB}")

            if parsed:
                wallet, vote = parsed

                # Check for existing similar wallet
                existing = find_existing_wallet(wallet)
                if existing:
                    wallet = existing  # merge into the existing wallet

                wallets.setdefault(wallet, {"YES": 0, "NO": 0, "Y&N": 0, "last_index": 0})
                key = f"{wallet}|{vote}"
                if key != last_key:
                    wallets[wallet][vote] += 1
                    wallets[wallet]["Y&N"] = min(wallets[wallet]["YES"], wallets[wallet]["NO"])
                    vote_index += 1
                    wallets[wallet]["last_index"] = vote_index  # store counter
                    last_key = key
                    update_results()

            time.sleep(0.2)
        except Exception:
            time.sleep(0.2)


# ================= CONTROL =================
def start_counter():
    global running, wallets, last_text, last_key
    wallets, last_text, last_key = {}, None, None
    update_results()
    if not running:
        running = True
        threading.Thread(target=ocr_loop, daemon=True).start()

def reset_counts():
    global wallets, last_text, last_key
    wallets, last_text, last_key = {}, None, None
    update_results()

def pause_counter():
    global running
    running = False

def toggle_sort():
    global sort_mode
    sort_mode = "new" if sort_mode == "most" else "most"
    update_results()

def toggle_split():
    global split_mode
    split_mode = "vertical" if split_mode == "horizontal" else "horizontal"
    redraw()

# ================= UI UPDATES =================
def update_results():
    results.delete("1.0", tk.END)
    
    # Header
    header = f"{'WHAA':^7}{'YES':^11}{'NO':^6}{'Y&N':^9}\n"
    results.insert(tk.END, header, "header")
    results.insert(tk.END, "\n", "spacer")

    # Prepare items
    items = list(wallets.items())
    if sort_mode == "most":
        items.sort(key=lambda x: (x[1]["YES"] + x[1]["NO"]), reverse=True)
    elif sort_mode == "new":
        items.sort(key=lambda x: x[1].get("last_index", 0), reverse=True)  # <-- use counter

    # Insert each wallet row
    for w, v in items:
        results.insert(tk.END, f"{w:^8}", "wallet")
        results.insert(tk.END, f"{v['YES']:^8}", "yes")
        results.insert(tk.END, f"{v['NO']:^7}", "no")
        results.insert(tk.END, f"{v['Y&N']:^7}\n", "both")

    # Tag config
    results.tag_config("header", foreground=settings["text_color"], font=("Consolas", 10, "bold"))
    results.tag_config("spacer", font=("Consolas", 2))
    results.tag_config("wallet", foreground="#666666", font=("Consolas", 9))
    results.tag_config("yes", foreground=settings["yes_color"], font=("Consolas", 11, "bold"))
    results.tag_config("no", foreground=settings["no_color"], font=("Consolas", 11, "bold"))
    results.tag_config("both", foreground=settings["both_color"], font=("Consolas", 11, "bold"))
def update_ui_colors():
    app.configure(bg=settings["bg_color"])
    top.configure(bg=settings["topbar_color"])
    ctrl.configure(bg=settings["bg_color"])
    results.configure(bg=settings["bg_color"], fg=settings["text_color"], font=("Consolas", 11))
    for w in top.winfo_children():
        w.configure(bg=settings["topbar_color"], fg=settings["text_color"])
    update_results()

def choose_color(key):
    c = colorchooser.askcolor()[1]
    if c:
        settings[key] = c
        save_settings()
        update_ui_colors()

def open_settings():
    win = tk.Toplevel(app)
    win.configure(bg=settings["bg_color"])
    win.geometry("320x350+150+150")
    bar = tk.Frame(win, bg=settings["topbar_color"], height=34)
    bar.pack(fill="x")
    tk.Label(bar, text="Settings", bg=settings["topbar_color"], fg=settings["text_color"]).pack(side="left", padx=10)
    tk.Button(bar, text="X", command=win.destroy, bg=settings["topbar_color"], fg=settings["text_color"], bd=0).pack(side="right", padx=10)
    
    body = tk.Frame(win, bg=settings["bg_color"])
    body.pack(fill="both", expand=True, padx=10, pady=10)
    def add(lbl, key):
        row = tk.Frame(body, bg=settings["bg_color"])
        row.pack(fill="x", pady=6)
        tk.Label(row, text=lbl, fg=settings["text_color"], bg=settings["bg_color"], width=12, anchor="w").pack(side="left")
        tk.Button(row, text="Change", command=lambda: choose_color(key)).pack(side="right")
    for l, k in [("Background","bg_color"), ("Top Bar","topbar_color"), ("Text","text_color"), ("YES","yes_color"), ("NO","no_color"), ("Y&N","both_color")]:
        add(l, k)

def close_app():
    global running
    running = False
    root.destroy()

# ================= APP SETUP =================
class PillButton(tk.Canvas):
    def __init__(self, parent, text, color, command):
        super().__init__(parent, width=65, height=30, bg=settings["bg_color"], highlightthickness=0, cursor="hand2")
        self.command = command
        self.create_rounded_rect(2, 2, 63, 28, 10, fill=color)
        self.create_text(32, 15, text=text, fill="#000000" if color != "#ff0055" else "#ffffff", font=("Segoe UI", 8, "bold"))
        self.bind("<Button-1>", lambda e: self.command())
    def create_rounded_rect(self, x1, y1, x2, y2, r, **kwargs):
        points = [x1+r, y1, x1+r, y1, x2-r, y1, x2-r, y1, x2, y1, x2, y1+r, x2, y1+r, x2, y2-r, x2, y2-r, x2, y2, x2-r, y2, x2-r, y2, x1+r, y2, x1+r, y2, x1, y2, x1, y2-r, x1, y2-r, x1, y1+r, x1, y1+r, x1, y1]
        return self.create_polygon(points, **kwargs, smooth=True)

# ================= MAIN UI =================
root = tk.Tk()
root.title("WYN counter")
root.geometry("0x0+0+0")
root.attributes("-alpha", 0.0)
root.bind("<Map>", lambda e: restore_app())

try:
    icon_pil = Image.open("icon.png").resize((ICON_SIZE, ICON_SIZE), Image.LANCZOS)
    icon_img = ImageTk.PhotoImage(icon_pil)
    root.iconphoto(True, icon_img)
except:
    icon_img = None

app = tk.Toplevel(root)
app.overrideredirect(True)
app.geometry("350x420+100+100")
app.configure(bg=settings["bg_color"])

top = tk.Frame(app, bg=settings["topbar_color"], height=40)
top.pack(fill="x")
def sm(e): app._ox, app._oy = e.x, e.y
def mv(e): app.geometry(f"+{e.x_root-app._ox}+{e.y_root-app._oy}")
top.bind("<Button-1>", sm); top.bind("<B1-Motion>", mv)

tk.Label(top, image=icon_img, bg=settings["topbar_color"]).pack(side="left", padx=(10, 6))
tk.Label(top, text="WYN counter", fg=settings["text_color"], bg=settings["topbar_color"], font=("Segoe UI", 13, "bold")).pack(side="left")
tk.Button(top, text="X", command=close_app, bg=settings["topbar_color"], fg=settings["text_color"], bd=0).pack(side="right", padx=10)
tk.Button(top, text="_", command=lambda: minimize_app(), bg=settings["topbar_color"], fg=settings["text_color"], bd=0, width=3).pack(side="right")
tk.Button(top, text="*", command=open_settings, bg=settings["topbar_color"], fg=settings["text_color"], bd=0).pack(side="right", padx=5)

ctrl = tk.Frame(app, bg=settings["bg_color"])
ctrl.pack(side="left", fill="y", padx=10, pady=(100, 0))

PillButton(ctrl, "Start", "#00ff9f", start_counter).pack(pady=4)
PillButton(ctrl, "Pause", "#ffcc00", pause_counter).pack(pady=4)
PillButton(ctrl, "Reset", "#ff0055", reset_counts).pack(pady=4)
PillButton(ctrl, "Sort", "#00d4ff", toggle_sort).pack(pady=4)
PillButton(ctrl, "Axis", "#87ceeb", toggle_split).pack(pady=4)

style = ttk.Style()
style.theme_use('clam')
style.configure("Vertical.TScrollbar", gripcount=0, background="#1a1a22", darkcolor="#1a1a1a", lightcolor="#1a1a1a", troughcolor="#0a0a0c", bordercolor="#0a0a0c", arrowcolor="#9b9bad")

scroll = ttk.Scrollbar(app, orient="vertical", style="Vertical.TScrollbar")
scroll.pack(side="right", fill="y")

results = tk.Text(app, font=("Consolas", 11), bg=settings["bg_color"], fg=settings["text_color"],
                 yscrollcommand=scroll.set, bd=0, padx=10, pady=10, highlightthickness=0,
                 selectbackground="#333333", wrap="none")
results.pack(fill="both", expand=True, padx=5, pady=5)
scroll.config(command=results.yview)

# ================= CATCHER =================
catcher = tk.Toplevel(app)
catcher.overrideredirect(True)
catcher.attributes("-topmost", True, "-alpha", 0.35)
catcher.geometry(f"{BOX_WIDTH}x{BOX_HEIGHT}+400+200")

catcher_icon = tk.Toplevel(app)
catcher_icon.overrideredirect(True)
catcher_icon.withdraw()
catcher_icon.geometry(f"{ICON_SIZE}x{ICON_SIZE}")
try:
    icon_lbl = tk.Label(catcher_icon, image=icon_img, bg="#000000")
    icon_lbl.pack()
    icon_lbl.bind("<Button-1>", lambda e: restore_app())
except:
    pass

canvas = tk.Canvas(catcher, highlightthickness=3, highlightbackground="red")
canvas.pack(fill="both", expand=True)

def minimize_app():
    app.withdraw()
    root.iconify()
    catcher_icon.deiconify()
    position_icon()

def restore_app():
    app.deiconify()
    root.deiconify()
    root.state('normal')
    catcher_icon.withdraw()

def position_icon():
    catcher_icon.geometry(f"+{catcher.winfo_x() + BOX_WIDTH + 4}+{catcher.winfo_y()}")

def redraw():
    canvas.delete("all")
    pos = int((BOX_HEIGHT if split_mode == "horizontal" else BOX_WIDTH) * split_ratio)
    if split_mode == "horizontal":
        canvas.create_line(0, pos, BOX_WIDTH, pos, fill="yellow", width=2)
    else:
        canvas.create_line(pos, 0, pos, BOX_HEIGHT, fill="yellow", width=2)
    canvas.create_rectangle(BOX_WIDTH-10, BOX_HEIGHT-10, BOX_WIDTH, BOX_HEIGHT, fill="red")

def press(e):
    global mouse_mode
    pos = int((BOX_HEIGHT if split_mode=="horizontal" else BOX_WIDTH) * split_ratio)
    if e.x >= BOX_WIDTH-12 and e.y >= BOX_HEIGHT-12:
        mouse_mode = "resize"
    elif abs((e.y if split_mode=="horizontal" else e.x) - pos) <= 5:
        mouse_mode = "split"
    else:
        mouse_mode = "move"
        catcher._mx, catcher._my = e.x_root, e.y_root

def drag(e):
    global BOX_WIDTH, BOX_HEIGHT, split_ratio
    if mouse_mode == "move":
        dx, dy = e.x_root-catcher._mx, e.y_root-catcher._my
        catcher.geometry(f"+{catcher.winfo_x()+dx}+{catcher.winfo_y()+dy}")
        catcher._mx, catcher._my = e.x_root, e.y_root
        position_icon()
    elif mouse_mode == "resize":
        BOX_WIDTH, BOX_HEIGHT = max(80, e.x), max(40, e.y)
        catcher.geometry(f"{BOX_WIDTH}x{BOX_HEIGHT}")
        redraw()
    elif mouse_mode == "split":
        split_ratio = max(0.1, min(e.y/BOX_HEIGHT if split_mode=="horizontal" else e.x/BOX_WIDTH, 0.9))
        redraw()

canvas.bind("<Button-1>", press)
canvas.bind("<B1-Motion>", drag)

redraw()
update_ui_colors()
root.mainloop()
