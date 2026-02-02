import customtkinter as ctk
from tkinter import messagebox, ttk, simpledialog
import tkinter as tk
import sqlite3
import os
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import matplotlib
from datetime import datetime, date
import calendar
import requests
from io import BytesIO
from PIL import Image, ImageTk

# --- CẤU HÌNH GIAO DIỆN ---
ctk.set_appearance_mode("Light")
ctk.set_default_color_theme("blue")

# Màu sắc
COLOR_BG_LOGIN = "#6a11cb"      
COLOR_PRIMARY = "#3498db"       
COLOR_SUCCESS = "#2ecc71"       
COLOR_DANGER = "#e74c3c"        
COLOR_HEADER = "#2c3e50"        
COLOR_TEXT = "#2d3436"          

# Font chữ
FONT_TITLE = ("Arial", 24, "bold")
FONT_BOLD = ("Arial", 13, "bold")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "restaurant.db")

# Thông tin VietQR
BANK_ID = "mbbank"
ACCOUNT_NO = "0842214819"
ACCOUNT_NAME = "NGO THI TRA MY"

# --- 1. POPUP THÊM/SỬA/XÓA MENU (ADMIN) ---
class MenuPopup(ctk.CTkToplevel):
    def __init__(self, parent, action="add", item_data=None):
        super().__init__(parent)
        self.action = action
        self.item_data = item_data 
        title = "Thêm món mới" if action == "add" else "Sửa món ăn"
        self.title(title)
        self.geometry("500x500") # Tăng chiều cao để chứa nút Xóa
        self.resizable(False, False)
        self.attributes("-topmost", True)
        self.result = None
        
        self.update_idletasks()
        x = (self.winfo_screenwidth() - 500) // 2
        y = (self.winfo_screenheight() - 500) // 2
        self.geometry(f"+{x}+{y}")
        self.configure(fg_color="white")
        self.lift(); self.focus_force(); self.grab_set()

        ctk.CTkLabel(self, text=title.upper(), font=("Arial", 22, "bold"), text_color=COLOR_PRIMARY).pack(pady=(30, 20))

        # Tên món
        ctk.CTkLabel(self, text="Tên món:", font=FONT_BOLD, text_color="black").pack(anchor="w", padx=50)
        self.entry_name = ctk.CTkEntry(self, width=400, height=40)
        self.entry_name.pack(pady=(5, 15))

        # Danh mục
        ctk.CTkLabel(self, text="Danh mục:", font=FONT_BOLD, text_color="black").pack(anchor="w", padx=50)
        self.combo_cat = ctk.CTkComboBox(self, width=400, height=40, values=["Món ăn", "Đồ uống", "Khác"])
        self.combo_cat.pack(pady=(5, 15))

        # Giá tiền
        ctk.CTkLabel(self, text="Giá tiền (VNĐ):", font=FONT_BOLD, text_color="black").pack(anchor="w", padx=50)
        self.entry_price = ctk.CTkEntry(self, width=400, height=40, placeholder_text="VD: 45000 hoặc 45,000")
        self.entry_price.pack(pady=(5, 15))

        # Điền dữ liệu cũ nếu là Edit
        if action == "edit" and item_data:
            self.entry_name.insert(0, item_data[1])
            self.combo_cat.set(item_data[2])
            # Hiển thị giá có dấu phẩy cho dễ nhìn
            price_str = f"{int(float(item_data[3])):,}"
            self.entry_price.insert(0, price_str)

        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(side="bottom", pady=30, fill="x", padx=50)
        
        # Nút Hủy & Lưu
        ctk.CTkButton(btn_frame, text="Hủy", fg_color="gray", width=100, height=45, command=self.destroy).pack(side="left")
        ctk.CTkButton(btn_frame, text="LƯU LẠI", fg_color=COLOR_SUCCESS, width=150, height=45, 
                      font=("Arial", 14, "bold"), command=self.save).pack(side="right")

        # NẾU LÀ SỬA -> THÊM NÚT XÓA Ở GIỮA
        if action == "edit":
            ctk.CTkButton(btn_frame, text="XÓA MÓN NÀY", fg_color=COLOR_DANGER, width=120, height=45,
                          font=("Arial", 12, "bold"), command=self.delete_item).pack(side="right", padx=10)

    def delete_item(self):
        # Xác nhận xóa
        if messagebox.askyesno("Xác nhận xóa", f"Bạn có chắc chắn muốn xóa món:\n{self.item_data[1]}?", parent=self):
            con = sqlite3.connect(DB_PATH)
            con.execute("DELETE FROM menu WHERE id=?", (self.item_data[0],))
            con.commit()
            con.close()
            self.result = "DELETED" # Đánh dấu là đã xóa
            self.destroy()

    def save(self):
        name = self.entry_name.get().strip()
        cat = self.combo_cat.get()
        # Xử lý giá tiền: Cho phép nhập "45,000" -> Xóa dấu phẩy -> 45000
        price_raw = self.entry_price.get().strip().replace(",", "").replace(".", "") 

        if not name or not price_raw:
            messagebox.showwarning("Thiếu thông tin", "Vui lòng nhập tên và giá!", parent=self)
            return
        
        try:
            price_float = float(price_raw)
        except ValueError:
            messagebox.showerror("Lỗi", "Giá tiền phải là số (VD: 45000)", parent=self)
            return

        self.result = (name, cat, price_float)
        self.destroy()

# --- 2. POPUP THÔNG BÁO HÓA ĐƠN ---
class InvoicePopup(ctk.CTkToplevel):
    def __init__(self, parent, filename, close_callback):
        super().__init__(parent)
        self.filename = filename
        self.close_callback = close_callback
        self.title("Thanh toán thành công")
        self.geometry("500x350")
        self.resizable(False, False)
        self.attributes("-topmost", True)
        self.update_idletasks()
        x = (self.winfo_screenwidth() - 500) // 2
        y = (self.winfo_screenheight() - 350) // 2
        self.geometry(f"+{x}+{y}")
        self.configure(fg_color="white")
        self.lift(); self.focus_force(); self.grab_set()

        ctk.CTkLabel(self, text="✔", font=("Arial", 60), text_color=COLOR_SUCCESS).pack(pady=(20, 0))
        ctk.CTkLabel(self, text="THANH TOÁN THÀNH CÔNG!", font=("Arial", 22, "bold"), text_color=COLOR_SUCCESS).pack(pady=(10, 10))
        ctk.CTkLabel(self, text=f"Đã xuất hóa đơn: {os.path.basename(filename)}", font=("Arial", 12), text_color="gray").pack(pady=5)

        btn_frame = ctk.CTkFrame(self, fg_color="transparent"); btn_frame.pack(side="bottom", pady=30, fill="x", padx=40)
        ctk.CTkButton(btn_frame, text="Mở lại File", fg_color="#95a5a6", width=120, height=45, command=self.open_file).pack(side="left")
        ctk.CTkButton(btn_frame, text="HOÀN TẤT", fg_color=COLOR_PRIMARY, width=280, height=45, font=("Arial", 14, "bold"), command=self.on_close).pack(side="right")

    def open_file(self):
        try: os.system(f"notepad.exe {self.filename}")
        except: pass
    def on_close(self):
        self.destroy(); 
        if self.close_callback: self.close_callback()

