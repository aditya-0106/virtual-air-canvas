\# Virtual Air Canvas



Draw in the air with your index finger. A webcam tracks your hand in real time and paints on a live canvas. No mouse, touchscreen or stylus needed.



Built with Python, OpenCV and MediaPipe.



\## Features



\- Real-time hand tracking with MediaPipe (one hand)

\- Draw by raising only your index finger

\- Clear the whole canvas instantly with an open palm

\- 7 colours plus an eraser, switchable from the keyboard

\- Smoothed fingertip movement for cleaner lines

\- Save your drawing as a PNG



\## Controls



| Input | Action |

|---|---|

| Index finger up (others down) | Draw / erase |

| Open palm (all four fingers up) | Clear canvas |

| Keys 1-7 | Blue, Green, Red, Yellow, Purple, Cyan, White |

| Key 8 | Eraser |

| C | Clear canvas |

| S | Save canvas as PNG (`drawing\_<timestamp>.png`) |

| Q | Quit |



\## How it works



1\. OpenCV captures webcam frames and mirrors them.

2\. MediaPipe Hands returns 21 landmarks for the hand in each frame.

3\. A finger counts as extended when its tip is above its middle joint. This gives simple gesture rules for drawing and clearing.

4\. The index fingertip position is smoothed with exponential smoothing, then line segments are drawn on a separate canvas layer.

5\. The canvas is blended onto the live video frame.



\## Setup



Requires a webcam and \*\*Python 3.12\*\*.



```

git clone https://github.com/aditya-0106/virtual-air-canvas.git

cd virtual-air-canvas

py -3.12 -m venv .venv

.\\.venv\\Scripts\\python.exe -m pip install -r requirements.txt

.\\.venv\\Scripts\\python.exe air\_canvas.py

```



\### Why these versions are pinned



\- `mediapipe==0.10.21`: newer MediaPipe releases removed the legacy `mp.solutions` interface this project uses.

\- Python 3.12: MediaPipe 0.10.21 has no installer for Python 3.14.



\## Limitations



\- Tracks one hand only.

\- Gesture rules are simple and can misfire in poor lighting or when the hand is partly out of frame.

\- The thumb is not used in any gesture.



\## Possible improvements



\- Migrate from the legacy `mp.solutions` interface to the newer MediaPipe Tasks API so the version pin is no longer needed.

\- Add undo and adjustable brush size.



\## Authors



Ramesha G and R N Aditya.





