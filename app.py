import sqlite3
from datetime import date
import pandas as pd
import streamlit as st

DB_FILE = "construction_site.db"

# 安全庫存門檻設定（低於此數量自動亮紅燈）
SAFETY_STOCK = {
    "台泥品牌水泥 (50kg/包)": 50,
    "高拉力鋼筋 SD420W (噸)": 10,
    "預拌混凝土 3000psi (m³)": 15,
    "清水模板 (片)": 80,
}

# ==========================================
# 1. 資料庫連線與初始化
# ==========================================
def get_conn():
    conn = sqlite3.connect(DB_FILE, check_same_thread=False)
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn

def init_db():
    conn = get_conn()
    cur = conn.cursor()

    # 建立協力廠商表
    cur.execute("""
        CREATE TABLE IF NOT EXISTS vendors (
            vendor_id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            trade TEXT NOT NULL,
            contact TEXT,
            phone TEXT,
            tax_id TEXT,
            rating INTEGER DEFAULT 5
        )
    """)

    # 建立材料進出貨紀錄表（關聯 vendors）
    cur.execute("""
        CREATE TABLE IF NOT EXISTS materials_log (
            log_id INTEGER PRIMARY KEY AUTOINCREMENT,
            tx_date TEXT NOT NULL,
            material_name TEXT NOT NULL,
            unit TEXT NOT NULL,
            tx_type TEXT NOT NULL, -- '進貨' 或 '領料'
            qty REAL NOT NULL,
            unit_price REAL DEFAULT 0,
            vendor_id INTEGER,
            billing_status TEXT DEFAULT '未請款', -- '未請款', '對帳中', '已請款付款'
            note TEXT,
            FOREIGN KEY (vendor_id) REFERENCES vendors(vendor_id) ON DELETE SET NULL
        )
    """)

    # 建立日常零用金表
    cur.execute("""
        CREATE TABLE IF NOT EXISTS petty_cash (
            cash_id INTEGER PRIMARY KEY AUTOINCREMENT,
            expense_date TEXT NOT NULL,
            category TEXT NOT NULL,
            item TEXT NOT NULL,
            amount INTEGER NOT NULL,
            handler TEXT,
            has_receipt TEXT DEFAULT '有發票/收據'
        )
    """)

    # 建立小型機具租借表
    cur.execute("""
        CREATE TABLE IF NOT EXISTS equipment_rental (
            rental_id INTEGER PRIMARY KEY AUTOINCREMENT,
            equip_name TEXT NOT NULL,
            asset_code TEXT,
            borrower TEXT NOT NULL,
            borrow_date TEXT NOT NULL,
            return_date TEXT,
            status TEXT DEFAULT '借出中'
        )
    """)

    # 若資料庫為空，寫入工地預設測試資料
    cur.execute("SELECT COUNT(*) FROM vendors")
    if cur.fetchone()[0] == 0:
        sample_vendors = [
            ("大高雄建材股份有限公司", "混凝土/水泥供應", "陳建宏", "0912-345-678", "24589102", 5),
            ("永固鋼鐵企業社", "鋼筋/鋼構工程", "林志明", "0928-765-432", "53819204", 5),
            ("順發模板五金行", "模板/五金耗材", "王美玲", "0933-111-222", "80192834", 4),
            ("宏達水電工程行", "水電工程", "張家豪", "0955-888-999", "42910384", 4),
        ]
        cur.executemany(
            "INSERT INTO vendors (name, trade, contact, phone, tax_id, rating) VALUES (?, ?, ?, ?, ?, ?)",
            sample_vendors,
        )

        sample_materials = [
            ("2026-11-10", "台泥品牌水泥 (50kg/包)", "包", "進貨", 120, 185, 1, "已請款付款", "基礎地梁工程進料"),
            ("2026-11-12", "台泥品牌水泥 (50kg/包)", "包", "領料", 85, 0, None, "不適用", "B1牆面泥作打底領用"),
            ("2026-11-11", "高拉力鋼筋 SD420W (噸)", "噸", "進貨", 25, 21500, 2, "對帳中", "1F柱主筋與箍筋"),
            ("2026-11-14", "高拉力鋼筋 SD420W (噸)", "噸", "領料", 18, 0, None, "不適用", "A區鋼筋綁紮領料"),
            ("2026-11-13", "清水模板 (片)", "片", "進貨", 150, 320, 3, "未請款", "1F頂板組模用"),
            ("2026-11-15", "清水模板 (片)", "片", "領料", 40, 0, None, "不適用", "樓梯間支撐模板"),
            ("2026-11-16", "預拌混凝土 3000psi (m³)", "m³", "進貨", 30, 2450, 1, "未請款", "1F頂板澆置進料"),
        ]
        cur.executemany(
            """INSERT INTO materials_log
               (tx_date, material_name, unit, tx_type, qty, unit_price, vendor_id, billing_status, note)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            sample_materials,
        )

        sample_cash = [
            ("2026-11-14", "工地便當/飲料", "灌漿作業工班便當 18 個 + 運動飲料", 2150, "李工務", "有發票/收據"),
            ("2026-11-15", "五金耗材", "鐵絲、墨斗線、切割片補充", 860, "陳主任", "有發票/收據"),
        ]
        cur.executemany(
            "INSERT INTO petty_cash (expense_date, category, item, amount, handler, has_receipt) VALUES (?, ?, ?, ?, ?, ?)",
            sample_cash,
        )

        sample_equip = [
            ("平板夯實機 (Compactor)", "EQ-001", "泥作工班-老王", "2026-11-14", None, "借出中"),
            ("3kW 移動式發電機", "EQ-004", "水電工班-小張", "2026-11-12", "2026-11-15", "已歸還"),
            ("雷射水平儀", "EQ-007", "放樣組-林工程師", "2026-11-15", None, "借出中"),
        ]
        cur.executemany(
            "INSERT INTO equipment_rental (equip_name, asset_code, borrower, borrow_date, return_date, status) VALUES (?, ?, ?, ?, ?, ?)",
            sample_equip,
        )

    conn.commit()
    conn.close()

# ==========================================
# 2. 頁面主架構設定
# ==========================================
st.set_page_config(page_title="土木工地日常行政與材料管理系統", page_icon="🏗️", layout="wide")
init_db()

st.title("🏗️ 土木工地日常行政與材料進出貨管理系統")
st.caption("整合材料庫存警示、協力廠商關聯查詢、請款對帳與工地日常行政管理（SQLite 關聯式資料庫）")

tab1, tab2, tab3, tab4 = st.tabs([
    "📦 1. 材料進出貨與庫存警示",
    "🤝 2. 協力廠商名錄與聯絡網",
    "🧾 3. 進貨單據與廠商對應查詢",
    "💰 4. 行政零用金與機具租借",
])

# ==========================================
# 模組 1：材料進出貨管理系統 (CRUD + 紅燈警示)
# ==========================================
with tab1:
    st.subheader("📊 即時材料庫存監控（低於安全存量自動亮紅燈）")
    conn = get_conn()
    df_mat = pd.read_sql_query("SELECT * FROM materials_log ORDER BY tx_date DESC, log_id DESC", conn)

    stock_rows = []
    for mat_name, min_qty in SAFETY_STOCK.items():
        sub = df_mat[df_mat["material_name"] == mat_name]
        in_qty = sub[sub["tx_type"] == "進貨"]["qty"].sum()
        out_qty = sub[sub["tx_type"] == "領料"]["qty"].sum()
        curr_qty = in_qty - out_qty
        unit = mat_name.split("(")[-1].replace(")", "")
        status = "🔴 庫存不足！請立即叫料" if curr_qty < min_qty else "🟢 庫存充足"
        stock_rows.append({
            "材料名稱": mat_name,
            "累計進貨": in_qty,
            "累計領料": out_qty,
            "目前庫存量": curr_qty,
            "安全庫存門檻": min_qty,
            "單位": unit,
            "庫存狀態警示": status,
        })
    df_stock = pd.DataFrame(stock_rows)
    st.dataframe(df_stock, use_container_width=True, hide_index=True)

    st.divider()
    col_add, col_manage = st.columns([1, 1.3])

    with col_add:
        st.markdown("#### ➕ 新增材料進貨 / 領料紀錄")
        df_vendors = pd.read_sql_query("SELECT vendor_id, name FROM vendors", conn)
        vendor_map = dict(zip(df_vendors["name"], df_vendors["vendor_id"]))

        with st.form("add_material_form", clear_on_submit=True):
            tx_date = st.date_input("異動日期", value=date.today())
            mat_choice = st.selectbox("材料名稱", list(SAFETY_STOCK.keys()))
            tx_type = st.radio("異動類型", ["進貨", "領料"], horizontal=True)
            qty = st.number_input("數量", min_value=0.5, step=1.0, value=10.0)
            unit_price = st.number_input("進貨單價（領料請填 0）", min_value=0.0, step=10.0, value=0.0)
            vendor_name = st.selectbox("供貨廠商（領料可略過）", ["無（工班領料）"] + list(vendor_map.keys()))
            billing_status = st.selectbox("請款對帳狀態", ["未請款", "對帳中", "已請款付款", "不適用"])
            note = st.text_input("工區用途 / 備註", placeholder="例如：2F柱筋綁紮、A區基礎灌漿")

            if st.form_submit_button("💾 寫入資料庫", use_container_width=True):
                unit_str = mat_choice.split("(")[-1].replace(")", "")
                v_id = vendor_map.get(vendor_name) if tx_type == "進貨" else None
                cur = conn.cursor()
                cur.execute(
                    """INSERT INTO materials_log
                       (tx_date, material_name, unit, tx_type, qty, unit_price, vendor_id, billing_status, note)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (str(tx_date), mat_choice, unit_str, tx_type, qty, unit_price, v_id, billing_status, note),
                )
                conn.commit()
                st.success(f"已成功新增「{mat_choice}」{tx_type} {qty} {unit_str}！")
                st.rerun()

    with col_manage:
        st.markdown("#### 📋 進出貨歷史明細與修改 / 刪除")
        st.dataframe(df_mat, use_container_width=True, hide_index=True, height=280)

        if not df_mat.empty:
            del_id = st.selectbox("選擇要刪除的紀錄編號 (log_id)", df_mat["log_id"].tolist())
            if st.button("🗑️ 刪除此筆材料紀錄", type="secondary"):
                conn.execute("DELETE FROM materials_log WHERE log_id = ?", (del_id,))
                conn.commit()
                st.warning(f"已刪除 log_id = {del_id}")
                st.rerun()
    conn.close()