# --- 3. POPUP THÀNH CÔNG CHUNG ---
class SuccessPopup(ctk.CTkToplevel):
    def __init__(self, parent, title, message, callback=None):
        super().__init__(parent)
        self.callback = callback
        self.title(title)
        self.geometry("500x300")
        self.resizable(False, False)
        self.attributes("-topmost", True)
        self.update_idletasks()
        x = (self.winfo_screenwidth() - 500) // 2
        y = (self.winfo_screenheight() - 300) // 2
        self.geometry(f"+{x}+{y}")
        self.configure(fg_color="white")
        self.lift(); self.focus_force(); self.grab_set()

        ctk.CTkLabel(self, text="✔", font=("Arial", 60), text_color=COLOR_SUCCESS).pack(pady=(20, 0))
        ctk.CTkLabel(self, text=title.upper(), font=("Arial", 22, "bold"), text_color=COLOR_SUCCESS).pack(pady=(5, 10))
        ctk.CTkLabel(self, text=message, font=("Arial", 14), text_color="gray").pack(pady=5)

        ctk.CTkButton(self, text="ĐÓNG (OK)", fg_color=COLOR_PRIMARY, width=200, height=45, 
                      font=("Arial", 14, "bold"), command=self.on_close).pack(side="bottom", pady=30)

    def on_close(self):
        self.destroy()
        if self.callback: self.callback()

# --- 4. POPUP XÁC NHẬN ---
class ConfirmPopup(ctk.CTkToplevel):
    def __init__(self, parent, title, message, confirm_command):
        super().__init__(parent)
        self.title(title); self.geometry("500x300"); self.resizable(False, False); self.attributes("-topmost", True)
        self.update_idletasks(); x = (self.winfo_screenwidth() - 500) // 2; y = (self.winfo_screenheight() - 300) // 2; self.geometry(f"+{x}+{y}"); self.configure(fg_color="white")
        self.confirm_command = confirm_command
        self.lift(); self.focus_force(); self.grab_set()

        ctk.CTkLabel(self, text="⚠️ XÁC NHẬN", font=("Arial", 24, "bold"), text_color=COLOR_PRIMARY).pack(pady=(30, 15))
        ctk.CTkLabel(self, text=message, font=("Arial", 15), text_color="#333", wraplength=400).pack(pady=10)
        
        btn_frame = ctk.CTkFrame(self, fg_color="transparent"); btn_frame.pack(side="bottom", pady=30, fill="x", padx=40)
        ctk.CTkButton(btn_frame, text="Quay lại", fg_color="gray", width=150, height=45, command=self.destroy).pack(side="left")
        ctk.CTkButton(btn_frame, text="ĐỒNG Ý", fg_color=COLOR_SUCCESS, width=220, height=45, font=("Arial", 13, "bold"), command=self.on_confirm).pack(side="right")

    def on_confirm(self): 
        self.destroy()
        self.update() 
        if self.confirm_command: self.confirm_command()

# --- 5. POPUP LỊCH ---
class CalendarPopup(ctk.CTkToplevel):
    def __init__(self, parent, callback):
        super().__init__(parent)
        self.callback = callback; self.title("Chọn ngày"); self.geometry("350x350"); self.resizable(False, False); self.attributes("-topmost", True)
        self.update_idletasks(); x = (self.winfo_screenwidth() - 350) // 2; y = (self.winfo_screenheight() - 350) // 2; self.geometry(f"+{x}+{y}"); self.configure(fg_color="white")
        self.lift(); self.focus_force(); self.grab_set()
        self.current_date = datetime.now(); self.year = self.current_date.year; self.month = self.current_date.month
        header = ctk.CTkFrame(self, fg_color="#f1f2f6", height=50); header.pack(fill="x")
        ctk.CTkButton(header, text="<", width=40, fg_color="transparent", text_color="black", command=self.prev_month).pack(side="left", padx=5)
        self.lbl_month = ctk.CTkLabel(header, text=f"Tháng {self.month}/{self.year}", font=("Arial", 16, "bold")); self.lbl_month.pack(side="left", expand=True)
        ctk.CTkButton(header, text=">", width=40, fg_color="transparent", text_color="black", command=self.next_month).pack(side="right", padx=5)
        self.body = ctk.CTkFrame(self, fg_color="white"); self.body.pack(fill="both", expand=True, padx=10, pady=10); self.render_calendar()

    def render_calendar(self):
        for w in self.body.winfo_children(): w.destroy()
        days = ["T2", "T3", "T4", "T5", "T6", "T7", "CN"]
        for i, d in enumerate(days): ctk.CTkLabel(self.body, text=d, font=("Arial", 12, "bold"), text_color="gray").grid(row=0, column=i, padx=2, pady=5)
        cal = calendar.monthcalendar(self.year, self.month)
        for r, week in enumerate(cal):
            for c, day in enumerate(week):
                if day != 0:
                    btn = ctk.CTkButton(self.body, text=str(day), width=35, height=35, fg_color="white", border_width=1, border_color="#ecf0f1", text_color="black", hover_color="#3498db", command=lambda d=day: self.select_date(d))
                    if day == datetime.now().day and self.month == datetime.now().month and self.year == datetime.now().year: btn.configure(fg_color="#dff9fb", border_color="#3498db", text_color="#3498db")
                    btn.grid(row=r+1, column=c, padx=2, pady=2)
    def prev_month(self): self.month -= 1; self.month = 12 if self.month < 1 else self.month; self.year -= 1 if self.month == 12 else 0; self.lbl_month.configure(text=f"Tháng {self.month}/{self.year}"); self.render_calendar()
    def next_month(self): self.month += 1; self.month = 1 if self.month > 12 else self.month; self.year += 1 if self.month == 1 else 0; self.lbl_month.configure(text=f"Tháng {self.month}/{self.year}"); self.render_calendar()
    def select_date(self, day): self.callback(f"{day:02d}/{self.month:02d}/{self.year}"); self.destroy()

# --- 6. POPUP ORDER ---
class OrderPopup(ctk.CTkToplevel):
    def __init__(self, parent, item_name, price, current_qty=1, current_note=""):
        super().__init__(parent)
        self.title("Chi tiết món"); self.geometry("500x450"); self.resizable(False, False); self.attributes("-topmost", True)
        self.result = None; self.update_idletasks(); x = (self.winfo_screenwidth() - 500) // 2; y = (self.winfo_screenheight() - 450) // 2; self.geometry(f"+{x}+{y}"); self.configure(fg_color="white")
        self.lift(); self.focus_force(); self.grab_set()
        ctk.CTkLabel(self, text=item_name, font=("Arial", 24, "bold"), text_color=COLOR_PRIMARY).pack(pady=(30, 5))
        ctk.CTkLabel(self, text=f"{price} VNĐ", font=("Arial", 18), text_color="gray").pack(pady=(0, 20))
        frame_qty = ctk.CTkFrame(self, fg_color="transparent"); frame_qty.pack(pady=10)
        ctk.CTkLabel(frame_qty, text="Số lượng:", font=FONT_BOLD, text_color="black").pack(side="left", padx=10)
        self.qty_var = tk.StringVar(value=str(current_qty))
        ctk.CTkButton(frame_qty, text="-", width=40, height=40, font=("Arial", 18, "bold"), fg_color="#bdc3c7", command=lambda: self.change_qty(-1)).pack(side="left", padx=5)
        self.entry_qty = ctk.CTkEntry(frame_qty, textvariable=self.qty_var, width=60, height=40, font=("Arial", 18), justify="center"); self.entry_qty.pack(side="left", padx=5)
        ctk.CTkButton(frame_qty, text="+", width=40, height=40, font=("Arial", 18, "bold"), fg_color="#bdc3c7", command=lambda: self.change_qty(1)).pack(side="left", padx=5)
        ctk.CTkLabel(self, text="Ghi chú:", font=FONT_BOLD, text_color="black").pack(pady=(20, 5), anchor="w", padx=40)
        self.entry_note = ctk.CTkEntry(self, placeholder_text="Ví dụ: Không hành...", width=420, height=50); self.entry_note.insert(0, current_note); self.entry_note.pack(pady=5)
        ctk.CTkLabel(self, text="*Nhập số lượng 0 để hủy món này khỏi giỏ", font=("Arial", 10, "italic"), text_color="red").pack(pady=5)
        btn_frame = ctk.CTkFrame(self, fg_color="transparent"); btn_frame.pack(side="bottom", pady=30, fill="x", padx=40)
        ctk.CTkButton(btn_frame, text="Hủy bỏ", fg_color="gray", width=120, height=45, command=self.destroy).pack(side="left")
        ctk.CTkButton(btn_frame, text="XÁC NHẬN", fg_color=COLOR_SUCCESS, width=280, height=45, font=("Arial", 14, "bold"), command=self.confirm).pack(side="right")
    def change_qty(self, delta):
        try: val = int(self.qty_var.get()) + delta
        except: val = 1
        if val < 0: val = 0 
        self.qty_var.set(str(val))
    def confirm(self):
        try: q = int(self.qty_var.get())
        except: q = 1
        self.result = (q, self.entry_note.get()); self.destroy()

