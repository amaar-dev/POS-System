import sqlite3
from datetime import datetime
import tkinter as tk
from tkinter import ttk, messagebox
import os
import tempfile
import platform


DB_NAME = "Oil_shop_database.db"

# --------------------------
# Database helper functions
# --------------------------

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

def get_product_by_barcode(barcode):
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute("SELECT id, name, price FROM products WHERE barcode=?", (barcode,))
    result = cur.fetchone()
    conn.close()
    return result

def insert_sale(total):
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    now = datetime.now()
    cur.execute("INSERT INTO sales (date, time, total) VALUES (?, ?, ?)",
                (now.strftime("%Y-%m-%d"), now.strftime("%H:%M"), total))
    conn.commit()
    sale_id = cur.lastrowid
    conn.close()
    return sale_id

def insert_sale_item(sale_id, product_id, quantity, price):
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute("INSERT INTO sale_items (sale_id, product_id, quantity, price) VALUES (?, ?, ?, ?)",
                (sale_id, product_id, quantity, price))
    conn.commit()
    conn.close()

def get_monthly_sales():
    conn = sqlite3.connect(DB_NAME)
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
    data = cur.fetchall()
    conn.close()
    return data

# --------------------------
# GUI Setup
# --------------------------

root = tk.Tk()
root.title("Oil Shop POS System")
root.geometry("900x600")

cart = []
total_amount = 0.0

# --- Functions ---
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
    quantity = 1  # Default to 1 for simplicity

    cart.append((product_id, name, quantity, price))
    total_amount += price

    tree_cart.insert("", "end", values=(name, quantity, f"Rs {price:.2f}"))
    lbl_total.config(text=f"Total: Rs {total_amount:.2f}")
    entry_barcode.delete(0, tk.END)

def print_receipt(cart, total_amount):
    """Generate and print a simple text receipt compatible with thermal printers."""
    now = datetime.now()
    date_str = now.strftime("%Y-%m-%d")
    time_str = now.strftime("%H:%M")

    receipt_lines = []
    receipt_lines.append("-" * 40)
    receipt_lines.append("           OIL SHOP RECEIPT")
    receipt_lines.append("-" * 40)
    receipt_lines.append(f"Date: {date_str}   Time: {time_str}")
    receipt_lines.append("")
    receipt_lines.append("ITEM                 QTY     PRICE")
    receipt_lines.append("-" * 40)

    for product_id, name, qty, price in cart:
        receipt_lines.append(f"{name:<20}{qty:<6}{price:>8.2f}")

    receipt_lines.append("-" * 40)
    receipt_lines.append(f"TOTAL:{'':>23}{total_amount:>8.2f}")
    receipt_lines.append("-" * 40)
    receipt_lines.append("  THANK YOU FOR YOUR PURCHASE!")
    receipt_lines.append("-" * 40)

    # Create a temporary file
    temp_receipt = os.path.join(tempfile.gettempdir(), "receipt.txt")
    with open(temp_receipt, "w", encoding="utf-8") as f:
        f.write("\n".join(receipt_lines))

    # Auto-print based on OS
    system = platform.system()
    try:
        if system == "Windows":
            os.startfile(temp_receipt, "print")
        elif system == "Darwin":  # macOS
            os.system(f"lp '{temp_receipt}'")
        else:  # Linux
            os.system(f"lp '{temp_receipt}'")
    except Exception as e:
        messagebox.showerror("Print Error", f"Could not print receipt: {e}")


def finish_sale():
    global cart, total_amount
    if not cart:
        messagebox.showwarning("Empty Cart", "No items to record.")
        return

    try:
        # Insert sale into database
        sale_id = insert_sale(total_amount)

        # Insert each item from cart into sale_items table
        for item in cart:
            product_id, name, quantity, price = item
            insert_sale_item(sale_id, product_id, quantity, price)

        # Print the receipt (and save it)
        print_receipt(cart, total_amount)

        # Notify user
        messagebox.showinfo("Success", f"Sale #{sale_id} recorded and receipt printed!")

        # Reset cart and total
        cart.clear()
        total_amount = 0
        lbl_total.config(text="Total: Rs 0.00")
        tree.delete(*tree.get_children())

    except Exception as e:
        messagebox.showerror("Error", f"Failed to record sale: {e}")


    sale_id = insert_sale(total_amount)
    for item in cart:
        product_id, name, quantity, price = item
        insert_sale_item(sale_id, product_id, quantity, price)

    messagebox.showinfo("Success", "Sale recorded successfully!")
    cart.clear()
    total_amount = 0
    lbl_total.config(text="Total: Rs 0.00")
    tree_cart.delete(*tree_cart.get_children())

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

# --- Product Editing ---
def load_inventory():
    for row in tree_inventory.get_children():
        tree_inventory.delete(row)
    for row in get_all_products():
        tree_inventory.insert("", tk.END, values=row)

def on_double_click(event):
    item = tree_inventory.selection()
    if not item:
        return
    item = item[0]
    values = list(tree_inventory.item(item, "values"))

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
            load_inventory()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to update: {e}")

    tk.Button(edit_win, text="Save Changes", command=save_changes).pack(pady=10)

# --------------------------
# Layout
# --------------------------

notebook = ttk.Notebook(root)
notebook.pack(fill="both", expand=True)

# --- POS Tab ---
frame_pos = ttk.Frame(notebook)
notebook.add(frame_pos, text="POS System")

frame_top = tk.Frame(frame_pos)
frame_top.pack(pady=10)

tk.Label(frame_top, text="Scan Barcode:", font=("Arial", 12)).pack(side=tk.LEFT, padx=5)
entry_barcode = tk.Entry(frame_top, font=("Arial", 12))
entry_barcode.pack(side=tk.LEFT, padx=5)
entry_barcode.bind("<Return>", lambda e: add_to_cart())

btn_add = tk.Button(frame_top, text="Add", command=add_to_cart)
btn_add.pack(side=tk.LEFT, padx=5)

columns_cart = ("Product", "Qty", "Price")
tree_cart = ttk.Treeview(frame_pos, columns=columns_cart, show="headings", height=15)
for col in columns_cart:
    tree_cart.heading(col, text=col)
tree_cart.pack(pady=10, fill=tk.BOTH, expand=True)

lbl_total = tk.Label(frame_pos, text="Total: Rs 0.00", font=("Arial", 14, "bold"))
lbl_total.pack(pady=5)

frame_bottom = tk.Frame(frame_pos)
frame_bottom.pack(pady=10)

btn_finish = tk.Button(frame_bottom, text="Finish Sale", bg="black", fg="white", width=15, command=finish_sale)
btn_finish.pack(side=tk.LEFT, padx=5)

btn_report = tk.Button(frame_bottom, text="Monthly Report", bg="black", fg="white", width=15, command=show_monthly_report)
btn_report.pack(side=tk.LEFT, padx=5)

btn_exit = tk.Button(frame_bottom, text="Exit", bg="black", fg="white", width=10, command=root.destroy)
btn_exit.pack(side=tk.LEFT, padx=5)

# --- Inventory Tab ---
frame_inventory = ttk.Frame(notebook)
notebook.add(frame_inventory, text="Inventory")

tree_inventory = ttk.Treeview(frame_inventory, columns=("ID", "Name", "Barcode", "Price", "Quantity"), show="headings")
for col in ("ID", "Name", "Barcode", "Price", "Quantity"):
    tree_inventory.heading(col, text=col)
tree_inventory.column("ID", width=40)
tree_inventory.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
tree_inventory.bind("<Double-1>", on_double_click)

load_inventory()

root.mainloop()
