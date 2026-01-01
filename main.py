import tkinter as tk
from tkinter import colorchooser
import threading, time, json, os, re
from PIL import ImageGrab
import pytesseract
import cv2
import numpy as np
import ctypes
from PIL import Image, ImageTk

# ================= SETTINGS =================
SETTINGS_FILE = "settings.json"
default_settings = {
    "bg_color": "#1a1a1a",
    "topbar_color": "#111111",
    "text_color": "#ffffff",
    "yes_color": "#00ff00",
    "no_color": "#ff5555",
    "both_color": "#ff00ff",
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

BOX_WIDTH, BOX_HEIGHT = 180, 45
split_mode = "vertical"
split_ratio = 0.65
mouse_mode = None
catcher_icon = None
ICON_SIZE = 28
sort_mode = "most"   # "most" or "new"
# Updated Modern Button Look
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
    wallet_raw = re.sub(r'\s*[SO]\s*$', '', clean).strip()
    wallet = wallet_raw[:6] + wallet_raw[-1] if len(wallet_raw) >= 7 else wallet_raw
    return wallet, vote

# ================= OCR LOOP =================
def ocr_loop():
    global wallets, last_text, last_key
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

            combined = f"{textA} {textB}"
            parsed = parse_line(combined)
            if parsed:
                wallet, vote = parsed
                wallets.setdefault(wallet, {"YES": 0, "NO": 0})
                key = f"{wallet}|{vote}"
                if key != last_key:
                    wallets[wallet][vote] += 1
                    last_key = key

            update_results()
            time.sleep(0.2)
        except Exception:
            time.sleep(0.2)

# ================= CONTROL =================
# ================= CONTROL =================
def start_counter():
    global running, wallets, last_text, last_key
    wallets, last_text = {}, None
    last_key = None  # <--- FIX: This ensures the VERY FIRST detection is counted
    update_results()
    if not running:
        running = True
        threading.Thread(target=ocr_loop, daemon=True).start()

def reset_counts():
    global wallets, last_text, last_key
    wallets, last_text = {}, None
    last_key = None  # <--- FIX: This ensures after a reset, the next capture counts
    update_results()

def pause_counter():
    global running
    running = False


def toggle_sort():
    global sort_mode
    sort_mode = "new" if sort_mode == "most" else "most"
    update_results()

# ================= UI =================
def update_results():
    results.delete("1.0", tk.END)
    items = list(wallets.items())

    if sort_mode == "most":
        items.sort(key=lambda x: (x[1]["YES"] + x[1]["NO"]), reverse=True)
    else:  # newest first
        items = items[::-1]

    for w, v in items:
        results.insert(
            tk.END,
            f"{w} | YES:{v['YES']} | NO:{v['NO']}\n"
        )

def update_ui_colors():
    app.configure(bg=settings["bg_color"])
    top.configure(bg=settings["topbar_color"])
    ctrl.configure(bg=settings["bg_color"])
    results.configure(bg=settings["bg_color"], fg=settings["text_color"], font=("Segoe UI", 10))
    for w in top.winfo_children():
        w.configure(bg=settings["topbar_color"], fg=settings["text_color"])

def choose_color(key):
    c = colorchooser.askcolor()[1]
    if c:
        settings[key] = c
        save_settings()
        update_ui_colors()

def open_settings():
    win = tk.Toplevel(app)
    win.configure(bg=settings["bg_color"])
    win.geometry("320x320+150+150")

    bar = tk.Frame(win, bg=settings["topbar_color"], height=34)
    bar.pack(fill="x")

    def sm(e):
        win._ox, win._oy = e.x, e.y
    def mv(e):
        win.geometry(f"+{e.x_root-win._ox}+{e.y_root-win._oy}")

    bar.bind("<Button-1>", sm)
    bar.bind("<B1-Motion>", mv)

    tk.Label(bar, text="Settings", bg=settings["topbar_color"],
             fg=settings["text_color"]).pack(side="left", padx=10)
    tk.Button(bar, text="X", command=win.destroy,
              bg=settings["topbar_color"], fg=settings["text_color"],
              bd=0).pack(side="right", padx=10)

    body = tk.Frame(win, bg=settings["bg_color"])
    body.pack(fill="both", expand=True, padx=10, pady=10)

    def add(lbl, key):
        row = tk.Frame(body, bg=settings["bg_color"])
        row.pack(fill="x", pady=6)
        tk.Label(row, text=lbl, fg=settings["text_color"],
                 bg=settings["bg_color"], width=12, anchor="w").pack(side="left")
        tk.Button(row, text="Change", command=lambda: choose_color(key)).pack(side="right")

    add("Background", "bg_color")
    add("Top Bar", "topbar_color")
    add("Text", "text_color")
    add("YES", "yes_color")
    add("NO", "no_color")
    add("BOTH", "both_color")

def close_app():
    global running
    running = False
    try: catcher.destroy()
    except: pass
    app.destroy()
    root.destroy()

# ================= ROOT (TASKBAR ANCHOR) =================
# ================= ROOT =================
root = tk.Tk()

# 1. Hide the tiny anchor window
root.geometry("1x1+0+0")
root.attributes("-alpha", 0.0)

# 2. Process and Set the Icon
try:
    # Use your existing logic to open the PNG
    icon_pil = Image.open("icon.png").resize((ICON_SIZE, ICON_SIZE), Image.LANCZOS)
    icon_img = ImageTk.PhotoImage(icon_pil)
    
    # THIS LINE replaces the feather on the taskbar/window
    root.tk.call('wm', 'iconphoto', root._w, icon_img)
except Exception as e:
    print(f"Icon not found, using default: {e}")
    icon_img = None

root.protocol("WM_DELETE_WINDOW", close_app)

# ================= APP =================
app = tk.Toplevel(root)
app.overrideredirect(True)
app.geometry("300x400+100+100")
app.configure(bg=settings["bg_color"])

def show_app(event=None):
    app.deiconify()
    app.lift()
    app.focus_force()

app.bind("<Map>", show_app)

try:
    ctypes.windll.dwmapi.DwmSetWindowAttribute(
        ctypes.windll.user32.GetParent(app.winfo_id()),
        2, ctypes.byref(ctypes.c_int(0)), 4
    )
except:
    pass

top = tk.Frame(app, bg=settings["topbar_color"], height=40)
top.pack(fill="x")

def sm(e):
    app._ox, app._oy = e.x, e.y
def mv(e):
    app.geometry(f"+{e.x_root-app._ox}+{e.y_root-app._oy}")
def show_catcher_icon():
    if catcher_icon and catcher_icon.winfo_exists():
        catcher_icon.deiconify()
        catcher_icon.lift()
        catcher_icon.attributes("-topmost", True)
        position_icon()
def sync_icon_with_catcher(event=None):
    position_icon()
def hide_catcher_icon():
    if catcher_icon and catcher_icon.winfo_exists():
        catcher_icon.withdraw()

top.bind("<Button-1>", sm)
top.bind("<B1-Motion>", mv)

tk.Label(top, text="WYN counter",
         fg=settings["text_color"],
         bg=settings["topbar_color"]).pack(side="left", padx=20)

tk.Button(top, text="*", command=open_settings,
          bg=settings["topbar_color"],
          fg=settings["text_color"],
          bd=0).pack(side="right", padx=5)
          
tk.Button(
    top,
    text="_",
    command=lambda: minimize_app(),
    bg=settings["topbar_color"],
    fg=settings["text_color"],
    bd=0,
    width=3
).pack(side="right")

tk.Button(top, text="X", command=close_app,
          bg=settings["topbar_color"],
          fg=settings["text_color"],
          bd=0).pack(side="right", padx=10)

ctrl = tk.Frame(app, bg=settings["bg_color"])
ctrl.pack(side="left", fill="y", padx=5)

tk.Button(ctrl, text="✨ Start", command=start_counter, bg="#4CAF50", fg="white", **btn_style).pack(fill="x", pady=5)
tk.Button(ctrl, text="⏸ Pause", command=pause_counter, bg="#FF9800", fg="white", **btn_style).pack(fill="x", pady=5)
tk.Button(ctrl, text="♻ Reset", command=reset_counts, bg="#F44336", fg="white", **btn_style).pack(fill="x", pady=5)
tk.Button(ctrl, text="📊 Order", command=toggle_sort, bg="#2196F3", fg="white", **btn_style).pack(fill="x", pady=5)


scroll = tk.Scrollbar(app)
scroll.pack(side="right", fill="y")
results = tk.Text(app, font=("Segoe UI", 10), yscrollcommand=scroll.set)
results.pack(fill="both", expand=True, padx=5, pady=5)
scroll.config(command=results.yview)

# ================= CATCHER =================
catcher = tk.Toplevel(app)
catcher.overrideredirect(True)
catcher.attributes("-topmost", True)
catcher.attributes("-alpha", 0.35)
catcher.geometry(f"{BOX_WIDTH}x{BOX_HEIGHT}+400+200")

catcher_icon = tk.Toplevel(app)
catcher_icon.overrideredirect(True)
catcher_icon.attributes("-topmost", True)
catcher_icon.geometry(f"{ICON_SIZE}x{ICON_SIZE}")
catcher.bind("<Configure>", sync_icon_with_catcher)

icon_lbl = tk.Label(catcher_icon, image=icon_img, bg="#000000")
icon_lbl.image = icon_img
icon_lbl.pack(fill="both", expand=True)
icon_lbl.bind("<Button-1>", lambda e: restore_app())

canvas = tk.Canvas(catcher, highlightthickness=3, highlightbackground="red")
canvas.pack(fill="both", expand=True)

def minimize_app():
    global app_hidden
    app_hidden = True
    app.withdraw()
    show_catcher_icon()

def restore_app():
    global app_hidden
    app_hidden = False
    hide_catcher_icon()
    app.deiconify()
    app.lift()
    app.focus_force()

def position_icon():
    if catcher_icon and catcher.winfo_exists():
        x = catcher.winfo_x() + BOX_WIDTH + 4
        y = catcher.winfo_y()
        catcher_icon.geometry(f"+{x}+{y}")

def divider_pos():
    return int((BOX_HEIGHT if split_mode=="horizontal" else BOX_WIDTH) * split_ratio)

def redraw():
    canvas.delete("all")
    if split_mode == "horizontal":
        y = divider_pos()
        canvas.create_line(0, y, BOX_WIDTH, y, fill="yellow", width=2)
    else:
        x = divider_pos()
        canvas.create_line(x, 0, x, BOX_HEIGHT, fill="yellow", width=2)
    canvas.create_rectangle(BOX_WIDTH-10, BOX_HEIGHT-10, BOX_WIDTH, BOX_HEIGHT, fill="red")

def press(e):
    global mouse_mode
    if e.x >= BOX_WIDTH-12 and e.y >= BOX_HEIGHT-12:
        mouse_mode = "resize"
    elif abs((e.y if split_mode=="horizontal" else e.x) - divider_pos()) <= 5:
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
    elif mouse_mode == "resize":
        BOX_WIDTH, BOX_HEIGHT = max(80, e.x), max(40, e.y)
        catcher.geometry(f"{BOX_WIDTH}x{BOX_HEIGHT}")
        redraw()
    elif mouse_mode == "split":
        if split_mode == "horizontal":
            split_ratio = max(0.1, min(e.y/BOX_HEIGHT, 0.9))
        else:
            split_ratio = max(0.1, min(e.x/BOX_WIDTH, 0.9))
        redraw()
        position_icon()

def release(e):
    global mouse_mode
    mouse_mode = None

canvas.bind("<Button-1>", press)
canvas.bind("<B1-Motion>", drag)
canvas.bind("<ButtonRelease-1>", release)

redraw()
update_ui_colors()
position_icon()
show_app()

root.mainloop()