# --- 7. POPUP CHI TIẾT THU NGÂN ---
class CashierDetailPopup(ctk.CTkToplevel):
    def __init__(self, parent, order_id, table_name, cashier_page):
        super().__init__(parent)
        self.order_id = order_id
        self.cashier_page = cashier_page
        self.table_name = table_name
        self.title(f"Thanh toán Chuyển khoản - {table_name}")
        self.geometry("600x700")
        self.attributes("-topmost", True)
        self.grab_set()

        # Tiêu đề
        ctk.CTkLabel(self, text=f"QUÉT MÃ QR THANH TOÁN", font=("Arial", 20, "bold")).pack(pady=20)
        
        # Vùng hiển thị mã QR
        self.qr_label = ctk.CTkLabel(self, text="Đang tạo mã QR...", fg_color="#f1f2f6", width=300, height=300, corner_radius=10)
        self.qr_label.pack(pady=10)

        # Thông tin số tiền
        self.lbl_amount = ctk.CTkLabel(self, text="Tổng tiền: 0 VNĐ", font=("Arial", 18, "bold"), text_color="#2ecc71")
        self.lbl_amount.pack(pady=10)

        # Nút xác nhận sau khi khách đã chuyển
        ctk.CTkButton(self, text="XÁC NHẬN ĐÃ NHẬN TIỀN", fg_color=COLOR_SUCCESS, height=50,
                     command=lambda: self.cashier_page.pay(self.order_id, self.table_name, "Chuyển khoản", self)).pack(pady=20)

        self.generate_qr_data()

    def generate_qr_data(self):
        # 1. Lấy tổng tiền
        con = sqlite3.connect(DB_PATH)
        res = con.execute("""
            SELECT SUM(m.price * oi.qty) 
            FROM order_items oi 
            JOIN menu m ON oi.menu_id=m.id 
            WHERE oi.order_id=? AND oi.status != 'Cancelled'
        """, (self.order_id,)).fetchone()
        total = res[0] if res[0] else 0
        con.close()

        self.lbl_amount.configure(text=f"Tổng tiền: {total:,.0f} VNĐ")

        # 2. Gọi API bằng requests (ổn định hơn)
        qr_url = f"https://img.vietqr.io/image/mbbank-0842214819-compact2.png?amount={total}&addInfo=Ban_{self.table_name}_HD_{self.order_id}"
        
        try:
            import requests
            from PIL import Image, ImageTk
            from io import BytesIO

            response = requests.get(qr_url, timeout=10)
            img = Image.open(BytesIO(response.content)).resize((300, 300))
            
            self.photo = ImageTk.PhotoImage(img) 
            self.qr_label.configure(image=self.photo, text="")
        except Exception as e:
            print(f"Lỗi tải QR: {e}")
            self.qr_label.configure(text="Lỗi kết nối Internet!")

# --- CLASS XỬ LÝ VIETQR ---
class QRService:
    @staticmethod
    def get_qr(amount, order_id):
        desc = f"Thanh toan don {order_id}"
        qr_url = f"https://img.vietqr.io/image/mbbank-0842214819-compact2.png?amount={amount}&addInfo=Thanh toan don {oid}&accountName=NGO THI TRA MY"
        try:
            response = requests.get(url, timeout=5)
            img = Image.open(BytesIO(response.content))
            return ImageTk.PhotoImage(img.resize((220, 220)))
        except:
            return None

# --- MAIN APP ---
class RestaurantApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Hệ thống Quản lý Nhà hàng - Ultimate Edition")
        self.after(0, lambda: self.state('zoomed'))
        self.create_test_users(); self.update_db_structure()
        self.current_user = None
        self.container = ctk.CTkFrame(self, fg_color="#f1f2f6"); self.container.pack(side="top", fill="both", expand=True)
        self.container.grid_rowconfigure(0, weight=1); self.container.grid_columnconfigure(0, weight=1)
        self.frames = {}
        for F in (LoginPage, TablePage, OrderPage, KitchenPage, CashierPage, ReportPage, MenuPage):
            page_name = F.__name__; frame = F(parent=self.container, controller=self)
            self.frames[page_name] = frame; frame.grid(row=0, column=0, sticky="nsew")
        self.show_frame("LoginPage")

    def create_test_users(self):
        try:
            con = sqlite3.connect(DB_PATH)
            users = [('admin', '123', 'admin'), ('staff', '123', 'staff'), ('cashier', '123', 'cashier'), ('kitchen', '123', 'kitchen')]
            for u in users:
                try: con.execute("INSERT INTO users (username, password, role) VALUES (?, ?, ?)", u)
                except: pass
            con.commit(); con.close()
        except: pass

    def update_db_structure(self):
        try:
            con = sqlite3.connect(DB_PATH)
            try: con.execute("ALTER TABLE orders ADD COLUMN payment_method TEXT DEFAULT 'Tiền mặt'")
            except: pass
            try: con.execute("ALTER TABLE order_items ADD COLUMN note TEXT DEFAULT ''")
            except: pass
            con.commit(); con.close()
        except: pass

    def show_frame(self, page_name, **kwargs):
        frame = self.frames[page_name]
        if hasattr(frame, "on_show"): frame.on_show(**kwargs)
        frame.tkraise()

