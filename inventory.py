# inventory.py
# Full backend + GUI logic for a smooth, persistent inventory system
# Built with: Python + Tkinter + SQLite

import tkinter as tk
from tkinter import ttk, messagebox
import sqlite3
from datetime import datetime

DB = 'inventory.db'

# === DATABASE LOGIC ===
def init_db():
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    # Main inventory table
    c.execute('''
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            identifier TEXT UNIQUE NOT NULL,
            description TEXT NOT NULL,
            quantity INTEGER NOT NULL,
            last_updated_by TEXT
        )
    ''')
    # Stock operation log
    c.execute('''
        CREATE TABLE IF NOT EXISTS stock_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            identifier TEXT NOT NULL,
            change INTEGER NOT NULL,
            person TEXT NOT NULL,
            timestamp TEXT DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()

def get_product_by(field, value):
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    query = f"SELECT * FROM products WHERE {field} = ?"
    c.execute(query, (value,))
    result = c.fetchone()
    conn.close()
    return result

def update_stock(identifier, delta, person):
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    # Check current quantity
    c.execute("SELECT quantity FROM products WHERE identifier = ?", (identifier,))
    row = c.fetchone()
    if not row:
        conn.close()
        return False

    current_qty = row[0]
    new_qty = current_qty + delta
    if new_qty < 0:
        conn.close()
        return False

    # Update quantity
    c.execute("""
        UPDATE products
        SET quantity = ?, last_updated_by = ?
        WHERE identifier = ?
    """, (new_qty, person, identifier))

    # Log the operation
    c.execute("""
        INSERT INTO stock_logs (identifier, change, person)
        VALUES (?, ?, ?)
    """, (identifier, delta, person))

    conn.commit()
    conn.close()
    return True

def add_new_product(identifier, description, quantity, person):
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    try:
        c.execute('''
            INSERT INTO products (identifier, description, quantity, last_updated_by)
            VALUES (?, ?, ?, ?)
        ''', (identifier, description, quantity, person))
        c.execute("""
            INSERT INTO stock_logs (identifier, change, person)
            VALUES (?, ?, ?)
        """, (identifier, quantity, person))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()

def get_logs(identifier):
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("""
        SELECT change, person, timestamp FROM stock_logs
        WHERE identifier = ? ORDER BY timestamp DESC
    """, (identifier,))
    rows = c.fetchall()
    conn.close()
    return rows

# === GUI ===
def start_gui():
    root = tk.Tk()
    root.title("Inventory System")
    root.geometry("700x650")

    # --- Search Section ---
    ttk.Label(root, text="Search Product", font=('Arial', 14, 'bold')).pack(pady=10)

    search_frame = ttk.Frame(root)
    search_frame.pack()

    search_var = tk.StringVar()
    field_var = tk.StringVar(value="identifier")

    ttk.Entry(search_frame, textvariable=search_var, width=30).grid(row=0, column=0, padx=5)
    ttk.Combobox(search_frame, textvariable=field_var, values=["identifier", "description", "last_updated_by"], width=18).grid(row=0, column=1)

    result_text = tk.StringVar()
    result_label = ttk.Label(root, textvariable=result_text, foreground="blue", font=('Arial', 11), wraplength=600, justify="left")
    result_label.pack(pady=10)

    # --- Stock Update Section ---
    action_frame = ttk.Frame(root)
    action_frame.pack(pady=5)

    delta_var = tk.StringVar()
    person_var = tk.StringVar()

    ttk.Label(action_frame, text="Stock Change (+/-):").grid(row=0, column=0)
    ttk.Entry(action_frame, textvariable=delta_var, width=10).grid(row=0, column=1)

    ttk.Label(action_frame, text="Updated By:").grid(row=1, column=0)
    ttk.Entry(action_frame, textvariable=person_var, width=20).grid(row=1, column=1)

    def perform_search():
        result_text.set("")
        pid = search_var.get().strip()
        field = field_var.get()
        if not pid:
            return messagebox.showwarning("Input", "Enter a value to search")
        row = get_product_by(field, pid)
        if row:
            result_text.set(f"🆔: {row[1]}\n📦: {row[2]}\nQty: {row[3]}\n👤: {row[4]}")
        else:
            result_text.set("Product not found")

    def update_and_log():
        pid = search_var.get().strip()
        delta = delta_var.get().strip()
        user = person_var.get().strip()

        if not (pid and delta and user):
            return messagebox.showerror("Missing Info", "All fields required")

        try:
            delta = int(delta)
        except ValueError:
            return messagebox.showerror("Invalid Input", "Stock change must be a number")

        if update_stock(pid, delta, user):
            perform_search()
            messagebox.showinfo("Success", f"Stock updated for {pid}")
        else:
            messagebox.showerror("Failed", f"Update failed for {pid} (maybe not enough stock?)")

    ttk.Button(root, text="Search", command=perform_search).pack()
    ttk.Button(root, text="Update Stock", command=update_and_log).pack(pady=10)

    # --- Logs Section ---
    log_box = tk.Text(root, height=10, width=85)
    log_box.pack(pady=10)

    def show_logs():
        pid = search_var.get().strip()
        if not pid:
            return
        logs = get_logs(pid)
        log_box.delete('1.0', tk.END)
        if logs:
            for change, user, ts in logs:
                log_box.insert(tk.END, f"[{ts}] {user} -> {'+' if change > 0 else ''}{change}\n")
        else:
            log_box.insert(tk.END, "No logs found for this identifier.")

    ttk.Button(root, text="Show Logs", command=show_logs).pack()

    # --- New Product Section ---
    ttk.Label(root, text="\nAdd New Product", font=('Arial', 14, 'bold')).pack()

    add_frame = ttk.Frame(root)
    add_frame.pack(pady=5)

    id_entry = tk.Entry(add_frame, width=15)
    desc_entry = tk.Entry(add_frame, width=25)
    qty_entry = tk.Entry(add_frame, width=10)
    user_entry = tk.Entry(add_frame, width=15)

    ttk.Label(add_frame, text="Identifier").grid(row=0, column=0)
    id_entry.grid(row=1, column=0)
    ttk.Label(add_frame, text="Description").grid(row=0, column=1)
    desc_entry.grid(row=1, column=1)
    ttk.Label(add_frame, text="Quantity").grid(row=0, column=2)
    qty_entry.grid(row=1, column=2)
    ttk.Label(add_frame, text="Added By").grid(row=0, column=3)
    user_entry.grid(row=1, column=3)

    def add_product_gui():
        try:
            identifier = id_entry.get().strip()
            description = desc_entry.get().strip()
            quantity = int(qty_entry.get().strip())
            person = user_entry.get().strip()

            if not all([identifier, description, person]):
                raise ValueError("Identifier, Description, and Added By are required")

            if add_new_product(identifier, description, quantity, person):
                messagebox.showinfo("Success", "Product added successfully")
                id_entry.delete(0, tk.END)
                desc_entry.delete(0, tk.END)
                qty_entry.delete(0, tk.END)
                user_entry.delete(0, tk.END)
            else:
                messagebox.showerror("Error", "Product identifier already exists")
        except Exception as e:
            messagebox.showerror("Error", str(e))

    ttk.Button(root, text="Add Product", command=add_product_gui).pack(pady=5)
    root.mainloop()

# === Main Entry ===
if __name__ == '__main__':
    init_db()
    start_gui()
