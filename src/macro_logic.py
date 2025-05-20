import time
import pickle
from pynput import mouse, keyboard
from datetime import datetime

actions = []
recording = False
recording_file = None
playback_running = False
pending_recording = None
playback_finished_callback = None


def set_playback_finished_callback(callback):
    global playback_finished_callback
    playback_finished_callback = callback


def set_recording_file(path):
    global recording_file
    recording_file = path


def get_recording_file():
    return recording_file if recording_file else ""


def on_click(x, y, button, pressed):
    if recording:
        actions.append(("mouse_click", time.time(), x, y, button.name, pressed))


def on_press(key):
    if recording:
        try:
            actions.append(("key_press", time.time(), key.char))
        except AttributeError:
            actions.append(("key_press", time.time(), str(key)))


def record_actions():
    global recording, actions, pending_recording
    recording = True
    actions = []
    start_time = time.time()

    mouse_listener = mouse.Listener(on_click=on_click)
    keyboard_listener = keyboard.Listener(on_press=on_press)

    mouse_listener.start()
    keyboard_listener.start()

    while recording:
        time.sleep(0.1)

    mouse_listener.stop()
    keyboard_listener.stop()

    if actions:
        base = actions[0][1]
        for i in range(len(actions)):
            actions[i] = (actions[i][0], actions[i][1] - base, *actions[i][2:])
        pending_recording = actions.copy()
        print("📌 Recording complete. Awaiting save.")
    else:
        print("⚠ No actions recorded.")


def save_pending_recording(path=None):
    global pending_recording, recording_file
    if pending_recording:
        if path:
            recording_file = path
        with open(recording_file, "wb") as f:
            pickle.dump(pending_recording, f)
        print(f"✅ Recording saved to: {recording_file}")
        pending_recording = None


def stop_recording():
    global recording
    recording = False


def stop_playback():
    global playback_running
    playback_running = False


def play_actions_loop(
    target_title, use_realistic=False, loop_forever=False, loop_count=1
):
    from pynput.mouse import Controller as MouseController, Button
    from pynput.keyboard import Controller as KeyboardController

    global playback_running
    playback_running = True

    mouse_ctrl = MouseController()
    keyboard_ctrl = KeyboardController()

    try:
        with open(recording_file, "rb") as f:
            actions = pickle.load(f)
    except FileNotFoundError:
        print("⚠ No recorded actions found.")
        playback_running = False
        return

    print(f"🔁 Starting playback: {len(actions)} actions")

    count = 0
    while playback_running and (loop_forever or count < loop_count):
        count += 1
        print(f"▶ Loop {count} started")

        prev_time = 0
        for action in actions:
            if not playback_running:
                break

            delay = action[1]
            time.sleep(max(0, delay - prev_time))
            prev_time = delay

            if action[0] == "mouse_click":
                _, _, x, y, button, pressed = action

                if use_realistic:
                    current_x, current_y = mouse_ctrl.position
                    steps = 20
                    dx = (x - current_x) / steps
                    dy = (y - current_y) / steps

                    for step in range(steps):
                        if not playback_running:
                            break
                        mouse_ctrl.position = (
                            int(current_x + dx * step),
                            int(current_y + dy * step),
                        )
                        time.sleep(0.005)

                mouse_ctrl.position = (x, y)

                if button == "left":
                    if pressed:
                        mouse_ctrl.press(Button.left)
                    else:
                        mouse_ctrl.release(Button.left)

            elif action[0] == "key_press":
                _, _, key = action
                try:
                    keyboard_ctrl.press(key)
                    keyboard_ctrl.release(key)
                except:
                    pass

    print(f"✅ Loop {count} completed.")
    if playback_finished_callback:
        playback_finished_callback()