# --- LOGIN PAGE ---
class LoginPage(ctk.CTkFrame):
    def __init__(self, parent, controller):
        super().__init__(parent, fg_color=COLOR_BG_LOGIN)
        self.controller = controller
        card = ctk.CTkFrame(self, fg_color="white", width=420, height=600, corner_radius=20)
        card.place(relx=0.5, rely=0.5, anchor="center"); card.pack_propagate(False)
        ctk.CTkLabel(card, text="Hệ Thống Quản Lý", font=("Arial", 28, "bold"), text_color="#333").pack(pady=(50, 20))
        self.entry_u = ctk.CTkEntry(card, placeholder_text="Tên đăng nhập", width=340, height=50, fg_color="#f7f9fa", text_color="black", border_width=1, corner_radius=10); self.entry_u.pack(pady=10)
        self.entry_p = ctk.CTkEntry(card, placeholder_text="Mật khẩu", show="*", width=340, height=50, fg_color="#f7f9fa", text_color="black", border_width=1, corner_radius=10); self.entry_p.pack(pady=10)
        ctk.CTkButton(card, text="ĐĂNG NHẬP", width=340, height=50, fg_color=COLOR_PRIMARY, font=("Arial", 14, "bold"), corner_radius=10, hover_color="#2980b9", command=self.login_logic).pack(pady=20)
        hint_frame = ctk.CTkFrame(card, fg_color="#f1f2f6", corner_radius=10); hint_frame.pack(pady=10, padx=20, fill="x")
        ctk.CTkLabel(hint_frame, text="Tài khoản Test:", font=("Arial", 12, "bold"), text_color="#333").pack(anchor="w", padx=10, pady=(5,0))
        ctk.CTkLabel(hint_frame, text="👑 Admin: admin / 123\n💰 Thu ngân: cashier / 123\n👨‍🍳 Bếp: kitchen / 123\n💁 Phục vụ: staff / 123", font=("Arial", 11), justify="left", text_color="#555").pack(anchor="w", padx=10, pady=(0,5))
        ctk.CTkButton(self, text="Thoát", width=80, fg_color="transparent", border_width=1, border_color="white", text_color="white", command=lambda: controller.destroy()).place(relx=0.95, rely=0.05, anchor="center")

    def login_logic(self):
        u, p = self.entry_u.get(), self.entry_p.get()
        try:
            con = sqlite3.connect(DB_PATH); con.row_factory = sqlite3.Row
            user = con.execute("SELECT * FROM users WHERE username=? AND password=?", (u, p)).fetchone()
            con.close()
            if user:
                self.controller.current_user = dict(user)
                role = user['role']
                # FIX ĐIỀU HƯỚNG BẾP & THU NGÂN
                if role == 'kitchen': self.controller.show_frame("KitchenPage")
                elif role == 'cashier': self.controller.show_frame("CashierPage")
                else: self.controller.show_frame("TablePage")
            else: messagebox.showerror("Lỗi", "Sai tài khoản hoặc mật khẩu!")
        except: messagebox.showerror("Lỗi", "Chưa có Database!")

# --- NAVBAR ---
class NavBar(ctk.CTkFrame):
    def __init__(self, parent, controller, title):
        super().__init__(parent, fg_color=COLOR_HEADER, height=70, corner_radius=0)
        self.controller = controller
        self.pack(fill="x", side="top")
        ctk.CTkLabel(self, text=title, font=("Arial", 22, "bold"), text_color="white").pack(side="left", padx=30, pady=15)
        self.btn_frame = ctk.CTkFrame(self, fg_color="transparent"); self.btn_frame.pack(side="right", padx=20)
        self.update_buttons()

    def update_buttons(self):
        for widget in self.btn_frame.winfo_children(): widget.destroy()
        user = self.controller.current_user
        if not user: return
        role = user['role']
        def add_btn(txt, cmd, color="transparent"):
            ctk.CTkButton(self.btn_frame, text=txt, fg_color=color, width=120, height=35, command=cmd).pack(side="left", padx=5)
        is_admin = role in ['admin', 'manager']
        
        # LOGIC MENU ĐÚNG
        if is_admin or role == 'staff': add_btn("Sơ đồ bàn", lambda: self.controller.show_frame("TablePage"))
        if is_admin or role == 'kitchen': add_btn("Nhà Bếp", lambda: self.controller.show_frame("KitchenPage"))
        if is_admin or role == 'cashier': 
            add_btn("Thu Ngân", lambda: self.controller.show_frame("CashierPage"))
            add_btn("Báo Cáo", lambda: self.controller.show_frame("ReportPage"))
        if is_admin: add_btn("Quản lý Menu", lambda: self.controller.show_frame("MenuPage"))
            
        add_btn("Đăng xuất", lambda: self.controller.show_frame("LoginPage"), COLOR_DANGER)

# --- MENU PAGE (ADMIN) ---
class MenuPage(ctk.CTkFrame):
    def __init__(self, parent, controller):
        super().__init__(parent, fg_color="white")
        self.controller = controller
        self.nav = NavBar(self, controller, "⚙️ QUẢN LÝ THỰC ĐƠN")
        head = ctk.CTkFrame(self, fg_color="transparent"); head.pack(fill="x", padx=40, pady=20)
        ctk.CTkButton(head, text="⬅ Quay lại", fg_color="gray", width=100, command=lambda: controller.show_frame("TablePage")).pack(side="left")
        ctk.CTkButton(head, text="✚ THÊM MÓN MỚI", fg_color=COLOR_SUCCESS, width=150, font=("Arial", 13, "bold"), command=self.add_item).pack(side="right")
        self.tree = ttk.Treeview(self, columns=("ID", "Tên món", "Danh mục", "Giá"), show="headings", height=15)
        self.tree.heading("ID", text="ID"); self.tree.column("ID", width=50, anchor="center")
        self.tree.heading("Tên món", text="Tên món"); self.tree.column("Tên món", width=250)
        self.tree.heading("Danh mục", text="Danh mục"); self.tree.column("Danh mục", width=150, anchor="center")
        self.tree.heading("Giá", text="Giá tiền"); self.tree.column("Giá", width=150, anchor="center")
        self.tree.pack(fill="both", expand=True, padx=40, pady=10)
        self.tree.bind("<Double-1>", self.edit_item)
        ctk.CTkLabel(self, text="* Nhấn đúp chuột vào món ăn để Sửa hoặc Xóa", text_color="gray").pack(pady=10)

    def on_show(self): self.nav.update_buttons(); self.load_menu()
    def load_menu(self):
        for i in self.tree.get_children(): self.tree.delete(i)
        con = sqlite3.connect(DB_PATH)
        items = con.execute("SELECT id, name, category, price FROM menu ORDER BY category, name").fetchall()
        con.close()
        for item in items: self.tree.insert("", "end", values=(item[0], item[1], item[2], f"{int(item[3]):,}"))

    def add_item(self):
        dialog = MenuPopup(self, action="add"); self.wait_window(dialog)
        if dialog.result:
            name, cat, price = dialog.result; con = sqlite3.connect(DB_PATH)
            con.execute("INSERT INTO menu (name, category, price) VALUES (?, ?, ?)", (name, cat, price))
            con.commit(); con.close(); messagebox.showinfo("Thành công", f"Đã thêm món: {name}"); self.load_menu()

    def edit_item(self, event):
        sel = self.tree.selection(); 
        if not sel: return
        item = self.tree.item(sel[0], "values"); price_clean = item[3].replace(",", "")
        dialog = MenuPopup(self, action="edit", item_data=(item[0], item[1], item[2], price_clean)); self.wait_window(dialog)
        if dialog.result == "DELETED": self.load_menu(); return
        if dialog.result:
            name, cat, price = dialog.result; con = sqlite3.connect(DB_PATH)
            con.execute("UPDATE menu SET name=?, category=?, price=? WHERE id=?", (name, cat, price, item[0]))
            con.commit(); con.close(); messagebox.showinfo("Thành công", "Đã cập nhật món ăn."); self.load_menu()

# --- TABLE PAGE ---
class TablePage(ctk.CTkFrame):
    def __init__(self, parent, controller):
        super().__init__(parent, fg_color="#f1f2f6")
        self.controller = controller
        self.nav = NavBar(self, controller, "🏰 SƠ ĐỒ BÀN ĂN")
        self.grid_frame = ctk.CTkScrollableFrame(self, fg_color="transparent"); self.grid_frame.pack(fill="both", expand=True, padx=40, pady=40)
    def on_show(self):
        self.nav.update_buttons(); self.sync_table_status()
        for w in self.grid_frame.winfo_children(): w.destroy()
        con = sqlite3.connect(DB_PATH); con.row_factory = sqlite3.Row
        tables = con.execute("SELECT * FROM tables").fetchall(); con.close()
        for i, t in enumerate(tables):
            r, c = divmod(i, 5)
            color = COLOR_SUCCESS if t['status'] == 'Available' else COLOR_DANGER
            status_txt = "TRỐNG" if t['status'] == 'Available' else "CÓ KHÁCH"
            btn = ctk.CTkButton(self.grid_frame, text=f"{t['name']}\n\n{status_txt}", fg_color=color, width=220, height=140, corner_radius=15, font=("Arial", 18, "bold"),
                                command=lambda tid=t['id']: self.controller.show_frame("OrderPage", table_id=tid))
            btn.grid(row=r, column=c, padx=20, pady=20)
    def sync_table_status(self):
        con = sqlite3.connect(DB_PATH)
        con.execute("UPDATE tables SET status='Available'")
        con.execute("UPDATE tables SET status='Serving' WHERE id IN (SELECT table_id FROM orders WHERE status='Pending')")
        con.commit(); con.close()