# ==========================================
# 模組 2：協力廠商名錄與聯絡網 (CRUD)
# ==========================================
with tab2:
    conn = get_conn()
    st.subheader("🤝 工地協力廠商資料庫")

    trade_filter = st.selectbox("🔍 依工種分類篩選", ["全部工種", "混凝土/水泥供應", "鋼筋/鋼構工程", "模板/五金耗材", "水電工程", "泥作工程", "機具租賃"])
    if trade_filter == "全部工種":
        df_v = pd.read_sql_query("SELECT * FROM vendors ORDER BY vendor_id DESC", conn)
    else:
        df_v = pd.read_sql_query("SELECT * FROM vendors WHERE trade = ? ORDER BY vendor_id DESC", conn, params=(trade_filter,))

    st.dataframe(df_v, use_container_width=True, hide_index=True)

    c1, c2 = st.columns(2)
    with c1:
        st.markdown("#### ➕ 新增協力廠商")
        with st.form("add_vendor_form", clear_on_submit=True):
            v_name = st.text_input("廠商名稱 *", placeholder="例如：巨力鋼構工程有限公司")
            v_trade = st.selectbox("工種分類", ["混凝土/水泥供應", "鋼筋/鋼構工程", "模板/五金耗材", "水電工程", "泥作工程", "機具租賃"])
            v_contact = st.text_input("現場聯絡人", placeholder="例如：林經理")
            v_phone = st.text_input("聯絡電話", placeholder="例如：0912-345-678")
            v_tax = st.text_input("統一編號", placeholder="8碼統編")
            v_rating = st.slider("配合評價 (1~5星)", 1, 5, 5)
            if st.form_submit_button("💾 新增廠商資料", use_container_width=True):
                if v_name.strip():
                    conn.execute(
                        "INSERT INTO vendors (name, trade, contact, phone, tax_id, rating) VALUES (?, ?, ?, ?, ?, ?)",
                        (v_name, v_trade, v_contact, v_phone, v_tax, v_rating),
                    )
                    conn.commit()
                    st.success(f"廠商「{v_name}」已建檔！")
                    st.rerun()
                else:
                    st.error("請輸入廠商名稱！")

    with c2:
        st.markdown("#### ✏️ 修改廠商評價 / 聯絡電話或刪除")
        if not df_v.empty:
            edit_vid = st.selectbox("選擇廠商編號 (vendor_id)", df_v["vendor_id"].tolist())
            target_v = df_v[df_v["vendor_id"] == edit_vid].iloc[0]
            with st.form("edit_vendor_form"):
                new_phone = st.text_input("更新聯絡電話", value=target_v["phone"])
                new_rating = st.slider("更新配合評價", 1, 5, int(target_v["rating"]))
                col_u, col_d = st.columns(2)
                if col_u.form_submit_button("🔄 更新廠商資訊", use_container_width=True):
                    conn.execute("UPDATE vendors SET phone = ?, rating = ? WHERE vendor_id = ?", (new_phone, new_rating, edit_vid))
                    conn.commit()
                    st.success("廠商資訊已更新！")
                    st.rerun()
                if col_d.form_submit_button("🗑️ 刪除該廠商", use_container_width=True):
                    conn.execute("DELETE FROM vendors WHERE vendor_id = ?", (edit_vid,))
                    conn.commit()
                    st.warning("已刪除該廠商資料！")
                    st.rerun()
    conn.close()

