"""
Virtual Air Canvas
==================
Tech  : Python · OpenCV · MediaPipe
Authors: Ramesha G and R N Aditya  

Controls
--------
✍️  Index finger UP (alone)   → Draw / Erase
🖐️  Open palm (all 4 fingers) → Clear canvas instantly
1-7 keys                       → Select colour (Blue/Green/Red/Yellow/Purple/Cyan/White)
8 key                          → Select Eraser
C key                          → Clear canvas
S key                          → Save drawing as PNG
Q key                          → Quit
"""

import cv2
import numpy as np
import mediapipe as mp
import datetime

# ── MediaPipe initialisation ─────────────────────────────────────────────────
mp_hands = mp.solutions.hands
mp_draw  = mp.solutions.drawing_utils

hands = mp_hands.Hands(
    static_image_mode        = False,
    max_num_hands            = 1,
    min_detection_confidence = 0.75,
    min_tracking_confidence  = 0.75,
)

# ── Camera ───────────────────────────────────────────────────────────────────
cap = cv2.VideoCapture(0)
cap.set(cv2.CAP_PROP_FRAME_WIDTH,  1280)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)

# ── Colour palette (BGR) ─────────────────────────────────────────────────────
COLOURS = [
    ("Blue",   (255,  80,  80)),
    ("Green",  ( 50, 220,  50)),
    ("Red",    ( 50,  50, 255)),
    ("Yellow", (  0, 230, 230)),
    ("Purple", (220,  50, 220)),
    ("Cyan",   (230, 200,   0)),
    ("White",  (240, 240, 240)),
    ("Eraser", (  0,   0,   0)),   
]

# Number key mapping: key '1' → index 0, ..., key '8' → index 7
KEY_MAP = {
    ord('1'): 0,
    ord('2'): 1,
    ord('3'): 2,
    ord('4'): 3,
    ord('5'): 4,
    ord('6'): 5,
    ord('7'): 6,
    ord('8'): 7,
}

ERASER_IDX   = len(COLOURS) - 1
BRUSH_SIZE   = 8
ERASER_SIZE  = 45
PALETTE_H    = 72          # height of the colour bar at the top (px)

# Exponential smoothing factor
SMOOTH_ALPHA = 0.50

# ── State ────────────────────────────────────────────────────────────────────
selected           = 0
canvas             = None
prev_x, prev_y     = None, None
smooth_x, smooth_y = None, None
save_count         = 0
flash_msg          = ""
flash_timer        = 0


# ── Gesture helpers ──────────────────────────────────────────────────────────
def finger_states(lm):
    """Return booleans for which fingers are extended."""
    tip_ids = {'index': 8, 'middle': 12, 'ring': 16, 'pinky': 20}
    pip_ids = {'index': 6, 'middle': 10, 'ring': 14, 'pinky': 18}
    st = {}
    for f in ('index', 'middle', 'ring', 'pinky'):
        st[f] = lm[tip_ids[f]].y < lm[pip_ids[f]].y
    st['thumb'] = lm[4].x < lm[3].x
    return st


def is_drawing_pose(st):
    """Index ONLY extended → draw."""
    return (st['index'] and
            not st['middle'] and
            not st['ring']   and
            not st['pinky'])


def is_open_palm(st):
    """All four fingers extended → clear canvas."""
    return st['index'] and st['middle'] and st['ring'] and st['pinky']