# --- ORDER PAGE ---
class OrderPage(ctk.CTkFrame):
    def __init__(self, parent, controller):
        super().__init__(parent, fg_color="#f1f2f6")
        self.controller = controller; self.table_id = None; self.current_order_id = None 
        header = ctk.CTkFrame(self, fg_color="white", height=70); header.pack(fill="x")
        self.lbl_title = ctk.CTkLabel(header, text="ĐẶT MÓN", font=FONT_TITLE, text_color=COLOR_TEXT); self.lbl_title.pack(side="left", padx=30)
        ctk.CTkButton(header, text="Quay lại", fg_color="gray", width=100, command=lambda: controller.show_frame("TablePage")).pack(side="right", padx=30)
        content = ctk.CTkFrame(self, fg_color="transparent"); content.pack(fill="both", expand=True, padx=30, pady=20)
        left = ctk.CTkFrame(content, fg_color="white", corner_radius=15); left.pack(side="left", fill="both", expand=True, padx=(0, 15))
        ctk.CTkLabel(left, text="THỰC ĐƠN (Double click để chọn)", font=FONT_BOLD, text_color=COLOR_PRIMARY).pack(pady=15)
        self.setup_treeview_style()
        self.tree_menu = ttk.Treeview(left, columns=("ID", "Tên", "Giá"), show="headings", height=20)
        self.tree_menu.heading("ID", text="ID"); self.tree_menu.column("ID", width=50, anchor="center")
        self.tree_menu.heading("Tên", text="Tên món"); self.tree_menu.heading("Giá", text="Giá")
        self.tree_menu.pack(fill="both", expand=True, padx=15, pady=10)
        self.tree_menu.bind("<Double-1>", self.add_to_cart)
        right = ctk.CTkFrame(content, fg_color="white", corner_radius=15); right.pack(side="right", fill="both", expand=True, padx=(15, 0))
        ctk.CTkLabel(right, text="GIỎ HÀNG (Double click món MỚI để sửa)", font=FONT_BOLD, text_color=COLOR_DANGER).pack(pady=15)
        self.tree_order = ttk.Treeview(right, columns=("Món", "SL", "Ghi chú", "Trạng thái", "ID", "Giá"), show="headings")
        self.tree_order.heading("Món", text="Món"); self.tree_order.column("Món", width=120)
        self.tree_order.heading("SL", text="SL"); self.tree_order.column("SL", width=40, anchor="center")
        self.tree_order.heading("Ghi chú", text="Ghi chú"); self.tree_order.column("Ghi chú", width=100)
        self.tree_order.heading("Trạng thái", text="TT"); self.tree_order.column("Trạng thái", width=80, anchor="center")
        self.tree_order.column("ID", width=0, stretch=False); self.tree_order.column("Giá", width=0, stretch=False)
        self.tree_order.pack(fill="both", expand=True, padx=15, pady=10)
        self.tree_order.bind("<Double-1>", self.edit_cart_item) 
        self.tree_order.tag_configure("new", foreground="green"); self.tree_order.tag_configure("old", foreground="gray")
        btn_row = ctk.CTkFrame(right, fg_color="transparent"); btn_row.pack(fill="x", padx=15, pady=20)
        ctk.CTkButton(btn_row, text="XÁC NHẬN & GỬI BẾP", fg_color=COLOR_SUCCESS, height=50, font=("Arial", 12, "bold"), command=self.confirm_and_send).pack(fill="x")

    def setup_treeview_style(self):
        style = ttk.Style(); style.theme_use("clam")
        style.configure("Treeview", background="white", foreground="black", rowheight=35, fieldbackground="white", font=("Arial", 12))
        style.configure("Treeview.Heading", background="#dfe6e9", foreground="black", font=("Arial", 12, "bold"))

    def on_show(self, table_id):
        self.table_id = table_id; self.lbl_title.configure(text=f"ĐẶT MÓN - BÀN SỐ {table_id}"); self.load_menu(); self.load_current_order() 

    def load_menu(self):
        for i in self.tree_menu.get_children(): self.tree_menu.delete(i)
        con = sqlite3.connect(DB_PATH); con.row_factory = sqlite3.Row
        menu = con.execute("SELECT * FROM menu WHERE status='Available'").fetchall(); con.close()
        for m in menu: self.tree_menu.insert("", "end", values=(m['id'], m['name'], f"{m['price']:,.0f}"))

    def load_current_order(self):
        for i in self.tree_order.get_children(): self.tree_order.delete(i)
        con = sqlite3.connect(DB_PATH); con.row_factory = sqlite3.Row
        order = con.execute("SELECT id FROM orders WHERE table_id=? AND status='Pending'", (self.table_id,)).fetchone()
        if order:
            self.current_order_id = order['id']
            items = con.execute("""SELECT oi.id, m.name, m.price, oi.qty, oi.note, oi.menu_id FROM order_items oi JOIN menu m ON oi.menu_id=m.id WHERE oi.order_id=? AND oi.status != 'Cancelled'""", (self.current_order_id,)).fetchall()
            for item in items: self.tree_order.insert("", "end", values=(item['name'], item['qty'], item['note'], "Đã gọi", item['menu_id'], item['price']), tags=('old',))
        else: self.current_order_id = None
        con.close()

    def add_to_cart(self, event):
        sel = self.tree_menu.selection()
        if not sel: return
        val = self.tree_menu.item(sel[0], "values"); dialog = OrderPopup(self, val[1], val[2]); self.wait_window(dialog) 
        if dialog.result:
            qty, note = dialog.result
            if qty > 0: self.tree_order.insert("", "end", values=(val[1], qty, note, "Mới", val[0], val[2]), tags=('new',))

    def edit_cart_item(self, event):
        sel = self.tree_order.selection()
        if not sel: return
        item = self.tree_order.item(sel[0], "values")
        if item[3] == "Đã gọi": messagebox.showinfo("Thông báo", "Món này đã gửi bếp. Vui lòng liên hệ Thu Ngân để hủy/sửa."); return
        dialog = OrderPopup(self, item[0], item[5], current_qty=item[1], current_note=item[2]); self.wait_window(dialog)
        if dialog.result:
            new_qty, new_note = dialog.result
            if new_qty == 0: self.tree_order.delete(sel[0]) 
            else: self.tree_order.item(sel[0], values=(item[0], new_qty, new_note, "Mới", item[4], item[5]))

    def confirm_and_send(self):
        new_items = []
        for row in self.tree_order.get_children():
            vals = self.tree_order.item(row, "values")
            if vals[3] == "Mới": new_items.append(vals)
        if not new_items: messagebox.showinfo("!", "Không có món mới."); return
        ConfirmPopup(self, "Xác nhận Order", f"Bạn có chắc chắn gửi {len(new_items)} món mới xuống bếp không?", lambda: self.process_order(new_items))

    def process_order(self, new_items):
        con = sqlite3.connect(DB_PATH); cur = con.cursor()
        if not self.current_order_id:
            cur.execute("INSERT INTO orders (table_id, status) VALUES (?, 'Pending')", (self.table_id,))
            self.current_order_id = cur.lastrowid
            cur.execute("UPDATE tables SET status='Serving' WHERE id=?", (self.table_id,))
        for item in new_items: cur.execute("INSERT INTO order_items (order_id, menu_id, qty, note) VALUES (?, ?, ?, ?)", (self.current_order_id, item[4], item[1], item[2]))
        con.commit(); con.close()
        
        # --- SỬ DỤNG SUCCESS POPUP ---
        SuccessPopup(self, "Thành công", "Đã gửi đơn xuống bếp!")
        
        self.controller.show_frame("TablePage")

