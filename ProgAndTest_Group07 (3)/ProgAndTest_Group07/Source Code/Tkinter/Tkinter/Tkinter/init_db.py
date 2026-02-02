import sqlite3
import os

def init_db():
    # Xác định đường dẫn file database cùng thư mục với file code
    base_dir = os.path.dirname(os.path.abspath(__file__))
    db_path = os.path.join(base_dir, "restaurant.db")
    if os.path.exists(db_path): os.remove(db_path)

    # Kết nối (nếu chưa có file nó sẽ tự tạo mới)
    con = sqlite3.connect(db_path)
    cur = con.cursor()

    print("Đang khởi tạo các bảng dữ liệu...")

    # 1. Bảng người dùng
    cur.execute("DROP TABLE IF EXISTS users")
    cur.execute("""
        CREATE TABLE users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            role TEXT NOT NULL,
            status TEXT DEFAULT 'Active'
        )
    """)

    # 2. Bảng bàn ăn
    cur.execute("DROP TABLE IF EXISTS tables")
    cur.execute("""
        CREATE TABLE tables (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            status TEXT DEFAULT 'Available'
        )
    """)

    # 3. Bảng thực đơn (Menu)
    cur.execute("DROP TABLE IF EXISTS menu")
    cur.execute("""
        CREATE TABLE menu (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            category TEXT,
            price REAL NOT NULL,
            status TEXT DEFAULT 'Available'
        )
    """)

    # 4. Bảng đơn hàng (Orders)
    cur.execute("DROP TABLE IF EXISTS orders")
    cur.execute("""
        CREATE TABLE orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            table_id INTEGER,
            status TEXT DEFAULT 'Pending',
            total REAL DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (table_id) REFERENCES tables (id)
        )
    """)

    # 5. Bảng chi tiết món ăn (Order Items)
    cur.execute("DROP TABLE IF EXISTS order_items")
    cur.execute("""
        CREATE TABLE order_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_id INTEGER,
            menu_id INTEGER,
            qty INTEGER NOT NULL,
            status TEXT DEFAULT 'Pending',
            FOREIGN KEY (order_id) REFERENCES orders (id),
            FOREIGN KEY (menu_id) REFERENCES menu (id)
        )
    """)

    # --- CHÈN DỮ LIỆU MẪU ĐỂ TEST ---
    
    # Tài khoản đăng nhập: admin / 123
    cur.execute("INSERT INTO users (username, password, role) VALUES (?, ?, ?)", 
                ('admin', '123', 'manager'))

    # Danh sách bàn
    tables = [('Bàn số 1',), ('Bàn số 2',), ('Bàn số 3',), ('Bàn số 4',), ('Bàn số 5',), ('Bàn số 6',)]
    cur.executemany("INSERT INTO tables (name) VALUES (?)", tables)

    # Thực đơn món ăn
    menu_items = [
        ('Cà Phê Sữa', 'Đồ uống', 25000),
        ('Bạc Xỉu', 'Đồ uống', 29000),
        ('Trà Đào', 'Đồ uống', 35000),
        ('Bánh Mì Kẹp', 'Món ăn', 20000),
        ('Phở Bò', 'Món ăn', 45000),
        ('Cơm Tấm', 'Món ăn', 40000)
    ]
    cur.executemany("INSERT INTO menu (name, category, price) VALUES (?, ?, ?)", menu_items)

    con.commit()
    con.close()
    print("Khởi tạo Database thành công!")

if __name__ == "__main__":
    init_db()