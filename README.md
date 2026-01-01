# wyn
 WYN: Logic & Purpose

The Purpose: This tool is a bridge between the screen and data. It captures the "Now" by reading what your eyes see, turning pixels into countable events. It serves as a real-time monitor for any stream where identity and choice (YES/NO) align.

⚙️ How it Works

The WYN uses a focus-window (The Catcher) to grab a screenshot of a specific area every 0.2 seconds.

1. OCR Vision: It extracts text characters from the image.
2. Key Memory: It compares the current text against a `last_key` variable. If it matches, it ignores it. If it’s new, it counts.
3. The Logic: It splits the image into two zones (Identity | Action) to ensure the vote is tied to the correct wallet.

🔮 The Future: Universal Alignment

The current version reads "YES" and "NO," but the future "Mold" is universal. Upcoming versions will move beyond simple text:

* Multi-State Tracking: Beyond binary choices—tracking any keyword or category.
* Symbol Recognition: Reading icons, emojis, or colors as data points instead of just letters.
* Temporal Logging: Exporting data to CSV to map how events change over time, like a digital horoscope.
* Universal Input: Adapting the OCR to read any list, any game, or any stream regardless of language or font.

We are moving from counting words to mapping movements. 

🌌 Whaa Yes No

Observe the flow. Track the Now.


Setup & Run:
1. Engine: Install Tesseract OCR to C:\Program Files\Tesseract-OCR\tesseract.exe.
2. Environment: Open CMD → pip install Pillow pytesseract opencv-python numpy pyinstaller
3. Files: Place main.py, icon.png (for UI), and icon.ico (for EXE) in one folder.
4. Build: In CMD folder → pyinstaller --noconsole --onefile --icon=icon.ico --add-data "icon.png;." main.py
5. Launch: Run main.exe from the /dist folder.