# ==========================================
# 模組 3：進貨單據與廠商對應查詢 (SQL JOIN 關聯查詢)
# ==========================================
with tab3:
    conn = get_conn()
    st.subheader("🧾 進貨單據與供貨廠商關聯對帳查詢")
    st.info("透過資料庫 `LEFT JOIN` 關聯 `materials_log` 與 `vendors`，點選任一筆進貨單據即可檢視完整廠商資訊並更新請款狀態。")

    query_join = """
        SELECT 
            m.log_id AS 單據編號,
            m.tx_date AS 進貨日期,
            m.material_name AS 材料名稱,
            m.qty AS 進貨數量,
            m.unit AS 單位,
            m.unit_price AS 單價,
            (m.qty * m.unit_price) AS 總金額,
            m.billing_status AS 請款對帳狀態,
            v.name AS 供貨廠商,
            v.trade AS 工種分類,
            v.contact AS 聯絡人,
            v.phone AS 聯絡電話,
            v.tax_id AS 統一編號
        FROM materials_log m
        LEFT JOIN vendors v ON m.vendor_id = v.vendor_id
        WHERE m.tx_type = '進貨'
        ORDER BY m.tx_date DESC
    """
    df_po = pd.read_sql_query(query_join, conn)
    st.dataframe(df_po, use_container_width=True, hide_index=True)

    if not df_po.empty:
        st.markdown("#### 🔎 單據詳情反查與請款對帳更新")
        selected_po = st.selectbox(
            "選擇進貨單據編號進行廠商對帳確認：",
            df_po["單據編號"].tolist(),
            format_func=lambda x: f"單據 #{x} | {df_po[df_po['單據編號']==x]['進貨日期'].values[0]} - {df_po[df_po['單據編號']==x]['材料名稱'].values[0]}",
        )
        row = df_po[df_po["單據編號"] == selected_po].iloc[0]

        m1, m2, m3, m4 = st.columns(4)
        m1.metric("供貨廠商", row["供貨廠商"] or "未指定廠商")
        m2.metric("單價 / 總金額", f"${row['單價']:,.0f} / ${row['總金額']:,.0f}")
        m3.metric("聯絡窗口與電話", f"{row['聯絡人']} ({row['聯絡電話']})")
        m4.metric("目前對帳狀態", row["請款對帳狀態"])

        new_status = st.selectbox("變更請款對帳狀態：", ["未請款", "對帳中", "已請款付款"], index=["未請款", "對帳中", "已請款付款"].index(row["請款對帳狀態"]) if row["請款對帳狀態"] in ["未請款", "對帳中", "已請款付款"] else 0)
        if st.button("✅ 確認更新請款狀態"):
            conn.execute("UPDATE materials_log SET billing_status = ? WHERE log_id = ?", (new_status, selected_po))
            conn.commit()
            st.success(f"單據 #{selected_po} 對帳狀態已更新為「{new_status}」！")
            st.rerun()
    conn.close()

