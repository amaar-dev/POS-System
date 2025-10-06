import sqlite3
from datetime import datetime
import tkinter as tk
from tkinter import ttk, messagebox

DB_FILE = "Oil_shop_database.db"

# --------------------------
# Database helper functions
# --------------------------
# Load data into the table
def load_data():
    for row in tree.get_children():
        tree.delete(row)
    for row in get_all_products():
        tree.insert("", tk.END, values=row)

load_data()

# Handle double-click edit
def on_double_click(event):
    item = tree.selection()[0]
    values = list(tree.item(item, "values"))

    edit_win = tk.Toplevel(root)
    edit_win.title("Edit Product")
    edit_win.geometry("300x300")

    fields = ["Name", "Barcode", "Price", "Quantity"]
    entries = {}

    for i, field in enumerate(fields):
        tk.Label(edit_win, text=field).pack()
        e = tk.Entry(edit_win)
        e.pack()
        e.insert(0, values[i + 1])
        entries[field] = e

    def save_changes():
        try:
            update_product(
                values[0],
                entries["Name"].get(),
                entries["Barcode"].get(),
                float(entries["Price"].get()),
                int(entries["Quantity"].get())
            )
            messagebox.showinfo("Success", "Product updated successfully!")
            edit_win.destroy()
            load_data()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to update: {e}")
    tk.Button(edit_win, text="Save", command=save_changes).pack(pady=10)




# Fetch all products and edit stock
def get_all_products():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT id, name, barcode, price, quantity FROM products")
    rows = c.fetchall()
    conn.close()
    return rows

def update_product(product_id, name, barcode, price, quantity):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("""
        UPDATE products
        SET name=?, barcode=?, price=?, quantity=?
        WHERE id=?
    """, (name, barcode, price, quantity, product_id))
    conn.commit()
    conn.close()


# Establish connection
def get_connection():
    return sqlite3.connect(DB_FILE)

def get_product_by_barcode(barcode):
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("SELECT id, name, price FROM products WHERE barcode = ?", (barcode,))
        return cur.fetchone()

def insert_sale(total):
    with get_connection() as conn:
        cur = conn.cursor()
        now = datetime.now()
        cur.execute("INSERT INTO sales (date, time, total) VALUES (?, ?, ?)",
                    (now.strftime("%Y-%m-%d"), now.strftime("%H:%M"), total))
        conn.commit()
        return cur.lastrowid

def insert_sale_item(sale_id, product_id, quantity, price):
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("INSERT INTO sale_items (sale_id, product_id, quantity, price) VALUES (?, ?, ?, ?)",
                    (sale_id, product_id, quantity, price))
        conn.commit()

def get_monthly_sales():
    with get_connection() as conn:
        cur = conn.cursor()
        month = datetime.now().strftime("%Y-%m")
        cur.execute("""
            SELECT s.date, s.time, p.name, si.quantity, si.price
            FROM sale_items si
            JOIN sales s ON si.sale_id = s.id
            JOIN products p ON si.product_id = p.id
            WHERE substr(s.date, 1, 7) = ?
            ORDER BY s.date, s.time
        """, (month,))
        return cur.fetchall()

# --------------------------
# GUI Setup
# --------------------------

# Gui cart setup


root = tk.Tk()
root.title("Oil Shop POS System")
root.geometry("800x600")

cart = []
total_amount = 0.0

def add_to_cart():
    global total_amount
    barcode = entry_barcode.get().strip()
    if not barcode:
        return

    product = get_product_by_barcode(barcode)
    if not product:
        messagebox.showerror("Error", "Product not found.")
        entry_barcode.delete(0, tk.END)
        return

    product_id, name, price = product
    quantity = 1  # can make adjustable later

    cart.append((product_id, name, quantity, price))
    total_amount += price

    tree.insert("", "end", values=(name, quantity, f"Rs {price:.2f}"))
    lbl_total.config(text=f"Total: Rs {total_amount:.2f}")
    entry_barcode.delete(0, tk.END)

def finish_sale():
    global cart, total_amount
    if not cart:
        messagebox.showwarning("Empty Cart", "No items to record.")
        return

    sale_id = insert_sale(total_amount)
    for item in cart:
        product_id, name, quantity, price = item
        insert_sale_item(sale_id, product_id, quantity, price)

    messagebox.showinfo("Success", "Sale recorded successfully!")
    cart.clear()
    total_amount = 0
    lbl_total.config(text="Total: Rs 0.00")
    tree.delete(*tree.get_children())

def show_monthly_report():
    data = get_monthly_sales()
    if not data:
        messagebox.showinfo("No Data", "No sales recorded this month.")
        return

    month = datetime.now().strftime("%B %Y")
    report = f"Monthly Report - {month}\n\n"
    total = 0
    for date, time, name, qty, price in data:
        report += f"{date} {time} | {name} (x{qty}) - Rs {price:.2f}\n"
        total += price
    report += f"\nTotal Sales: Rs {total:.2f}"

    messagebox.showinfo("Monthly Report", report)

# Gui layout for inventory
root = tk.Tk()
root.title("Oil Shop Management System")
root.geometry("750x450")

tree = ttk.Treeview(root, columns=("ID", "Name", "Barcode", "Price", "Quantity"), show="headings")
tree.heading("ID", text="ID")
tree.heading("Name", text="Name")
tree.heading("Barcode", text="Barcode")
tree.heading("Price", text="Price")
tree.heading("Quantity", text="Quantity")
tree.column("ID", width=40)
tree.column("Name", width=180)
tree.column("Barcode", width=150)
tree.column("Price", width=100)
tree.column("Quantity", width=80)
tree.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)


# --------------------------
# UI Layout
# --------------------------

frame_top = tk.Frame(root)
frame_top.pack(pady=10)

tk.Label(frame_top, text="Scan Barcode:", font=("Arial", 12)).pack(side=tk.LEFT, padx=5)
entry_barcode = tk.Entry(frame_top, font=("Arial", 12))
entry_barcode.pack(side=tk.LEFT, padx=5)
entry_barcode.bind("<Return>", lambda e: add_to_cart())

btn_add = tk.Button(frame_top, text="Add", command=add_to_cart)
btn_add.pack(side=tk.LEFT, padx=5)

columns = ("Product", "Qty", "Price")
tree = ttk.Treeview(root, columns=columns, show="headings", height=15)
for col in columns:
    tree.heading(col, text=col)
tree.pack(pady=10, fill=tk.BOTH, expand=True)

lbl_total = tk.Label(root, text="Total: Rs 0.00", font=("Arial", 14, "bold"))
lbl_total.pack(pady=5)

frame_bottom = tk.Frame(root)
frame_bottom.pack(pady=10)

btn_finish = tk.Button(frame_bottom, text="Finish Sale", bg="black", fg="white", width=15, command=finish_sale)
btn_finish.pack(side=tk.LEFT, padx=5)

btn_report = tk.Button(frame_bottom, text="Monthly Report", bg="black", fg="white", width=15, command=show_monthly_report)
btn_report.pack(side=tk.LEFT, padx=5)

btn_exit = tk.Button(frame_bottom, text="Exit", bg="black", fg="black", width=10, command=root.destroy)
btn_exit.pack(side=tk.LEFT, padx=5)

tree.bind("<Double-1>", on_double_click)

root.mainloop()