# ── UI helpers ───────────────────────────────────────────────────────────────
def draw_palette(frame, sel, w):
    n     = len(COLOURS)
    box_w = w // n

    for i, (name, col) in enumerate(COLOURS):
        x1, x2 = i * box_w, (i + 1) * box_w - 2

        cv2.rectangle(frame, (x1, 0),  (x2, PALETTE_H),    col,        -1)
        cv2.rectangle(frame, (x1, 48), (x2, PALETTE_H),    (25,25,25), -1)

        # Key number label (e.g. "[1]")
        key_label = f"[{i + 1}]"
        cv2.putText(frame, key_label, (x1 + 5, 20),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.42, (255, 255, 255), 1, cv2.LINE_AA)

        # Colour name label
        cv2.putText(frame, name, (x1 + 5, PALETTE_H - 8),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.38, (210, 210, 210), 1, cv2.LINE_AA)

        # Selection indicator
        if i == sel:
            cv2.rectangle(frame, (x1, 0), (x2, PALETTE_H), (255, 255, 255), 3)
            cx = (x1 + x2) // 2
            pts = np.array([[cx - 9, PALETTE_H], [cx + 9, PALETTE_H], [cx, PALETTE_H + 14]])
            cv2.fillPoly(frame, [pts], (255, 255, 255))


