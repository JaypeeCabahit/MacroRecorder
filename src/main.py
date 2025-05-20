import customtkinter as ctk
import threading
import macro_logic
import pygetwindow as gw
import keyboard
from tkinter import filedialog, messagebox
import sys
from PIL import Image
import os
from datetime import datetime

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

app = ctk.CTk()
app.title("Jaypee's Macro Recorder")
app.resizable(False, False)

# Center window
window_width, window_height = 420, 550
screen_width, screen_height = app.winfo_screenwidth(), app.winfo_screenheight()
x = int((screen_width / 2) - (window_width / 2))
y = int((screen_height / 2) - (window_height / 2))
app.geometry(f"{window_width}x{window_height}+{x}+{y}")

selected_app_title = None
playback_thread = None
is_recording = False

realistic_mode_enabled = ctk.BooleanVar(value=True)
loop_count_var = ctk.StringVar(value="1")

hotkeys = {
    "start_record": "shift+1",
    "stop_record": "shift+1",
    "start_playback": "shift+2",
    "stop_playback": "shift+2",
}

hotkey_window = None  # Prevent multiple instances


def rebind_hotkeys():
    keyboard.unhook_all_hotkeys()

    def safe_callback(func):
        def wrapper():
            try:
                if (
                    not hotkey_window
                    or not hotkey_window.winfo_exists()
                    or not hotkey_window.focus_displayof()
                ):
                    func()
            except:
                func()  # In case the window was destroyed

        return wrapper

    if hotkeys["start_record"]:
        keyboard.add_hotkey(hotkeys["start_record"], safe_callback(toggle_recording))
    if hotkeys["stop_record"]:
        keyboard.add_hotkey(hotkeys["stop_record"], safe_callback(toggle_recording))
    if hotkeys["start_playback"]:
        keyboard.add_hotkey(hotkeys["start_playback"], safe_callback(toggle_playback))
    if hotkeys["stop_playback"]:
        keyboard.add_hotkey(hotkeys["stop_playback"], safe_callback(toggle_playback))


def open_hotkey_settings():
    global hotkey_window
    if hotkey_window and hotkey_window.winfo_exists():
        hotkey_window.lift()
        return

    hotkey_window = ctk.CTkToplevel(app)
    hotkey_window.title("Hotkey Settings")
    hotkey_window.geometry("400x330")
    hotkey_window.resizable(False, False)
    hotkey_window.grab_set()

    hotkey_window.protocol("WM_DELETE_WINDOW", lambda: None)

    # Disable main UI buttons
    for btn in [hamburger_btn, record_btn, play_btn, refresh_btn, loop_button]:
        btn.configure(state="disabled")

    current_recording = [None]

    default_hotkeys = {
        "start_record": "shift+1",
        "stop_record": "shift+1",
        "start_playback": "shift+2",
        "stop_playback": "shift+2",
    }

    label_refs = {}

    def enable_hotkey_detection(key_name, label_widget):
        if current_recording[0] is not None:
            print("⚠ Finish setting the previous hotkey first.")
            return

        label_widget.configure(text="Press keys...")
        captured = []
        buffer = set()

        def on_key(event):
            name = event.name
            scan_code = event.scan_code

            shift_map = {
                "!": "1",
                "@": "2",
                "#": "3",
                "$": "4",
                "%": "5",
                "^": "6",
                "&": "7",
                "*": "8",
                "(": "9",
                ")": "0",
            }

            if name is None or name in shift_map:
                name = shift_map.get(name, str(scan_code))

            key = name.lower()
            if event.event_type == "down":
                buffer.add(key)
                mods = {"shift", "ctrl", "alt"}
                mod_keys = [k for k in buffer if k in mods]
                other_keys = [k for k in buffer if k not in mods]

                if len(mod_keys) >= 1 and len(other_keys) >= 1:
                    combo = "+".join(mod_keys + other_keys)
                    captured.clear()
                    captured.append(combo)
                    label_widget.configure(text=combo.upper())
                    keyboard.unhook(current_recording[0])
                    current_recording[0] = None
                    hotkeys[key_name] = combo
                    print(f"🔧 Hotkey for {key_name} set to: {combo}")
                    rebind_hotkeys()
            elif event.event_type == "up":
                buffer.discard(key)

        current_recording[0] = keyboard.hook(on_key)

    def create_hotkey_row(row, label, key_name):
        ctk.CTkLabel(hotkey_window, text=label).grid(
            row=row, column=0, padx=10, pady=5, sticky="w"
        )

        label_widget = ctk.CTkLabel(
            hotkey_window, text=hotkeys.get(key_name, "None").upper(), width=120
        )
        label_widget.grid(row=row, column=1, padx=5)
        label_refs[key_name] = label_widget

        ctk.CTkButton(
            hotkey_window,
            text="Change",
            width=60,
            command=lambda: enable_hotkey_detection(key_name, label_widget),
        ).grid(row=row, column=2, padx=5)

        def clear():
            hotkeys[key_name] = ""
            label_widget.configure(text="None")
            print(f"❌ Hotkey for {key_name} cleared.")

        ctk.CTkButton(hotkey_window, text="Clear", width=50, command=clear).grid(
            row=row, column=3, padx=5
        )

    create_hotkey_row(0, "Start record", "start_record")
    create_hotkey_row(1, "Stop record", "stop_record")
    create_hotkey_row(2, "Start playback", "start_playback")
    create_hotkey_row(3, "Stop playback", "stop_playback")

    def reset_hotkeys():
        for key, default in default_hotkeys.items():
            hotkeys[key] = default
            if key in label_refs:
                label_refs[key].configure(text=default.upper())
        print("🔁 Hotkeys reset to default.")
        rebind_hotkeys()

    def close_window():
        for btn in [hamburger_btn, record_btn, play_btn, refresh_btn, loop_button]:
            btn.configure(state="normal")

        if current_recording[0]:
            keyboard.unhook(current_recording[0])
            current_recording[0] = None

        rebind_hotkeys()
        hotkey_window.grab_release()
        hotkey_window.destroy()

    # Close & Reset buttons
    ctk.CTkButton(hotkey_window, text="Reset to Default", command=reset_hotkeys).grid(
        row=4, column=0, columnspan=2, pady=10
    )
    ctk.CTkButton(hotkey_window, text="Close", command=close_window).grid(
        row=4, column=2, columnspan=2, pady=10
    )