# ==========================================
# 模組 4：日常行政零用金 / 機具租借登記
# ==========================================
with tab4:
    conn = get_conn()
    col_cash, col_equip = st.columns(2)

    with col_cash:
        st.subheader("💵 工地日常行政零用金")
        df_cash = pd.read_sql_query("SELECT * FROM petty_cash ORDER BY expense_date DESC", conn)
        st.metric("累計零用金支出總額", f"NT$ {df_cash['amount'].sum():,}" if not df_cash.empty else "NT$ 0")
        st.dataframe(df_cash, use_container_width=True, hide_index=True)

        with st.form("add_cash_form", clear_on_submit=True):
            st.markdown("**➕ 登記零用金支出**")
            c_date = st.date_input("支出日期", value=date.today())
            c_cat = st.selectbox("費用類別", ["工地便當/飲料", "五金耗材", "交通/油資", "行政文具雜支"])
            c_item = st.text_input("支出摘要明細", placeholder="例如：買工地飲用水 5 箱")
            c_amt = st.number_input("金額 (NTD)", min_value=1, step=50, value=500)
            c_handler = st.text_input("經手人", value="工地主任")
            c_rec = st.selectbox("憑證狀態", ["有發票/收據", "免用統一發票收據", "暫無憑證"])
            if st.form_submit_button("💾 新增零用金紀錄", use_container_width=True):
                conn.execute(
                    "INSERT INTO petty_cash (expense_date, category, item, amount, handler, has_receipt) VALUES (?, ?, ?, ?, ?, ?)",
                    (str(c_date), c_cat, c_item, c_amt, c_handler, c_rec),
                )
                conn.commit()
                st.success("零用金紀錄已儲存！")
                st.rerun()

    with col_equip:
        st.subheader("🛠️ 小型機具借出與歸還登記")
        df_eq = pd.read_sql_query("SELECT * FROM equipment_rental ORDER BY rental_id DESC", conn)
        st.dataframe(df_eq, use_container_width=True, hide_index=True)

        with st.form("add_equip_form", clear_on_submit=True):
            st.markdown("**➕ 登記機具借出**")
            e_name = st.selectbox("機具名稱", ["平板夯實機 (Compactor)", "3kW 移動式發電機", "雷射水平儀", "電動破碎機", "潛水抽水機"])
            e_code = st.text_input("機具編號", placeholder="例如：EQ-009")
            e_borrower = st.text_input("借用人 / 工班", placeholder="例如：鋼筋工班-阿明")
            e_bdate = st.date_input("借出日期", value=date.today())
            if st.form_submit_button("📤 登記借出", use_container_width=True):
                conn.execute(
                    "INSERT INTO equipment_rental (equip_name, asset_code, borrower, borrow_date, status) VALUES (?, ?, ?, ?, '借出中')",
                    (e_name, e_code, e_borrower, str(e_bdate)),
                )
                conn.commit()
                st.success(f"已登記借出：{e_name}")
                st.rerun()

        borrowed_df = df_eq[df_eq["status"] == "借出中"]
        if not borrowed_df.empty:
            st.markdown("**📥 機具歸還確認**")
            ret_id = st.selectbox(
                "選擇要歸還的借出單號：",
                borrowed_df["rental_id"].tolist(),
                format_func=lambda x: f"#{x} | {borrowed_df[borrowed_df['rental_id']==x]['equip_name'].values[0]} ({borrowed_df[borrowed_df['rental_id']==x]['borrower'].values[0]})",
            )
            if st.button("✅ 確認機具已歸還入庫", use_container_width=True):
                conn.execute(
                    "UPDATE equipment_rental SET status = '已歸還', return_date = ? WHERE rental_id = ?",
                    (str(date.today()), ret_id),
                )
                conn.commit()
                st.success("機具已更新為「已歸還」！")
                st.rerun()
    conn.close()