def draw_hud(frame, mode, sel, w, h):
    col_name = COLOURS[sel][0]
    col_val  = COLOURS[sel][1]

    # ── bottom bar ──
    overlay = frame.copy()
    cv2.rectangle(overlay, (0, h - 42), (w, h), (20, 20, 20), -1)
    cv2.addWeighted(overlay, 0.75, frame, 0.25, 0, frame)

    cv2.putText(frame,
                "Index finger=Draw  Open palm=Clear  |  1-7=Colour  8=Eraser  C=Clear  S=Save  Q=Quit",
                (12, h - 13), cv2.FONT_HERSHEY_SIMPLEX,
                0.50, (190, 190, 190), 1, cv2.LINE_AA)

    # ── mode badge (top-right) ──
    MODE_COLOURS = {
        'DRAWING'    : (  0, 220,   0),
        'ERASING'    : (  0, 130, 255),
        'PALM CLEAR' : (  0,   0, 255),
        'IDLE'       : (120, 120, 120),
    }
    badge_col = MODE_COLOURS.get(mode, (120, 120, 120))
    cv2.putText(frame, mode,
                (w - 175, PALETTE_H + 35),
                cv2.FONT_HERSHEY_SIMPLEX, 0.8, badge_col, 2, cv2.LINE_AA)

    # colour swatch
    if sel != ERASER_IDX:
        cv2.circle(frame, (w - 28, PALETTE_H + 20), 13, col_val, -1)
        cv2.circle(frame, (w - 28, PALETTE_H + 20), 13, (255, 255, 255), 2)

    # ── flash message ──
    global flash_msg, flash_timer
    if flash_timer > 0:
        cx = w // 2
        cy = h // 2
        (tw, th), _ = cv2.getTextSize(flash_msg, cv2.FONT_HERSHEY_SIMPLEX, 1.3, 3)
        cv2.rectangle(frame, (cx - tw//2 - 20, cy - th - 20),
                              (cx + tw//2 + 20, cy + 20), (20, 20, 20), -1)
        cv2.putText(frame, flash_msg,
                    (cx - tw // 2, cy),
                    cv2.FONT_HERSHEY_SIMPLEX, 1.3, (0, 220, 255), 3, cv2.LINE_AA)
        flash_timer -= 1


def show_flash(msg, frames=45):
    global flash_msg, flash_timer
    flash_msg   = msg
    flash_timer = frames


# ── Main loop ────────────────────────────────────────────────────────────────
while True:
    ret, frame = cap.read()
    if not ret:
        break

    frame = cv2.flip(frame, 1)
    h, w  = frame.shape[:2]

    if canvas is None:
        canvas = np.zeros((h, w, 3), dtype=np.uint8)

    # ── Palette ──────────────────────────────────────────────────────────────
    draw_palette(frame, selected, w)

    # ── Hand detection ───────────────────────────────────────────────────────
    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    rgb.flags.writeable = False
    res = hands.process(rgb)
    rgb.flags.writeable = True

    mode = 'IDLE'

    if res.multi_hand_landmarks:
        hand_lm = res.multi_hand_landmarks[0]
        lm      = hand_lm.landmark

        raw_x = int(lm[8].x * w)
        raw_y = int(lm[8].y * h)

        # ── Exponential smoothing ─────────────────────────────────────────
        if smooth_x is None:
            smooth_x, smooth_y = raw_x, raw_y
        else:
            smooth_x = int(SMOOTH_ALPHA * smooth_x + (1 - SMOOTH_ALPHA) * raw_x)
            smooth_y = int(SMOOTH_ALPHA * smooth_y + (1 - SMOOTH_ALPHA) * raw_y)

        sx, sy = smooth_x, smooth_y

        st = finger_states(lm)

        # ── GESTURE: open palm → clear ────────────────────────────────────
        if is_open_palm(st):
            mode = 'PALM CLEAR'
            canvas[:] = 0
            prev_x, prev_y = None, None
            overlay = frame.copy()
            cv2.rectangle(overlay, (0, 0), (w, h), (0, 0, 180), -1)
            cv2.addWeighted(overlay, 0.18, frame, 0.82, 0, frame)
            show_flash("CANVAS CLEARED!", 40)

        # ── GESTURE: index-only → draw / erase ───────────────────────────
        elif is_drawing_pose(st):
            name, col = COLOURS[selected]

            if selected == ERASER_IDX:
                mode      = 'ERASING'
                thickness = ERASER_SIZE
                col       = (0, 0, 0)
                cv2.circle(frame, (sx, sy), ERASER_SIZE // 2, (180, 180, 180), 2)
                cv2.circle(frame, (sx, sy), 3, (200, 200, 200), -1)
            else:
                mode      = 'DRAWING'
                thickness = BRUSH_SIZE
                cv2.circle(frame, (sx, sy), 6,  col,           -1)
                cv2.circle(frame, (sx, sy), 8,  (255,255,255),  1)

            # Only draw below the palette bar
            if sy > PALETTE_H:
                if prev_x is not None:
                    cv2.line(canvas,
                             (prev_x, prev_y), (sx, sy),
                             col, thickness, cv2.LINE_AA)
                prev_x, prev_y = sx, sy
            else:
                prev_x, prev_y = None, None

        else:
            prev_x, prev_y = None, None
            mode = 'IDLE'
            cv2.circle(frame, (sx, sy), 7, (180, 180, 180), 1)

        mp_draw.draw_landmarks(
            frame, hand_lm, mp_hands.HAND_CONNECTIONS,
            mp_draw.DrawingSpec(color=(70, 70, 70), thickness=1, circle_radius=2),
            mp_draw.DrawingSpec(color=(50, 50, 50), thickness=1),
        )

    else:
        prev_x,   prev_y   = None, None
        smooth_x, smooth_y = None, None

    # ── Merge canvas onto live frame ─────────────────────────────────────────
    ink_mask = canvas.any(axis=2)
    if ink_mask.any():
        blended = cv2.addWeighted(frame, 0.30, canvas, 0.70, 0)
        frame[ink_mask] = blended[ink_mask]

    # ── HUD ──────────────────────────────────────────────────────────────────
    draw_hud(frame, mode, selected, w, h)

    cv2.imshow("Virtual Air Canvas  |  Python + OpenCV + MediaPipe", frame)

    # ── Keyboard controls ─────────────────────────────────────────────────────
    key = cv2.waitKey(1) & 0xFF

    if key == ord('q'):
        break

    elif key == ord('c'):
        canvas[:] = 0
        show_flash("CANVAS CLEARED!")

    elif key == ord('s'):
        save_count += 1
        ts       = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"drawing_{ts}.png"
        cv2.imwrite(filename, canvas)
        print(f"[Saved] {filename}")
        show_flash(f"Saved: {filename}", 55)

    elif key in KEY_MAP:
        selected = KEY_MAP[key]
        show_flash(f"{COLOURS[selected][0]} selected", 35)

# ── Cleanup ──────────────────────────────────────────────────────────────────
cap.release()
cv2.destroyAllWindows()