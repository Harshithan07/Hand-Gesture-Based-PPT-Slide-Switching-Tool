import tkinter as tk
from tkinter import filedialog
from PIL import Image, ImageTk
import fitz  # PyMuPDF
import cv2
import mediapipe as mp
import threading
import time

class PDFViewer:
    def __init__(self, master):
        self.master = master
        self.master.title("PDF Viewer")

        self.frame = tk.Frame(master)
        self.frame.pack()

        # Set initial zoom factor
        self.zoom_factor = 1.0

        # Set canvas size to A4 landscape dimensions (842x595 pixels)
        self.canvas = tk.Canvas(self.frame, width=842, height=595)
        self.canvas.pack(side=tk.LEFT, expand=True, fill=tk.BOTH)

        self.scrollbar = tk.Scrollbar(self.frame, command=self.canvas.yview)
        self.scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.canvas.configure(yscrollcommand=self.scrollbar.set)

        self.upload_button = tk.Button(master, text="Upload PDF", command=self.upload_pdf)
        self.upload_button.pack()

        self.prev_button = tk.Button(master, text="Previous Page", command=self.move_to_previous_page)
        self.prev_button.pack(side=tk.LEFT, padx=5, pady=5)

        self.next_button = tk.Button(master, text="Next Page", command=self.move_to_next_page)
        self.next_button.pack(side=tk.LEFT, padx=5, pady=5)

        # Zoom buttons
        self.zoom_in_button = tk.Button(master, text="Zoom In", command=self.zoom_in)
        self.zoom_in_button.pack(side=tk.LEFT, padx=5, pady=5)

        self.zoom_out_button = tk.Button(master, text="Zoom Out", command=self.zoom_out)
        self.zoom_out_button.pack(side=tk.LEFT, padx=5, pady=5)

        self.doc = None
        self.current_page = 0

        # MediaPipe setup for gesture recognition
        self.mp_hands = mp.solutions.hands
        self.hands = self.mp_hands.Hands()
        self.cap = cv2.VideoCapture(0)
        self.prev_gesture = None

        # Time tracking for gestures
        self.last_gesture_time = 0
        self.gesture_delay = 3  # seconds

        # Start the camera in a separate thread
        self.thread = threading.Thread(target=self.load_camera)
        self.thread.daemon = True  # Allow thread to exit when main program exits
        self.thread.start()

    def upload_pdf(self):
        pdf_path = filedialog.askopenfilename(filetypes=[("PDF Files", "*.pdf")])
        if pdf_path:
            self.doc = fitz.open(pdf_path)
            self.current_page = 0
            self.load_page()

    def load_page(self):
        if self.doc:
            page = self.doc[self.current_page]
            pix = page.get_pixmap()
            img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)

            # Resize the image based on the current zoom factor
            img_width = int(842 * self.zoom_factor)
            img_height = int(595 * self.zoom_factor)
            img = img.resize((img_width, img_height), Image.LANCZOS)

            self.img_tk = ImageTk.PhotoImage(img)
            self.canvas.create_image(421, 297, anchor=tk.CENTER, image=self.img_tk)  # Center the image
            self.canvas.config(scrollregion=self.canvas.bbox(tk.ALL))

    def load_camera(self):
        while True:
            ret, frame = self.cap.read()
            if not ret:
                break

            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            results = self.hands.process(frame_rgb)

            if results.multi_hand_landmarks:
                for hand_landmarks in results.multi_hand_landmarks:
                    self.detect_gesture(hand_landmarks)

            cv2.imshow("Camera", frame)
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break

        self.cap.release()
        cv2.destroyAllWindows()

    def detect_gesture(self, hand_landmarks):
        finger_count = 0

        # Count the number of fingers shown
        if hand_landmarks.landmark[self.mp_hands.HandLandmark.INDEX_FINGER_TIP].y < hand_landmarks.landmark[self.mp_hands.HandLandmark.INDEX_FINGER_MCP].y:
            finger_count += 1
        if hand_landmarks.landmark[self.mp_hands.HandLandmark.MIDDLE_FINGER_TIP].y < hand_landmarks.landmark[self.mp_hands.HandLandmark.MIDDLE_FINGER_MCP].y:
            finger_count += 1

        current_time = time.time()
        
        # Process gestures based on finger count and time since last gesture
        if finger_count == 1 and current_time - self.last_gesture_time >= self.gesture_delay:
            self.move_to_next_page()
            self.last_gesture_time = current_time  # Update last gesture time
        elif finger_count == 2 and current_time - self.last_gesture_time >= self.gesture_delay:
            self.move_to_previous_page()
            self.last_gesture_time = current_time  # Update last gesture time

    def move_to_next_page(self):
        if self.doc and self.current_page < len(self.doc) - 1:
            self.current_page += 1
            self.load_page()

    def move_to_previous_page(self):
        if self.doc and self.current_page > 0:
            self.current_page -= 1
            self.load_page()

    def zoom_in(self):
        self.zoom_factor *= 1.1  # Increase zoom factor by 10%
        self.load_page()  # Reload the page with new zoom factor

    def zoom_out(self):
        self.zoom_factor /= 1.1  # Decrease zoom factor by 10%
        self.load_page()  # Reload the page with new zoom factor

if __name__ == "__main__":
    root = tk.Tk()
    pdf_viewer = PDFViewer(root)
    root.mainloop()
