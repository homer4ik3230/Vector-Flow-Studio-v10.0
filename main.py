import customtkinter as ctk
from tkinter import filedialog, messagebox, Canvas
from PIL import Image, ImageTk, ImageFilter
import vtracer
import os
import threading
from svglib.svglib import svg2rlg
from reportlab.graphics import renderPM

class VectorFlowStudio(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Vector Flow Studio v10.0 - Ultimate")
        self.geometry("1400x900")
        
        # Установка иконки окна
        try:
            if os.path.exists("icon.ico"):
                self.iconbitmap("icon.ico")
        except:
            pass

        # Состояние приложения
        self.current_img = None
        self.svg_data = None
        self.history = []
        self.history_index = -1
        
        # Переменные для обрезки
        self.crop_start_x = None
        self.crop_start_y = None
        self.rect_id = None

        self._setup_ui()

    def _setup_ui(self):
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # ЛЕВАЯ ПАНЕЛЬ
        self.sidebar = ctk.CTkFrame(self, width=300, corner_radius=0)
        self.sidebar.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)

        ctk.CTkLabel(self.sidebar, text="VECTOR FLOW V10", font=("Arial", 24, "bold")).pack(pady=20)
        
        ctk.CTkButton(self.sidebar, text="📂 ОТКРЫТЬ ФОТО", command=self.open_image, fg_color="#2fa572").pack(pady=10, padx=20)

        # Кнопки Истории
        hist_frame = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        hist_frame.pack(pady=10)
        self.btn_undo = ctk.CTkButton(hist_frame, text="⟲ Назад", width=100, command=self.undo).pack(side="left", padx=5)
        self.btn_redo = ctk.CTkButton(hist_frame, text="⟳ Вперед", width=100, command=self.redo).pack(side="left", padx=5)

        # Панель подтверждения обрезки (скрыта)
        self.crop_panel = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        ctk.CTkButton(self.crop_panel, text="✅ ПРИМЕНИТЬ ОБРЕЗКУ", fg_color="green", command=self.apply_crop).pack(pady=5, padx=20)
        ctk.CTkButton(self.crop_panel, text="❌ ОТМЕНА", fg_color="red", command=self.cancel_crop).pack(pady=5, padx=20)

        # Настройки векторизации
        ctk.CTkLabel(self.sidebar, text="ДЕТАЛИЗАЦИЯ (1-8):").pack(pady=(20, 0))
        self.detail_slider = ctk.CTkSlider(self.sidebar, from_=1, to=8, number_of_steps=7)
        self.detail_slider.set(4)
        self.detail_slider.pack(pady=10, padx=20)

        self.btn_vector = ctk.CTkButton(self.sidebar, text="⚡ ВЕКТОРИЗОВАТЬ", command=self.start_vector_thread, fg_color="#1f538d")
        self.btn_vector.pack(pady=20, padx=20)

        ctk.CTkButton(self.sidebar, text="💾 СОХРАНИТЬ КАК...", command=self.save_file, fg_color="gray30").pack(pady=10, padx=20)

        # ПРАВАЯ ПАНЕЛЬ (Холст)
        self.canvas = Canvas(self, bg="#1a1a1a", bd=0, highlightthickness=0)
        self.canvas.grid(row=0, column=1, sticky="nsew", padx=20, pady=20)
        
        # Бинды для обрезки
        self.canvas.bind("<ButtonPress-1>", self.on_crop_start)
        self.canvas.bind("<B1-Motion>", self.on_crop_drag)

    # --- ФУНКЦИИ ---

    def open_image(self):
        path = filedialog.askopenfilename(filetypes=[("Изображения", "*.png *.jpg *.jpeg *.webp")])
        if path:
            img = Image.open(path).convert("RGB")
            self.history = []
            self.add_to_history(img)

    def add_to_history(self, img):
        if self.history_index < len(self.history) - 1:
            self.history = self.history[:self.history_index + 1]
        self.history.append(img.copy())
        if len(self.history) > 20: self.history.pop(0)
        self.history_index = len(self.history) - 1
        self.current_img = img
        self.render_canvas(img)

    def render_canvas(self, img):
        self.update_idletasks()
        canvas_w = self.canvas.winfo_width()
        canvas_h = self.canvas.winfo_height()
        if canvas_w < 10: canvas_w, canvas_h = 1000, 800
        
        disp_img = img.copy()
        disp_img.thumbnail((canvas_w, canvas_h))
        self.tk_img = ImageTk.PhotoImage(disp_img)
        self.canvas.delete("all")
        self.canvas.create_image(canvas_w//2, canvas_h//2, image=self.tk_img)

    # Логика обрезки
    def on_crop_start(self, event):
        if not self.current_img: return
        self.crop_start_x = event.x
        self.crop_start_y = event.y
        if self.rect_id: self.canvas.delete(self.rect_id)
        self.rect_id = self.canvas.create_rectangle(event.x, event.y, event.x, event.y, outline="yellow", dash=(4,4), width=2)
        self.crop_panel.pack(pady=10)

    def on_crop_drag(self, event):
        if self.rect_id:
            self.canvas.coords(self.rect_id, self.crop_start_x, self.crop_start_y, event.x, event.y)

    def apply_crop(self):
        try:
            coords = self.canvas.coords(self.rect_id)
            cw, ch = self.canvas.winfo_width(), self.canvas.winfo_height()
            iw, ih = self.current_img.size
            ratio = min(cw/iw, ch/ih)
            ox, oy = (cw - iw*ratio)/2, (ch - ih*ratio)/2
            
            x1 = (coords[0] - ox) / ratio
            y1 = (coords[1] - oy) / ratio
            x2 = (coords[2] - ox) / ratio
            y2 = (coords[3] - oy) / ratio
            
            cropped = self.current_img.crop((min(x1, x2), min(y1, y2), max(x1, x2), max(y1, y2)))
            self.add_to_history(cropped)
            self.cancel_crop()
        except:
            messagebox.showwarning("Внимание", "Ошибка области обрезки")

    def cancel_crop(self):
        if self.rect_id: self.canvas.delete(self.rect_id)
        self.crop_panel.pack_forget()

    # Логика векторизации
    def start_vector_thread(self):
        if self.current_img:
            threading.Thread(target=self.run_vtracer, daemon=True).start()

    def run_vtracer(self):
        try:
            self.current_img.save("v_in.png")
            vtracer.convert("v_in.png", "v_out.svg", iteration_count=int(self.detail_slider.get()))
            with open("v_out.svg", "r") as f: self.svg_data = f.read()
            
            # Рендерим предпросмотр вектора
            drawing = svg2rlg("v_out.svg")
            renderPM.drawToFile(drawing, "v_pre.png", fmt="PNG")
            preview = Image.open("v_pre.png")
            self.after(0, lambda: self.render_canvas(preview))
            messagebox.showinfo("Успех", "Изображение векторизовано!")
        except Exception as e:
            self.after(0, lambda: messagebox.showerror("Ошибка", f"Ошибка vtracer: {e}"))

    def save_file(self):
        if not self.svg_data:
            return messagebox.showwarning("Внимание", "Сначала векторизуйте изображение!")
        path = filedialog.asksaveasfilename(defaultextension=".svg", 
                                             filetypes=[("SVG Vector", "*.svg"), ("PNG Image", "*.png")])
        if path:
            if path.endswith(".svg"):
                with open(path, "w") as f: f.write(self.svg_data)
            else:
                self.current_img.save(path)
            messagebox.showinfo("Готово", "Файл сохранен!")

    def undo(self):
        if self.history_index > 0:
            self.history_index -= 1
            self.current_img = self.history[self.history_index]
            self.render_canvas(self.current_img)

    def redo(self):
        if self.history_index < len(self.history) - 1:
            self.history_index += 1
            self.current_img = self.history[self.history_index]
            self.render_canvas(self.current_img)

if __name__ == "__main__":
    app = VectorFlowStudio()
    app.mainloop()