class ConsoleRedirect:
    def __init__(self, widget):
        self.widget = widget

    def write(self, message):
        if message.strip() and not message.startswith("==="):  # Time-stamp only logs
            timestamp = datetime.now().strftime("%I:%M %p").lstrip("0")
            formatted = f"[{timestamp}] {message}"
        else:
            formatted = message
        self.widget.configure(state="normal")
        self.widget.insert("end", formatted)
        self.widget.see("end")
        self.widget.configure(state="disabled")

    def flush(self):
        pass


def resource_path(relative_path):
    base_path = getattr(sys, "_MEIPASS", os.path.abspath("."))
    return os.path.join(base_path, relative_path)


# Load images
play_img = ctk.CTkImage(Image.open(resource_path("assets/play.png")), size=(40, 40))
record_img = ctk.CTkImage(Image.open(resource_path("assets/record.png")), size=(40, 40))
stop_img = ctk.CTkImage(Image.open(resource_path("assets/stop.png")), size=(40, 40))


def update_macro_label():
    path = macro_logic.get_recording_file()
    if not path or not os.path.exists(path):
        macro_label.configure(text="Current Macro File: None")
        print("📁 No macro file found.")
    else:
        macro_label.configure(text=f"Current Macro File: {os.path.basename(path)}")
        print(f"📂 Macro loaded: {path}")


def load_macro_file():
    path = filedialog.askopenfilename(filetypes=[("Pickle Files", "*.pkl")])
    if path:
        macro_logic.set_recording_file(path)
        update_macro_label()
        print(f"✅ Loaded macro: {path}")


def save_macro():
    macro_logic.save_pending_recording()
    print("💾 Macro saved.")


def save_macro_as():
    path = filedialog.asksaveasfilename(
        defaultextension=".pkl", filetypes=[("Pickle Files", "*.pkl")]
    )
    if path:
        macro_logic.save_pending_recording(path)
        macro_logic.set_recording_file(path)
        update_macro_label()
        print(f"💾 Saved as: {path}")


def select_app():
    windows = gw.getWindowsWithTitle("")
    app_titles = [win.title for win in windows if win.title]
    app_dropdown.configure(values=app_titles)


def set_selected_app(value):
    global selected_app_title
    selected_app_title = value


def toggle_recording():
    global is_recording

    if macro_logic.playback_running:
        print("⚠ Cannot record while playback is running.")
        return

    if is_recording:
        macro_logic.stop_recording()
        record_btn.configure(image=record_img)
        is_recording = False
        if messagebox.askyesno("Save Recording", "Do you want to save this recording?"):
            path = filedialog.asksaveasfilename(
                defaultextension=".pkl", filetypes=[("Pickle Files", "*.pkl")]
            )
            if path:
                macro_logic.save_pending_recording(path)
                macro_logic.set_recording_file(path)
                update_macro_label()
            else:
                print("⚠ Save cancelled. Recording not saved.")
        else:
            print("❌ Recording discarded. Not saved.")
    else:
        if macro_logic.playback_running:
            print("⚠ Cannot record while playback is running.")
            return
        threading.Thread(target=macro_logic.record_actions, daemon=True).start()
        record_btn.configure(image=stop_img)
        is_recording = True