# --- KITCHEN PAGE ---
class KitchenPage(ctk.CTkFrame):
    def __init__(self, parent, controller):
        super().__init__(parent, fg_color="white")
        self.controller = controller
        self.nav = NavBar(self, controller, "👨‍🍳 BẾP & BAR")
        head = ctk.CTkFrame(self, fg_color=COLOR_HEADER, height=50, corner_radius=0); head.pack(fill="x", padx=30, pady=(30, 0))
        columns = [("Bàn", 80), ("Tên món", 250), ("SL", 60), ("Ghi chú", 200), ("Trạng thái", 120), ("Thao tác", 100)]
        for i, (col_name, width) in enumerate(columns):
            if col_name in ["Tên món", "Ghi chú"]: head.grid_columnconfigure(i, weight=1)
            else: head.grid_columnconfigure(i, weight=0)
            lbl = ctk.CTkLabel(head, text=col_name, text_color="white", font=FONT_BOLD, width=width, anchor="w" if col_name in ["Tên món", "Ghi chú"] else "center")
            lbl.grid(row=0, column=i, padx=5, sticky="ew")
        self.scroll = ctk.CTkScrollableFrame(self, fg_color="transparent"); self.scroll.pack(fill="both", expand=True, padx=30, pady=(0, 30))

    def on_show(self):
        self.nav.update_buttons()
        for w in self.scroll.winfo_children(): w.destroy()
        con = sqlite3.connect(DB_PATH); con.row_factory = sqlite3.Row
        items = con.execute("""SELECT oi.id, t.name as tname, m.name as mname, oi.qty, oi.note, oi.status 
            FROM order_items oi JOIN menu m ON oi.menu_id=m.id JOIN orders o ON oi.order_id=o.id 
            JOIN tables t ON o.table_id=t.id WHERE oi.status NOT IN ('Completed', 'Cancelled')""").fetchall()
        con.close()
        for i, item in enumerate(items):
            bg = "#f8f9fa" if i % 2 != 0 else "white" 
            row = ctk.CTkFrame(self.scroll, fg_color=bg, height=60); row.pack(fill="x", pady=2)
            for col_idx in [1, 3]: row.grid_columnconfigure(col_idx, weight=1)
            ctk.CTkLabel(row, text=str(item['tname']), width=80, text_color="black").grid(row=0, column=0, padx=5)
            ctk.CTkLabel(row, text=str(item['mname']), text_color="black", font=("Arial", 13, "bold"), anchor="w").grid(row=0, column=1, padx=5, sticky="ew")
            # Convert to string to avoid crash
            ctk.CTkLabel(row, text=str(item['qty']), width=60, text_color="black").grid(row=0, column=2, padx=5)
            note_txt = str(item['note']) if item['note'] else ""
            ctk.CTkLabel(row, text=note_txt, text_color="red" if note_txt else "gray", font=("Arial", 12, "italic"), anchor="w").grid(row=0, column=3, padx=5, sticky="ew")
            ctk.CTkLabel(row, text="🔥 Đang làm", text_color="#e67e22", width=120).grid(row=0, column=4, padx=5)
            ctk.CTkButton(row, text="Xong", width=80, fg_color=COLOR_SUCCESS, height=35, command=lambda x=item['id']: self.done(x)).grid(row=0, column=5, padx=5)

    def done(self, iid):
        con = sqlite3.connect(DB_PATH); con.execute("UPDATE order_items SET status='Completed' WHERE id=?", (iid,)); con.commit(); con.close(); self.on_show()

