import sqlite3
import pandas as pd
import streamlit as st

# --- DATABASE SETUP ---
DB_NAME = "inventory_sales.db"


def init_db():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    # Inventory Table
    c.execute(
        """
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL,
            sku TEXT,
            price REAL NOT NULL,
            stock INTEGER NOT NULL
        )
    """
    )
    # Sales Table
    c.execute(
        """
        CREATE TABLE IF NOT EXISTS sales (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            product_id INTEGER,
            quantity INTEGER NOT NULL,
            total_price REAL NOT NULL,
            sale_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (product_id) REFERENCES products (id)
        )
    """
    )
    conn.commit()
    conn.close()


init_db()


def get_connection():
    return sqlite3.connect(DB_NAME)


# --- STREAMLIT UI ---
st.set_page_config(page_title="Inventory & Sales Hub", layout="wide")
st.title("📦 Inventory & Sales Management Hub")

tabs = st.tabs(
    ["📊 Dashboard", "➕ Manage Inventory", "🛒 Log Sales", "📜 Sales History"]
)

# -------------------------------------------------------------------
# TAB 1: DASHBOARD
# -------------------------------------------------------------------
with tabs[0]:
    st.header("Overview")
    conn = get_connection()

    products_df = pd.read_sql_query("SELECT * FROM products", conn)
    sales_df = pd.read_sql_query(
        """
        SELECT s.id, p.name AS product_name, s.quantity, s.total_price, s.sale_date 
        FROM sales s 
        JOIN products p ON s.product_id = p.id
    """,
        conn,
    )
    conn.close()

    col1, col2, col3 = st.columns(3)
    total_products = len(products_df)
    total_revenue = (
        sales_df["total_price"].sum() if not sales_df.empty else 0.0
    )
    low_stock_count = (
        len(products_df[products_df["stock"] < 5])
        if not products_df.empty
        else 0
    )

    col1.metric("Total Products", total_products)
    col2.metric("Total Revenue", f"${total_revenue:,.2f}")
    col3.metric("Low Stock Items (<5)", low_stock_count)

    st.subheader("Current Stock Levels")
    if not products_df.empty:
        st.dataframe(
            products_df[["id", "name", "sku", "price", "stock"]],
            use_container_width=True,
        )
    else:
        st.info(
            "No products in database yet. Head to 'Manage Inventory' to add some!"
        )

# -------------------------------------------------------------------
# TAB 2: MANAGE INVENTORY
# -------------------------------------------------------------------
with tabs[1]:
    st.header("Add New Product")
    with st.form("add_product_form", clear_on_submit=True):
        col_a, col_b = st.columns(2)
        p_name = col_a.text_input("Product Name")
        p_sku = col_b.text_input("SKU / Item Code")
        p_price = col_a.number_input("Unit Price ($)", min_value=0.0, step=0.50)
        p_stock = col_b.number_input("Initial Stock", min_value=0, step=1)

        submit = st.form_submit_button("Add Product")
        if submit:
            if p_name.strip():
                try:
                    conn = get_connection()
                    c = conn.cursor()
                    c.execute(
                        "INSERT INTO products (name, sku, price, stock) VALUES (?, ?, ?, ?)",
                        (p_name, p_sku, p_price, p_stock),
                    )
                    conn.commit()
                    conn.close()
                    st.success(f"Added **{p_name}** to inventory!")
                    st.rerun()
                except sqlite3.IntegrityError:
                    st.error("A product with this name already exists.")
            else:
                st.warning("Please enter a valid product name.")

# -------------------------------------------------------------------
# TAB 3: LOG SALES
# -------------------------------------------------------------------
with tabs[2]:
    st.header("Record a Transaction")
    conn = get_connection()
    products_df = pd.read_sql_query("SELECT * FROM products", conn)
    conn.close()

    if not products_df.empty:
        # Create item selector
        product_options = {
            f"{row['name']} (Stock: {row['stock']})": row
            for _, row in products_df.iterrows()
        }
        selected_option = st.selectbox(
            "Select Item", list(product_options.keys())
        )
        selected_item = product_options[selected_option]

        sale_qty = st.number_input(
            "Quantity Sold",
            min_value=1,
            max_value=int(selected_item["stock"])
            if selected_item["stock"] > 0
            else 1,
            step=1,
        )
        calculated_total = sale_qty * selected_item["price"]

        st.write(f"**Total Price:** ${calculated_total:,.2f}")

        if selected_item["stock"] <= 0:
            st.error("This item is currently out of stock.")
        else:
            if st.button("Complete Sale"):
                conn = get_connection()
                c = conn.cursor()

                # Deduct Stock
                new_stock = selected_item["stock"] - sale_qty
                c.execute(
                    "UPDATE products SET stock = ? WHERE id = ?",
                    (new_stock, selected_item["id"]),
                )

                # Log Sale
                c.execute(
                    "INSERT INTO sales (product_id, quantity, total_price) VALUES (?, ?, ?)",
                    (selected_item["id"], sale_qty, calculated_total),
                )

                conn.commit()
                conn.close()

                st.success("Sale logged successfully!")
                st.rerun()
    else:
        st.info("Add products to inventory before logging sales.")

# -------------------------------------------------------------------
# TAB 4: SALES HISTORY
# -------------------------------------------------------------------
with tabs[3]:
    st.header("Recent Sales")
    conn = get_connection()
    sales_df = pd.read_sql_query(
        """
        SELECT s.id AS 'Sale ID', p.name AS 'Product', s.quantity AS 'Qty Sold', 
               s.total_price AS 'Total Revenue', s.sale_date AS 'Date'
        FROM sales s 
        JOIN products p ON s.product_id = p.id
        ORDER BY s.sale_date DESC
    """,
        conn,
    )
    conn.close()

    if not sales_df.empty:
        st.dataframe(sales_df, use_container_width=True)
    else:
        st.info("No sales recorded yet.")