def toggle_playback():
    global playback_thread
    if is_recording:
        print("⚠ Cannot playback while recording is active.")
        return

    if macro_logic.playback_running:
        macro_logic.stop_playback()
        play_btn.configure(image=play_img)
        return

    if not selected_app_title:
        print("⚠ Please select a target application.")
        return

    path = macro_logic.get_recording_file()
    if not path or not os.path.exists(path):
        print("⚠ No valid macro file to play.")
        return

    try:
        count = int(loop_count_var.get())
    except ValueError:
        count = 1

    def on_playback_finished():
        play_btn.configure(image=play_img)
        print("🟢 Playback fully finished.")

    macro_logic.set_playback_finished_callback(on_playback_finished)

    playback_thread = threading.Thread(
        target=macro_logic.play_actions_loop,
        args=(selected_app_title, realistic_mode_enabled.get(), False, count),
        daemon=True,
    )
    playback_thread.start()
    play_btn.configure(image=stop_img)


def toggle_theme(mode):
    ctk.set_appearance_mode("light" if mode == "Light" else "dark")


# UI Layout
main_frame = ctk.CTkFrame(app, corner_radius=10)
main_frame.pack(padx=20, pady=20, fill="both", expand=True)

# Hamburger Menu
menu_frame = None


def show_menu():
    global menu_frame
    if menu_frame and menu_frame.winfo_exists():
        menu_frame.destroy()
        return
    menu_frame = ctk.CTkFrame(main_frame, width=120, corner_radius=6)
    menu_frame.place(x=10, y=50)

    ctk.CTkButton(menu_frame, text="Load", command=load_macro_file, width=100).pack(
        pady=4
    )
    ctk.CTkButton(menu_frame, text="Save", command=save_macro, width=100).pack(pady=4)
    ctk.CTkButton(menu_frame, text="Save As", command=save_macro_as, width=100).pack(
        pady=4
    )
    ctk.CTkButton(
        menu_frame, text="Hotkeys", command=open_hotkey_settings, width=100
    ).pack(pady=4)


top_bar = ctk.CTkFrame(main_frame, fg_color="transparent")
top_bar.pack(fill="x", pady=(5, 0))

hamburger_btn = ctk.CTkButton(top_bar, text="☰", width=32, height=32, command=show_menu)
hamburger_btn.pack(side="left", padx=(0, 8))

macro_label = ctk.CTkLabel(top_bar, text="", font=ctk.CTkFont(size=14, weight="bold"))
macro_label.pack(side="left", pady=5)
update_macro_label()

btn_row = ctk.CTkFrame(main_frame, fg_color="transparent")
btn_row.pack(pady=5)

play_btn = ctk.CTkButton(
    btn_row, text="", image=play_img, width=80, height=80, command=toggle_playback
)
play_btn.grid(row=0, column=0, padx=10)

record_btn = ctk.CTkButton(
    btn_row, text="", image=record_img, width=80, height=80, command=toggle_recording
)
record_btn.grid(row=0, column=1, padx=10)

ctk.CTkLabel(main_frame, text="Target Application:").pack(pady=(20, 5))
app_dropdown = ctk.CTkOptionMenu(main_frame, values=[""], command=set_selected_app)
app_dropdown.pack(pady=5, fill="x")

refresh_btn = ctk.CTkButton(main_frame, text="Refresh App List", command=select_app)
refresh_btn.pack(pady=(5, 10), fill="x")

# Realistic Movement
realistic_checkbox = ctk.CTkCheckBox(
    main_frame, text="Use Realistic Movement", variable=realistic_mode_enabled
)
realistic_checkbox.pack(anchor="w", padx=5, pady=(5, 0))

# Loop Count Entry
loop_entry = ctk.CTkEntry(
    main_frame,
    textvariable=loop_count_var,
    width=150,
    placeholder_text="Set the loop amount",
)


def set_loop_amount():
    try:
        count = int(loop_count_var.get())
        if count < 1:
            raise ValueError
        print(f"🔁 Loop amount set to: {count}")
    except ValueError:
        print("⚠ Please enter a valid positive number for loop amount.")


loop_entry.pack(anchor="w", padx=5, pady=(5, 10))

loop_button = ctk.CTkButton(
    main_frame,
    text="Set Loop Amount",
    command=set_loop_amount,
    width=150,
)
loop_button.pack(anchor="w", padx=5, pady=(0, 10))

# Console
ctk.CTkLabel(main_frame, text="Console:").pack(anchor="w", padx=5)
console_text = ctk.CTkTextbox(main_frame, height=100)
console_text.pack(fill="both", padx=5, pady=5)
console_text.configure(state="disabled")

theme_switch = ctk.CTkSegmentedButton(
    main_frame, values=["Dark", "Light"], command=toggle_theme
)
theme_switch.set("Dark")
theme_switch.pack(pady=10)

# Redirect stdout to console
sys.stdout = ConsoleRedirect(console_text)
sys.stderr = ConsoleRedirect(console_text)

keyboard.add_hotkey(hotkeys["start_playback"], toggle_playback)
keyboard.add_hotkey(hotkeys["start_record"], toggle_recording)

select_app()

print("==================================")
print("Built-In Keybinds:")
print("SHIFT + 1 → Start/Stop Recording")
print("SHIFT + 2 → Start/Stop Playback")
print("==================================")

app.mainloop()