# --- CASHIER PAGE ---
class CashierPage(ctk.CTkFrame):
    def __init__(self, parent, controller):
        super().__init__(parent, fg_color="#f1f2f6")
        self.controller = controller
        self.nav = NavBar(self, controller, "💰 QUẢN LÝ THANH TOÁN")
        self.scroll = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.scroll.pack(fill="both", expand=True, padx=40, pady=40)

    def on_show(self):
        self.nav.update_buttons()
        for w in self.scroll.winfo_children(): w.destroy()
        con = sqlite3.connect(DB_PATH)
        con.row_factory = sqlite3.Row
        # Tính tổng tiền trực tiếp từ SQL để hiển thị ở danh sách
        orders = con.execute("""
            SELECT o.id, t.name, SUM(m.price*oi.qty) as total 
            FROM orders o 
            JOIN tables t ON o.table_id=t.id 
            JOIN order_items oi ON o.id=oi.order_id 
            JOIN menu m ON oi.menu_id=m.id 
            WHERE o.status='Pending' AND oi.status != 'Cancelled' 
            GROUP BY o.id
        """).fetchall()
        con.close()
        
        if not orders:
            ctk.CTkLabel(self.scroll, text="Chưa có đơn hàng nào cần thanh toán.", font=("Arial", 16)).pack(pady=50)
        for o in orders:
            self.create_order_card(o)

    def create_order_card(self, o):
        card = ctk.CTkFrame(self.scroll, fg_color="white", height=80, corner_radius=10)
        card.pack(fill="x", pady=10)
        
        lbl_info = ctk.CTkLabel(card, text=f"{o['name']} - Đơn #{o['id']}", font=("Arial", 18, "bold"), text_color="black")
        lbl_info.pack(side="left", padx=30, pady=15)
        
        btn_pay = ctk.CTkButton(card, text=f"THANH TOÁN: {o['total']:,.0f}đ", fg_color=COLOR_SUCCESS, 
                                command=lambda: self.open_detail_popup(o['id'], o['name']))
        btn_pay.pack(side="right", padx=30)

    def open_detail_popup(self, oid, tname):
        # Tạo một hộp thoại nhỏ để chọn phương thức
        choice_dialog = ctk.CTkInputDialog(text="Nhập '1' cho Tiền mặt, '2' cho Chuyển khoản:", title="Chọn phương thức")
        input_val = choice_dialog.get_input()
        
        if input_val == "1":
            # Thanh toán tiền mặt: Gọi thẳng hàm pay
            self.pay(oid, tname, "Tiền mặt", None) 
        elif input_val == "2":
            # Thanh toán chuyển khoản: Mở popup có mã QR
            CashierDetailPopup(self, oid, tname, self)
        else:
            messagebox.showwarning("Thông báo", "Vui lòng chọn phương thức thanh toán hợp lệ.")

    def pay(self, oid, tname, method, popup_instance):
        def confirm_action():
            # 1. Xuất hóa đơn ra file TRƯỚC
            self.export_pdf_invoice(oid, tname, method)

            # 2. Cập nhật Database
            con = sqlite3.connect(DB_PATH)
            con.execute("UPDATE orders SET status='Paid', payment_method=? WHERE id=?", (method, oid))
            con.execute("UPDATE tables SET status='Available' WHERE name=?", (tname,))
            con.commit()
            con.close()

            # 3. Đóng popup (nếu là chuyển khoản) và quay về màn hình thu ngân
            if popup_instance: popup_instance.destroy()
            
            # 4. Làm mới danh sách bàn đang chờ
            self.on_show()
            messagebox.showinfo("Thành công", "Đã xuất hóa đơn PDF!")

        ConfirmPopup(self, "Xác nhận", f"Xác nhận thanh toán cho {tname} ({method})?", confirm_action)

    def export_pdf_invoice(self, oid, tname, method):
        from reportlab.pdfgen import canvas
        from reportlab.lib.pagesizes import A6
        from reportlab.pdfbase import pdfmetrics
        from reportlab.pdfbase.ttfonts import TTFont
        import os

        # 1. Lấy dữ liệu chi tiết món ăn từ Database
        con = sqlite3.connect(DB_PATH)
        con.row_factory = sqlite3.Row
        items = con.execute("""
            SELECT m.name, m.price, oi.qty 
            FROM order_items oi JOIN menu m ON oi.menu_id=m.id 
            WHERE oi.order_id=? AND oi.status != 'Cancelled'
        """, (oid,)).fetchall()
        con.close()

        filename = f"HoaDon_{oid}_{datetime.now().strftime('%H%M%S')}.pdf"
        c = canvas.Canvas(filename, pagesize=A6)
        width, height = A6

        # 2. Cấu hình Font Arial (Phải có file Arial.ttf trong thư mục)
        font_path = os.path.join(os.path.dirname(__file__), "Arial.ttf")
        if os.path.exists(font_path):
            pdfmetrics.registerFont(TTFont('Arial-Viet', font_path))
            c.setFont('Arial-Viet', 10)
        else:
            c.setFont("Helvetica", 10) # Fallback nếu thiếu font

        # 3. Vẽ nội dung hóa đơn
        c.drawCentredString(width/2, height - 30, "NHÀ HÀNG CÔ BA")
        c.setFontSize(8)
        c.drawCentredString(width/2, height - 45, f"Hóa đơn: #{oid} - Bàn: {tname}")
        c.drawCentredString(width/2, height - 55, f"Ngày: {datetime.now().strftime('%d/%m/%Y %H:%M')}")
        c.line(15, height - 65, width - 15, height - 65)

        y = height - 80
        total = 0
        c.drawString(20, y, "Món")
        c.drawRightString(width - 50, y, "SL")
        c.drawRightString(width - 20, y, "T.Tiền")

        y -= 15
        for item in items:
            line_total = item['price'] * item['qty']
            total += line_total
            c.drawString(20, y, item['name'][:20])
            c.drawRightString(width - 50, y, str(item['qty']))
            c.drawRightString(width - 20, y, f"{line_total:,.0f}")
            y -= 12
            if y < 30: break

        c.line(15, y + 5, width - 15, y + 5)
        y -= 15
        c.setFontSize(10)
        c.drawString(20, y, "TỔNG CỘNG:")
        c.drawRightString(width - 20, y, f"{total:,.0f} VND")
        
        c.setFontSize(8)
        c.drawCentredString(width/2, y - 25, f"Hình thức: {method}")
        c.drawCentredString(width/2, y - 40, "Cảm ơn Quý khách!")

        c.save()
        os.startfile(filename) # Tự động mở file PDF

    def generate_pdf_invoice(self, oid, tname, method, total_amount, items):
        from reportlab.lib.pagesizes import A6
        from reportlab.pdfgen import canvas
        from reportlab.lib.units import mm
        
        filename = f"Invoice_{oid}_{datetime.now().strftime('%H%M%S')}.pdf"
        c = canvas.Canvas(filename, pagesize=A6)
        width, height = A6

        # Vẽ tiêu đề
        c.setFont("Helvetica-Bold", 14)
        c.drawCentredString(width/2, height - 10*mm, "NHÀ HÀNG CÔ BA")
        c.setFont("Helvetica", 10)
        c.drawCentredString(width/2, height - 15*mm, f"Hóa đơn: #{oid} - Bàn: {tname}")
        c.drawCentredString(width/2, height - 20*mm, f"Ngày: {datetime.now().strftime('%d/%m/%Y %H:%M')}")
        
        c.line(10*mm, height - 25*mm, width - 10*mm, height - 25*mm)

        # Vẽ tiêu đề cột
        y = height - 30*mm
        c.setFont("Helvetica-Bold", 9)
        c.drawString(12*mm, y, "Món")
        c.drawRightString(width - 25*mm, y, "SL")
        c.drawRightString(width - 12*mm, y, "T.Tien")

        # Vẽ danh sách món (Lưu ý: Font chuẩn không dấu, muốn tiếng Việt cần cài thêm font .ttf)
        y -= 5*mm
        c.setFont("Helvetica", 9)
        for item in items:
            c.drawString(12*mm, y, f"{item['name']}")
            c.drawRightString(width - 25*mm, y, f"{item['qty']}")
            c.drawRightString(width - 12*mm, y, f"{item['price']*item['qty']:,.0f}")
            y -= 5*mm
            if y < 20*mm: break # Tránh tràn trang

        c.line(10*mm, y, width - 10*mm, y)
        y -= 7*mm
        c.setFont("Helvetica-Bold", 11)
        c.drawString(12*mm, y, "TONG CONG:")
        c.drawRightString(width - 12*mm, y, f"{total_amount:,.0f} VND")
        
        y -= 5*mm
        c.setFont("Helvetica-Oblique", 9)
        c.drawCentredString(width/2, y, f"HTTT: {method}")

        c.save()
        os.startfile(filename) # Tự động mở file sau khi lưu

    def write_bill_file(self, order_id, table_name, method):
        con = sqlite3.connect(DB_PATH)
        con.row_factory = sqlite3.Row
        # Lấy danh sách món ăn của đơn hàng
        items = con.execute("""
            SELECT m.name, m.price, oi.qty 
            FROM order_items oi 
            JOIN menu m ON oi.menu_id=m.id 
            WHERE oi.order_id=? AND oi.status != 'Cancelled'
        """, (order_id,)).fetchall()
        con.close()

        # Tạo nội dung hóa đơn
        timestamp = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        filename = f"HoaDon_{order_id}_{datetime.now().strftime('%H%M%S')}.txt"
        total_bill = 0
        
        content =  "==========================================\n"
        content += "          NHÀ HÀNG CÔ BA                  \n"
        content += "==========================================\n"
        content += f"HÓA ĐƠN THANH TOÁN\n"
        content += f"Mã đơn: #{order_id}\n"
        content += f"Ngày: {timestamp}\n"
        content += f"Bàn: {table_name}\n"
        content += "------------------------------------------\n"
        content += f"{'Tên Món':<20} {'SL':<5} {'Thành Tiền'}\n"
        content += "------------------------------------------\n"
        
        for item in items:
            subtotal = item['price'] * item['qty']
            total_bill += subtotal
            # Cắt tên món nếu quá dài để tránh vỡ khung
            name = item['name'][:18]
            content += f"{name:<20} {item['qty']:<5} {subtotal:,.0f}\n"
            
        content += "------------------------------------------\n"
        content += f"TỔNG CỘNG:           {total_bill:,.0f} VND\n"
        content += f"THANH TOÁN:          {method}\n"
        content += "==========================================\n"
        content += "        CẢM ƠN QUÝ KHÁCH - HẸN GẶP LẠI    \n"
        content += "==========================================\n"

        try:
            # Lưu file với mã hóa utf-8 để hiển thị tiếng Việt (nếu Notepad hỗ trợ)
            with open(filename, "w", encoding="utf-8") as f:
                f.write(content)
            # Tự động mở file hóa đơn để nhấn in
            os.system(f"notepad.exe {filename}")
        except Exception as e:
            print(f"Lỗi xuất hóa đơn: {e}")

# --- REPORT PAGE ---
class ReportPage(ctk.CTkFrame):
    def __init__(self, parent, controller):
        super().__init__(parent, fg_color="white")
        self.controller = controller
        self.nav = NavBar(self, controller, "📊 BÁO CÁO DOANH THU")
        bar = ctk.CTkFrame(self, fg_color="#f1f2f6", height=60); bar.pack(fill="x", padx=40, pady=20)
        ctk.CTkButton(bar, text="⬅ Quay lại", fg_color="gray", width=100, command=lambda: controller.show_frame("TablePage")).pack(side="left", padx=10)
        ctk.CTkLabel(bar, text="Loại báo cáo:", font=FONT_BOLD).pack(side="left", padx=10)
        self.combo_type = ctk.CTkComboBox(bar, values=["Toàn bộ", "Theo Ngày", "Theo Tháng", "Theo Năm"], width=120, command=self.on_type_change)
        self.combo_type.pack(side="left", padx=10); self.combo_type.set("Theo Ngày")
        self.btn_date_picker = ctk.CTkButton(bar, text=datetime.now().strftime("%d/%m/%Y"), width=150, fg_color="white", text_color="black", border_width=1, command=self.open_calendar)
        self.btn_date_picker.pack(side="left", padx=10)
        self.entry_filter = ctk.CTkEntry(bar, placeholder_text="mm/yyyy", width=150)
        ctk.CTkButton(bar, text="Xem Báo Cáo", fg_color=COLOR_PRIMARY, width=120, command=self.load_report).pack(side="left", padx=20)
        self.lbl_stats = ctk.CTkLabel(self, text="", font=("Arial", 16, "bold"), text_color=COLOR_TEXT); self.lbl_stats.pack(pady=10)
        self.chart_frame = ctk.CTkFrame(self, fg_color="white"); self.chart_frame.pack(fill="both", expand=True, padx=40, pady=20)

        self.lbl_stats = ctk.CTkLabel(self, text="", font=("Arial", 16, "bold"), text_color=COLOR_TEXT)
        self.lbl_stats.pack(pady=5)

        # Khung chứa Top/Bottom món ăn
        self.stats_cards = ctk.CTkFrame(self, fg_color="transparent")
        self.stats_cards.pack(fill="x", padx=40, pady=5)

        self.lbl_best_seller = ctk.CTkLabel(self.stats_cards, text="", font=("Arial", 13, "bold"), text_color=COLOR_SUCCESS)
        self.lbl_best_seller.pack(side="left", expand=True)

        self.lbl_worst_seller = ctk.CTkLabel(self.stats_cards, text="", font=("Arial", 13, "bold"), text_color=COLOR_DANGER)
        self.lbl_worst_seller.pack(side="left", expand=True)

    def on_show(self): self.nav.update_buttons()
    def on_type_change(self, choice):
        self.btn_date_picker.pack_forget(); self.entry_filter.pack_forget()
        if choice == "Theo Ngày":
            self.btn_date_picker.pack(side="left", padx=10, before=self.chart_frame); self.btn_date_picker.lift() 
            for w in self.winfo_children(): 
                if isinstance(w, ctk.CTkFrame) and w != self.chart_frame:
                    for child in w.winfo_children():
                        if child == self.btn_date_picker: child.pack(side="left", padx=10, after=self.combo_type)
        elif choice != "Toàn bộ":
            self.entry_filter.pack(side="left", padx=10, after=self.combo_type)
            if choice == "Theo Tháng": self.entry_filter.configure(placeholder_text="mm/yyyy")
            elif choice == "Theo Năm": self.entry_filter.configure(placeholder_text="yyyy")

    def open_calendar(self): CalendarPopup(self, self.set_date)
    def set_date(self, date_str): self.btn_date_picker.configure(text=date_str)

    def load_report(self):
        filter_type = self.combo_type.get()
        # SQL lấy danh sách món và tổng số lượng bán ra
        sql = """
            SELECT m.name, SUM(oi.qty) as qty, SUM(oi.qty*m.price) as rev 
            FROM order_items oi 
            JOIN menu m ON oi.menu_id=m.id 
            JOIN orders o ON oi.order_id=o.id 
            WHERE o.status='Paid' AND oi.status != 'Cancelled'
        """
        params = ()
        # --- Giữ nguyên logic lọc thời gian của bạn ---
        if filter_type != "Toàn bộ":
            if filter_type == "Theo Ngày":
                try: 
                    d = datetime.strptime(self.btn_date_picker.cget("text"), "%d/%m/%Y")
                    sql += " AND date(o.created_at) = ?"
                    params = (d.strftime("%Y-%m-%d"),)
                except: return
            else:
                filter_val = self.entry_filter.get()
                if not filter_val: messagebox.showwarning("!", "Nhập thời gian"); return
                try:
                    if filter_type == "Theo Tháng": 
                        d = datetime.strptime(filter_val, "%m/%Y")
                        sql += " AND strftime('%Y-%m', o.created_at) = ?"
                        params = (d.strftime("%Y-%m"),)
                    elif filter_type == "Theo Năm": 
                        sql += " AND strftime('%Y', o.created_at) = ?"
                        params = (filter_val,)
                except: messagebox.showerror("Lỗi", "Định dạng sai!"); return
        
        sql += " GROUP BY m.name ORDER BY qty DESC" # Sắp xếp theo số lượng giảm dần

        for w in self.chart_frame.winfo_children(): w.destroy()
        
        con = sqlite3.connect(DB_PATH)
        df = pd.read_sql_query(sql, con, params=params)
        con.close()

        if df.empty:
            self.lbl_stats.configure(text="Không có dữ liệu trong thời gian này.")
            self.lbl_best_seller.configure(text="")
            self.lbl_worst_seller.configure(text="")
            return

        # 1. Hiển thị Tổng doanh thu
        total_rev = df['rev'].sum()
        self.lbl_stats.configure(text=f"TỔNG DOANH THU: {total_rev:,.0f} VNĐ")

        # 2. Tìm món bán chạy nhất / chậm nhất
        best_item = df.iloc[0] # Dòng đầu tiên sau khi ORDER BY qty DESC
        worst_item = df.iloc[-1] # Dòng cuối cùng

        self.lbl_best_seller.configure(
            text=f"🏆 BÁN CHẠY NHẤT: {best_item['name']} ({int(best_item['qty'])} món)"
        )
        self.lbl_worst_seller.configure(
            text=f"⚠️ BÁN CHẬM NHẤT: {worst_item['name']} ({int(worst_item['qty'])} món)"
        )

        # 3. Vẽ biểu đồ (Giữ nguyên logic của bạn)
        plt.style.use('seaborn-v0_8-pastel')
        fig, ax = plt.subplots(figsize=(8, 4), dpi=100)
        bars = ax.bar(df['name'], df['qty'], color=COLOR_PRIMARY)
        ax.set_title("Số lượng món bán ra")
        
        for bar in bars:
            height = bar.get_height()
            ax.text(bar.get_x() + bar.get_width()/2., height, f'{int(height)}', 
                    ha='center', va='bottom', fontsize=10, fontweight='bold')
        
        plt.xticks(rotation=15, ha='right')
        plt.tight_layout()
        
        canvas = FigureCanvasTkAgg(fig, master=self.chart_frame)
        canvas.draw()
        canvas.get_tk_widget().pack(fill="both", expand=True)

    def export_excel(self):
        try:
            con = sqlite3.connect(DB_PATH); df = pd.read_sql_query("SELECT * FROM orders WHERE status='Paid'", con); con.close()
            if df.empty: return messagebox.showwarning("!", "Không có dữ liệu")
            df.to_excel("Bao_Cao.xlsx", index=False); messagebox.showinfo("OK", "Đã xuất file Bao_Cao.xlsx")
        except: messagebox.showerror("Error", "Lỗi xuất file")

if __name__ == "__main__":
    app = RestaurantApp()
    app.mainloop()