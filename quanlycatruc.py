import base64
import hashlib
import hmac
import html
from io import BytesIO
import json
import re
from datetime import date, timedelta
from pathlib import Path

import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
from supabase import create_client


SHIFT_ROLE_PRIORITY = {
    "Phó Giám Đốc": 0,
    "Hạt Trưởng": 1,
    "Hạt Phó": 2,
    "Trưởng Phòng": 3,
    "Phó Phòng": 4,
    "Trạm Phó": 5,
    "Đội Trưởng": 6,
    "Đội Phó": 7,
    "Ca Trưởng": 8,
    "Tổ Trưởng": 9,
    "Kíp Trưởng": 10,
    "HCNS": 11,
}

REPORT_GROUP_COLORS = (
    ("#eef3ff", "#142b78"),
    ("#effaf3", "#176b3a"),
    ("#fff6e5", "#8a5200"),
    ("#f8efff", "#6b2c91"),
    ("#fff0f0", "#9b2525"),
)

PROJECT_TEAM = "Dự Án Gói Tháo Dỡ ITs"
TRAFFIC_SAFETY_TEAM = "Đội ĐBGT"
SUPPLEMENTARY_SHIFT = "Nhân sự tăng cường"


def normalize_report_label(value):
    return " ".join(str(value or "").split()).casefold()

st.set_page_config(page_title="Quản lý vận hành", layout="wide", initial_sidebar_state="collapsed")

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Roboto+Condensed:wght@400;600;700&display=swap');
:root { --navy:#142b78; --red:#c62f2f; --line:#d8d8d8; --paper:#fffef8; }
.stApp { background:#f7f4df; color:#414141; font-family:'Roboto Condensed','Arial Narrow',Arial,sans-serif; width:100%; overflow-x:hidden; color-scheme:light; }
html, body, [data-testid="stAppViewContainer"], [data-testid="stAppViewBlockContainer"] {
    color-scheme:light !important;
}
.block-container { width:100%; max-width:none; box-sizing:border-box; margin:0; padding:.5rem clamp(.3rem,1vw,.75rem) 2rem; }
[data-testid="stHeader"] { background:transparent; }
/* Ẩn các nút quảng bá/deploy của Streamlit nhưng giữ nút mở sidebar và khu vực đăng nhập. */
[data-testid="stToolbarActions"],
[data-testid="stMainMenu"],
[data-testid="stAppDeployButton"],
[data-testid="stHeader"] button[data-testid="stBaseButton-header"]:has(span) {
    display:none !important;
}
.stSidebar, [data-testid="stSidebar"] { display:none !important; }
.agency-header { background:var(--paper); border-bottom:4px solid #edcf62; min-height:112px; display:grid; grid-template-columns:minmax(180px,25%) minmax(0,50%) minmax(0,25%); align-items:center; gap:1rem; padding:.45rem 1rem; }
.agency-logo { display:block; width:100%; max-width:245px; height:94px; object-fit:contain; object-position:left center; }
.agency-copy { grid-column:2; min-width:0; text-align:center; }
.agency-copy h1 { color:var(--navy); font-size:clamp(1.25rem,2.8vw,2.65rem); line-height:1.05; margin:0; font-weight:700; text-wrap:balance; }
.agency-copy p { color:var(--red); font-weight:700; font-size:clamp(1rem,2.1vw,1.75rem); line-height:1.05; letter-spacing:.01em; margin:.25rem 0 0; text-wrap:balance; }
.date-strip { background:#fff; border:1px solid #eadb98; color:var(--red); text-align:center; font-weight:700; font-size:1.2rem; padding:.45rem .5rem; margin:.6rem 0; }
.section-caption { background:#fff; border:1px solid var(--line); color:var(--red); font-weight:700; text-align:center; padding:.55rem; margin-top:.25rem; }
.main-navigation { margin:.55rem 0 .8rem; display:flex; align-items:center; min-height:2.65rem; }
[data-testid="stRadio"] { width:100% !important; }
[data-testid="stElementContainer"]:has(> div[data-testid="stRadio"]) { width:100% !important; }
[data-testid="stRadioGroup"] {
    display:flex !important; flex-wrap:nowrap !important; align-items:center !important;
    gap:.35rem !important; width:100% !important;
}
[data-testid="stRadioOption"] {
    flex:0 1 auto !important; width:auto !important; min-height:2.65rem;
    display:flex !important; align-items:center !important; justify-content:center;
    background:#fff;
    border:1px solid #d9d9d9; border-radius:.375rem; color:#414141; font-weight:400;
    padding:.3rem .65rem; text-align:center; box-shadow:0 1px 2px rgba(0,0,0,.04);
}
[data-testid="stRadioOption"][data-selected="true"] {
    background:#fff; color:var(--red); border-color:#d9d9d9; box-shadow:0 1px 2px rgba(0,0,0,.04);
}
[data-testid="stRadioOption"] > div { display:flex !important; align-items:center !important; }
[data-testid="stRadioOption"] > div > div:first-child { display:none !important; }
.login-toolbar { display:flex; justify-content:flex-end; align-items:center; min-height:2.65rem; margin:.55rem 0 .8rem; }
.login-toolbar [data-testid="stButton"] { width:auto !important; }
.login-toolbar button { width:auto !important; color:var(--navy); font-weight:700; padding:.3rem .65rem; white-space:nowrap; }
[data-testid="stColumn"]:has(.login-toolbar) [data-testid="stButton"] { margin-left:auto !important; }
[data-testid="stColumn"]:has(.login-toolbar) > [data-testid="stVerticalBlock"] { align-items:flex-end !important; }
/* Dùng nhiều selector để tương thích các phiên bản Streamlit Cloud khác nhau. */
div[role="tablist"],
div[data-baseweb="tab-list"] {
    display:flex !important;
    width:100% !important;
    gap:0 !important;
    overflow-x:auto !important;
}

div[role="tablist"] > div,
div[data-baseweb="tab-list"] > div {
    flex:1 1 0 !important;
    min-width:0 !important;
}

button[data-testid="stTab"],
button[data-baseweb="tab"],
div[role="tablist"] button[role="tab"],
div[role="tablist"] > div[role="tab"],
div[data-baseweb="tab-list"] [role="tab"] { 
    flex: 1 1 0 !important; 
    min-width:0 !important;
    display:flex !important;
    justify-content: center !important; 
    background: #e5ebf0 !important; 
    border: 1px solid var(--line) !important; /* Tạo viền xám mỏng bao quanh */
    border-radius: 0 !important; 
    color: #222 !important; 
    font-weight: 700 !important; 
    padding: 0.65rem !important; 
    margin: 0 !important; 
}

/* Xóa viền bên trái của các tab (trừ tab đầu tiên) để tránh bị nét đôi khi xếp sát nhau */
button[data-testid="stTab"]:not(:first-child),
button[data-baseweb="tab"]:not(:first-child),
div[role="tablist"] button[role="tab"]:not(:first-child),
div[role="tablist"] > div[role="tab"]:not(:first-child),
div[data-baseweb="tab-list"] [role="tab"]:not(:first-child) {
    border-left: none !important;
}

/* Tùy chỉnh nút Tab đang được chọn (Active) */
button[data-testid="stTab"][aria-selected="true"],
button[data-baseweb="tab"][aria-selected="true"],
div[role="tablist"] button[role="tab"][aria-selected="true"],
div[role="tablist"] > div[role="tab"][aria-selected="true"],
div[data-baseweb="tab-list"] [role="tab"][aria-selected="true"] { 
    background: #fff !important; 
    color: var(--red) !important; 
    border-bottom: 2px solid var(--red) !important; /* Chỉ tạo gạch đỏ nhẹ ở dưới */
    box-shadow: none !important; /* Xóa bỏ vạch đỏ mập ở phía trên */
}
.stDataFrame { background:#fff; }
/* Đồng bộ màu các ô nhập và nút thao tác trên cả nền sáng và chế độ trình duyệt tối. */
[data-testid="stDateInput"] input,
[data-testid="stTextInput"] input,
[data-testid="stNumberInput"] input,
[data-testid="stTextArea"] textarea {
    background:#fff !important;
    color:#252525 !important;
    border-color:#cfd6df !important;
    -webkit-text-fill-color:#252525 !important;
}
[data-testid="stDateInput"] > div,
[data-testid="stTextInput"] > div,
[data-testid="stNumberInput"] > div,
[data-testid="stTextArea"] > div,
[data-testid="stDateInput"] [data-baseweb="input"],
[data-testid="stDateInput"] [data-baseweb="base-input"],
[data-testid="stSelectbox"] [data-baseweb="select"],
[data-testid="stSelectbox"] [data-baseweb="select"] > div {
    background:#fff !important;
    color:#252525 !important;
    border-color:#cfd6df !important;
}
[data-testid="stDateInput"] *,
[data-testid="stTextInput"] *,
[data-testid="stNumberInput"] *,
[data-testid="stTextArea"] *,
[data-testid="stSelectbox"] * {
    color:#252525 !important;
}
[data-baseweb="input"],
[data-baseweb="base-input"],
[data-baseweb="input-container"],
[data-baseweb="select"],
[data-baseweb="select"] > div,
[role="combobox"] {
    background:#fff !important;
    color:#252525 !important;
    border-color:#cfd6df !important;
    color-scheme:light !important;
}
[data-baseweb="input"] *,
[data-baseweb="base-input"] *,
[data-baseweb="input-container"] *,
[data-baseweb="select"] *,
[role="combobox"] * {
    background-color:transparent !important;
    color:#252525 !important;
    -webkit-text-fill-color:#252525 !important;
}
[data-testid="stDateInput"] [data-baseweb="input"] *,
[data-testid="stDateInput"] [data-baseweb="base-input"] * {
    background:#fff !important;
    color:#252525 !important;
    -webkit-text-fill-color:#252525 !important;
}
[data-testid="stDateInput"] [data-baseweb="input"] > div,
[data-testid="stDateInput"] [data-baseweb="input"] input,
[data-testid="stDateInput"] [data-baseweb="base-input"] > div {
    background:#fff !important;
    color:#252525 !important;
    border-color:#cfd6df !important;
    -webkit-text-fill-color:#252525 !important;
}
[data-testid="stSelectbox"] [data-baseweb="select"] [data-baseweb="value-container"],
[data-testid="stSelectbox"] [data-baseweb="select"] [data-baseweb="single-value"],
[data-testid="stSelectbox"] [data-baseweb="select"] input {
    color:#252525 !important;
    -webkit-text-fill-color:#252525 !important;
}
[data-testid="stTextInput"] label,
[data-testid="stTextArea"] label,
[data-testid="stNumberInput"] label,
[data-testid="stDateInput"] label,
[data-testid="stSelectbox"] label,
[data-testid="stMarkdownContainer"] label {
    color:#414141 !important;
}
[data-testid="stTextInput"] input:disabled {
    background:#f4f6f8 !important;
    color:#252525 !important;
    -webkit-text-fill-color:#252525 !important;
    opacity:1 !important;
}
[data-testid="stDateInput"] input::placeholder,
[data-testid="stTextInput"] input::placeholder,
[data-testid="stTextArea"] textarea::placeholder {
    color:#68717c !important;
    opacity:1 !important;
}
[data-testid="stDateInput"] svg,
[data-testid="stSelectbox"] svg,
[data-testid="stNumberInput"] button svg {
    color:#142b78 !important;
    fill:#142b78 !important;
}
[data-baseweb="menu"],
[data-baseweb="popover"],
[data-baseweb="calendar"] {
    background:#fff !important;
    color:#252525 !important;
    color-scheme:light !important;
}
[data-baseweb="calendar"] *,
[data-baseweb="popover"] * {
    color:#252525 !important;
}
[data-baseweb="calendar"] button {
    background:#fff !important;
    border-color:transparent !important;
}
[data-baseweb="calendar"] button:hover,
[data-baseweb="calendar"] button[aria-selected="true"] {
    background:#eaf0ff !important;
    color:#142b78 !important;
}
[role="option"] {
    color:#252525 !important;
    background:#fff !important;
}
[role="option"][aria-selected="true"],
[role="option"]:hover {
    background:#eaf0ff !important;
    color:#142b78 !important;
}
/* Hộp đăng nhập phải giữ giao diện sáng, không phụ thuộc theme trình duyệt. */
[role="dialog"],
[data-testid="stDialog"],
[data-testid="stDialog"] > div,
[data-testid="stDialog"] form,
[role="dialog"] form {
    background:#fff !important;
    color:#252525 !important;
}
[role="dialog"] *,
[data-testid="stDialog"] * {
    color:#252525 !important;
}
[role="dialog"] input,
[data-testid="stDialog"] input {
    background:#fff !important;
    color:#252525 !important;
    border-color:#cfd6df !important;
    -webkit-text-fill-color:#252525 !important;
}
[role="dialog"] [data-testid="stFormSubmitButton"] > button,
[data-testid="stDialog"] [data-testid="stFormSubmitButton"] > button {
    background:#142b78 !important;
    color:#fff !important;
    border-color:#142b78 !important;
}
[role="dialog"] [data-testid="stFormSubmitButton"] > button *,
[data-testid="stDialog"] [data-testid="stFormSubmitButton"] > button * {
    color:#fff !important;
    -webkit-text-fill-color:#fff !important;
}
[data-testid="stButton"] > button,
[data-testid="stFormSubmitButton"] > button {
    background:#142b78 !important;
    color:#fff !important;
    border:1px solid #142b78 !important;
    font-weight:700 !important;
}
[data-testid="stButton"] > button *,
[data-testid="stFormSubmitButton"] > button * {
    color:inherit !important;
    -webkit-text-fill-color:currentColor !important;
}
[data-testid="stButton"] > button:hover,
[data-testid="stFormSubmitButton"] > button:hover {
    background:#1f3d9b !important;
    border-color:#1f3d9b !important;
    color:#fff !important;
}
[data-testid="stButton"] > button:focus,
[data-testid="stFormSubmitButton"] > button:focus {
    box-shadow:0 0 0 .15rem rgba(20,43,120,.22) !important;
}
[data-testid="stButton"] > button[kind="secondary"],
[data-testid="stFormSubmitButton"] > button[kind="secondary"] {
    background:#fff !important;
    color:#c62f2f !important;
    border-color:#c62f2f !important;
}
[data-testid="stButton"] > button[kind="secondary"]:hover,
[data-testid="stFormSubmitButton"] > button[kind="secondary"]:hover {
    background:#fff1f1 !important;
    color:#a52222 !important;
    border-color:#a52222 !important;
}
.login-toolbar [data-testid="stButton"] > button {
    background:#fff !important;
    color:#142b78 !important;
    border-color:#cfd6df !important;
}
.login-toolbar [data-testid="stButton"] > button:hover {
    background:#eef3ff !important;
    color:#142b78 !important;
    border-color:#142b78 !important;
}
.schedule-table-wrap { width:100%; overflow-x:auto; margin:.4rem 0 1rem; }
.schedule-table { width:100%; border-collapse:collapse; background:#fff; color:#111; font-size:.9rem; }
.schedule-table th, .schedule-table td { border:1px solid #d9d9d9; padding:.55rem .5rem; text-align:left; vertical-align:top; white-space:normal; }
.schedule-table th { background:#edf1f5; color:#111; font-weight:700; }
.schedule-table td { background:#fff; color:#111; line-height:1.45; }
.schedule-table .schedule-group-row td { font-weight:700; border-top:2px solid currentColor; }
.schedule-table .schedule-group-row + tr td { border-top:0; }
.admin-panel { background:#fff; border-top:3px solid var(--navy); padding:.75rem; margin-top:1rem; }
@media (max-width:650px) {
    .block-container { padding:.25rem .3rem 1.25rem; }
    .agency-header { position:relative; min-height:78px; display:block; padding:.45rem .25rem .5rem; }
    .agency-logo { position:absolute; top:.45rem; left:.3rem; z-index:1; width:52px; height:38px; max-width:52px; object-position:left center; }
    .agency-copy { display:block; width:100%; margin:0; padding:0 .1rem; text-align:center; }
    .agency-copy h1 { font-size:.9rem; line-height:1; white-space:nowrap; text-align:center; }
    .agency-copy p { font-size:.78rem; line-height:1; margin:.12rem auto 0; text-align:center; white-space:nowrap; }
    .date-strip { font-size:.78rem; padding:.42rem .25rem; margin:.4rem 0; }
    .section-caption { font-size:.9rem; padding:.5rem .25rem; }
    [data-testid="stHorizontalBlock"]:has(.main-navigation) {
        display:flex !important; flex-wrap:nowrap !important; align-items:center !important;
    }
    [data-testid="stHorizontalBlock"]:has(.main-navigation) > [data-testid="stColumn"]:first-child {
        flex:1 1 0 !important; width:calc(100% - 100px) !important; min-width:0 !important;
    }
    [data-testid="stHorizontalBlock"]:has(.main-navigation) > [data-testid="stColumn"]:last-child {
        flex:0 0 100px !important; width:100px !important; min-width:100px !important;
    }
    [data-testid="stRadioOption"] {
        min-height:2.35rem; font-size:.68rem; line-height:1.1; padding:.4rem .3rem;
    }
    div[role="tablist"] button[role="tab"],
    div[role="tablist"] > div[role="tab"],
    div[data-baseweb="tab-list"] button[data-baseweb="tab"],
    div[data-baseweb="tab-list"] [role="tab"] {
        font-size:.62rem !important;
        line-height:1.1 !important;
        padding:.55rem .18rem !important;
        white-space:normal !important;
        text-align:center !important;
    }
    .schedule-table-wrap { overflow-x:auto; -webkit-overflow-scrolling:touch; }
    .schedule-table {
        min-width:820px;
        font-size:.68rem;
        line-height:1.2;
    }
    .schedule-table th,
    .schedule-table td {
        padding:.3rem .35rem;
        white-space:nowrap;
    }
    .schedule-table th { font-size:.64rem; }
    .schedule-table td { font-size:.68rem; }
}
</style>
""", unsafe_allow_html=True)

# Kết nối an toàn thông qua st.secrets
@st.cache_resource
def init_connection():
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    return create_client(url, key)
try:
    supabase = init_connection()
    db_connected = True
except Exception as e:
    st.error("Không thể kết nối cơ sở dữ liệu. Vui lòng kiểm tra lại cấu hình!")
    db_connected = False


def render_agency_header(display_date):
    logo_path = Path(__file__).with_name("deocalogo.jpg")
    logo_data = base64.b64encode(logo_path.read_bytes()).decode("ascii") if logo_path.exists() else ""
    st.markdown(f"""
    <header class="agency-header">
        <img class="agency-logo" src="data:image/jpeg;base64,{logo_data}" alt="DEOCA GROUP">
        <div class="agency-copy">
            <h1>CÔNG TY CỔ PHẦN TẬP ĐOÀN ĐÈO CẢ</h1>
            <p>QUẢN LÝ VẬN HÀNH CAO TỐC TPHCM - TL - MT</p>
        </div>
    </header>
    <div class="date-strip"> NGÀY: {display_date}</div>
    """, unsafe_allow_html=True)


def next_available_id(records):
    used_ids = {
        int(item["id"])
        for item in records
        if item.get("id") is not None and str(item["id"]).isdigit()
    }
    next_id = 1
    while next_id in used_ids:
        next_id += 1
    return next_id


def vehicle_km_value(value):
    parsed = pd.to_numeric(value, errors="coerce")
    return int(parsed) if pd.notna(parsed) and parsed >= 0 else 0


def clear_shift_form_state():
    keys = ["add_errors"]
    keys.extend(
        key
        for key in st.session_state
        if key.startswith((
            "add_date_", "add_team_", "add_location_", "add_shift_",
            "add_role_", "add_people_count_", "add_group_work_",
            "add_person_name_", "add_person_phone_",
        ))
    )
    for key in keys:
        st.session_state.pop(key, None)
    st.session_state["shift_form_version"] = (
        st.session_state.get("shift_form_version", 0) + 1
    )


def clear_vehicle_form_state():
    prefixes = ("vehicle_add_", "vehicle_new_")
    keys = []
    keys.extend(
        key
        for key in st.session_state
        if key.startswith(prefixes)
    )
    for key in keys:
        st.session_state.pop(key, None)
    st.session_state["vehicle_form_version"] = (
        st.session_state.get("vehicle_form_version", 0) + 1
    )


# --- QUẢN LÝ PHÂN QUYỀN ADMIN ---
AUTH_COOKIE_NAME = "quanlycatruc_auth"


def auth_cookie_secret():
    return st.secrets.get("AUTH_COOKIE_SECRET") or st.secrets.get("SUPABASE_KEY", "")


def signed_auth_value(username):
    value = str(username)
    signature = hmac.new(
        auth_cookie_secret().encode("utf-8"),
        value.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    return f"{value}.{signature}"


def verified_auth_username(cookie_value):
    if not cookie_value or "." not in cookie_value:
        return None
    username, signature = cookie_value.rsplit(".", 1)
    expected = signed_auth_value(username).rsplit(".", 1)[1]
    if hmac.compare_digest(signature, expected):
        return username
    return None


def set_auth_cookie(username):
    cookie_header = f"{AUTH_COOKIE_NAME}={signed_auth_value(username)}; path=/; SameSite=Lax"
    components.html(
        f"""
        <script>
        document.cookie = {json.dumps(cookie_header)};
        </script>
        """,
        height=0,
    )


def clear_auth_cookie():
    components.html(
        f"""
        <script>
        document.cookie = {json.dumps(
            f"{AUTH_COOKIE_NAME}=; path=/; expires=Thu, 01 Jan 1970 00:00:00 GMT; SameSite=Lax"
        )};
        </script>
        """,
        height=0,
    )


def cleanup_old_report_data(supabase_client, cutoff_date):
    cleanup_tables = ("shift_reports", "vehicles", "fuel_reports")
    deleted_counts = {}
    missing_tables = []
    errors = []

    for table_name in cleanup_tables:
        try:
            response = supabase_client.table(table_name).select("id, ngay").execute()
            old_ids = []
            for row in response.data or []:
                parsed_date = pd.to_datetime(
                    row.get("ngay"), dayfirst=True, errors="coerce"
                )
                if pd.notna(parsed_date) and parsed_date.date() < cutoff_date:
                    row_id = row.get("id")
                    if row_id is not None:
                        old_ids.append(row_id)
            if old_ids:
                for row_id in old_ids:
                    supabase_client.table(table_name).delete().eq("id", row_id).execute()
            deleted_counts[table_name] = len(old_ids)
        except Exception as error:
            error_text = str(error)
            if "PGRST205" in error_text or f"public.{table_name}" in error_text:
                missing_tables.append(table_name)
            else:
                errors.append(f"{table_name}: {error_text}")

    return deleted_counts, missing_tables, errors


if "is_admin" not in st.session_state:
    st.session_state.is_admin = False
if "logged_in_user" not in st.session_state:
    st.session_state.logged_in_user = None
if "tab_accounts" not in st.session_state:
    st.session_state.tab_accounts = {
        "Báo Cáo Ca Trực": {"username": "tab1", "password": "123"},
        "Phương Tiện": {"username": "tab2", "password": "123"},
        "Nhiên Liệu": {"username": "tab3", "password": "123"},
    }

if not st.session_state.logged_in_user:
    saved_username = verified_auth_username(st.context.cookies.get(AUTH_COOKIE_NAME))
    if saved_username == "admin":
        st.session_state.is_admin = True
        st.session_state.logged_in_user = "admin"
    elif any(
        saved_username == account.get("username") and account.get("username")
        for account in st.session_state.tab_accounts.values()
    ):
        st.session_state.logged_in_user = saved_username

@st.dialog("Đăng nhập")
def show_login_dialog():
    with st.form("login"):
        username = st.text_input("Tên đăng nhập")
        pwd = st.text_input("Mật khẩu", type="password")
        if st.form_submit_button("Đăng nhập"):
            is_admin_login = username.strip() == "admin" and pwd == "admin123"
            is_tab_login = any(
                username.strip() == account.get("username")
                and pwd == account.get("password")
                and account.get("username")
                for account in st.session_state.tab_accounts.values()
            )
            if is_admin_login or is_tab_login:
                st.session_state.is_admin = is_admin_login
                st.session_state.logged_in_user = "admin" if is_admin_login else username.strip()
                set_auth_cookie(st.session_state.logged_in_user)
                st.rerun()
            else:
                st.error("Tên đăng nhập hoặc mật khẩu không đúng.")

header_date = st.session_state.get("selected_date", date.today())
if isinstance(header_date, str):
    parsed_header_date = pd.to_datetime(header_date, dayfirst=True, errors="coerce")
    header_date = parsed_header_date.date() if pd.notna(parsed_header_date) else date.today()
render_agency_header(header_date.strftime("%d/%m/%Y"))

menu_column, login_column = st.columns([4, 1], gap="small")
with menu_column:
    st.markdown('<div class="main-navigation">', unsafe_allow_html=True)
    menu = st.radio(
        "Chức năng",
        ["Báo Cáo Ca Trực", "Phương Tiện", "Nhiên Liệu"],
        horizontal=True,
        label_visibility="collapsed",
        key="main_navigation",
    )
    st.markdown("</div>", unsafe_allow_html=True)

with login_column:
    st.markdown('<div class="login-toolbar">', unsafe_allow_html=True)
    if st.session_state.is_admin:
        if st.button("ADMIN · Đăng xuất", key="logout"):
            st.session_state.is_admin = False
            st.session_state.logged_in_user = None
            clear_auth_cookie()
            st.rerun()
    elif st.session_state.logged_in_user:
        if st.button(f"{st.session_state.logged_in_user} · Đăng xuất", key="logout"):
            st.session_state.logged_in_user = None
            clear_auth_cookie()
            st.rerun()
    else:
        if st.button("Đăng nhập", key="open-login"):
            show_login_dialog()
    st.markdown("</div>", unsafe_allow_html=True)

if st.session_state.is_admin:
    with st.expander("Quản lý tài khoản"):
        manage_tab, add_tab = st.tabs(["Sửa / Xóa tài khoản", "Thêm tài khoản"])
        with manage_tab:
            account_menu = st.selectbox(
                "Tab cần quản lý",
                list(st.session_state.tab_accounts),
                key="account_menu",
            )
            account = st.session_state.tab_accounts[account_menu]
            with st.form("account_management"):
                edited_username = st.text_input("Tên đăng nhập", value=account["username"])
                edited_password = st.text_input("Mật khẩu", value=account["password"], type="password")
                save_account, delete_account = st.columns(2)
                with save_account:
                    save_clicked = st.form_submit_button("Lưu tài khoản")
                with delete_account:
                    delete_clicked = st.form_submit_button("Xóa tài khoản", type="secondary")
                if save_clicked:
                    username = edited_username.strip()
                    duplicate = any(
                        name != account_menu
                        and values["username"] == username
                        and username
                        for name, values in st.session_state.tab_accounts.items()
                    )
                    if not username or not edited_password:
                        st.error("Tên đăng nhập và mật khẩu không được để trống.")
                    elif duplicate:
                        st.error("Tên đăng nhập đã được sử dụng cho tab khác.")
                    else:
                        st.session_state.tab_accounts[account_menu] = {
                            "username": username,
                            "password": edited_password,
                        }
                        st.success(f"Đã cập nhật tài khoản cho {account_menu}.")
                        st.rerun()
                if delete_clicked:
                    st.session_state.tab_accounts[account_menu] = {"username": "", "password": ""}
                    st.success(f"Đã xóa tài khoản của {account_menu}.")
                    st.rerun()

        with add_tab:
            with st.form("add_account"):
                new_account_menu = st.selectbox(
                    "Tab cần cấp tài khoản",
                    list(st.session_state.tab_accounts),
                    key="new_account_menu",
                )
                new_username = st.text_input("Tên đăng nhập mới")
                new_password = st.text_input("Mật khẩu mới", type="password")
                add_clicked = st.form_submit_button("Thêm / Cấp lại tài khoản")
                if add_clicked:
                    username = new_username.strip()
                    duplicate = any(
                        values["username"] == username and username
                        for values in st.session_state.tab_accounts.values()
                    )
                    if not username or not new_password:
                        st.error("Tên đăng nhập và mật khẩu không được để trống.")
                    elif duplicate:
                        st.error("Tên đăng nhập đã được sử dụng cho tab khác.")
                    else:
                        st.session_state.tab_accounts[new_account_menu] = {
                            "username": username,
                            "password": new_password,
                        }
                        st.success(f"Đã cấp tài khoản cho {new_account_menu}.")
                        st.rerun()

    with st.expander("Xuất báo cáo Excel"):
        cleanup_cutoff_date = date.today() - timedelta(days=10)
        if date.today().weekday() >= 5:
            st.warning(
                "Nhắc Admin cuối tuần: hãy tải file Excel sao lưu trước khi dữ liệu "
                f"trước ngày {cleanup_cutoff_date:%d/%m/%Y} được tự động dọn dẹp."
            )
        if not db_connected:
            st.warning(
                "Chưa kết nối Supabase nên chưa thể tự động dọn dữ liệu. "
                "Hãy sao lưu dữ liệu phiên làm việc trước khi đóng ứng dụng."
            )

        export_dates = st.date_input(
            "Ngày báo cáo (chọn một ngày hoặc khoảng ngày)",
            value=(date.today(), date.today()),
            format="DD/MM/YYYY",
            key="export_report_dates",
        )
        if isinstance(export_dates, (list, tuple)):
            if len(export_dates) == 2:
                export_start, export_end = export_dates
            elif len(export_dates) == 1:
                export_start = export_end = export_dates[0]
            else:
                export_start = export_end = date.today()
            if export_start is None:
                export_start = date.today()
            if export_end is None:
                export_end = export_start
        else:
            export_start = export_end = export_dates
        if st.button("Tạo file Excel", key="create_excel_report"):
            export_tables = {
                "Báo cáo ca trực": ("shift_reports", "shift_reports"),
                "Phương tiện": ("vehicles", "vehicles"),
                "Nhiên liệu": ("fuel_reports", "fuel_reports"),
            }
            export_columns = {
                "Báo cáo ca trực": [
                    ("ngay", "NGÀY LÀM VIỆC"),
                    ("ca", "CA TRỰC"),
                    ("ho_ten", "HỌ VÀ TÊN"),
                    ("bo_phan", "ĐỘI/BỘ PHẬN"),
                    ("chuc_vu", "CHỨC VỤ"),
                    ("vi_tri", "VỊ TRÍ TRỰC"),
                    ("noi_dung", "NỘI DUNG CÔNG VIỆC"),
                    ("sdt", "SỐ ĐIỆN THOẠI"),
                ],
                "Phương tiện": [
                    ("ngay", "NGÀY"),
                    ("ngay_nhan_xe", "NGÀY NHẬN XE"),
                    ("bien_so", "BIỂN SỐ"),
                    ("loai_xe", "LOẠI XE"),
                    ("tinh_trang", "TÌNH TRẠNG"),
                    ("vi_tri", "VỊ TRÍ HOẠT ĐỘNG"),
                    ("so_km_hien_tai", "SỐ KM HIỆN TẠI"),
                    ("ngay_bao_duong_gan_nhat", "NGÀY BẢO DƯỠNG GẦN NHẤT"),
                    ("so_km_bao_duong_gan_nhat", "SỐ KM BẢO DƯỠNG GẦN NHẤT"),
                    ("so_km_bao_duong_du_kien", "SỐ KM BẢO DƯỠNG DỰ KIẾN"),
                ],
            }
            export_frames = {}
            missing_tables = []
            for sheet_name, (table_name, _) in export_tables.items():
                if not db_connected:
                    export_frames[sheet_name] = pd.DataFrame()
                    continue
                try:
                    response = supabase.table(table_name).select("*").execute()
                    table_frame = pd.DataFrame(response.data or [])
                except Exception as error:
                    if "PGRST205" in str(error) or f"public.{table_name}" in str(error):
                        missing_tables.append(table_name)
                        table_frame = pd.DataFrame()
                    else:
                        st.error(f"Không thể đọc bảng {table_name}: {error}")
                        table_frame = pd.DataFrame()
                if "ngay" in table_frame.columns:
                    parsed_dates = pd.to_datetime(
                        table_frame["ngay"], dayfirst=True, errors="coerce",
                    ).dt.date
                    table_frame = table_frame[
                        parsed_dates.between(export_start, export_end, inclusive="both")
                    ]
                if (
                    sheet_name == "Báo cáo ca trực"
                    and not table_frame.empty
                    and "bo_phan" in table_frame.columns
                    and "chuc_vu" in table_frame.columns
                ):
                    table_frame = table_frame.assign(
                        _team_sort=table_frame["bo_phan"].fillna("").astype(str).str.casefold(),
                        _location_sort=table_frame.get(
                            "vi_tri", pd.Series("", index=table_frame.index)
                        ).fillna("").astype(str).str.casefold(),
                        _role_name_sort=table_frame["chuc_vu"].fillna("").astype(str).str.casefold(),
                        _role_order=table_frame["chuc_vu"].fillna("").map(
                            lambda value: SHIFT_ROLE_PRIORITY.get(
                                str(value).strip(), 99
                            )
                        )
                    ).sort_values(
                        ["_team_sort", "_location_sort", "_role_order", "_role_name_sort"],
                        kind="stable",
                    ).drop(
                        columns=["_team_sort", "_location_sort", "_role_name_sort", "_role_order"]
                    )
                if sheet_name in export_columns:
                    ordered_columns = export_columns[sheet_name]
                    for source_column, _ in ordered_columns:
                        if source_column not in table_frame:
                            table_frame[source_column] = ""
                    table_frame = table_frame[
                        [source_column for source_column, _ in ordered_columns]
                    ].rename(
                        columns=dict(ordered_columns)
                    )
                else:
                    table_frame = table_frame.drop(
                        columns=["id", "phan_muc"], errors="ignore"
                    )
                export_frames[sheet_name] = table_frame

            output = BytesIO()
            with pd.ExcelWriter(output, engine="openpyxl") as writer:
                for sheet_name, table_frame in export_frames.items():
                    if table_frame.empty:
                        table_frame = pd.DataFrame(
                            {
                                "Ghi chú": [
                                    f"Không có dữ liệu từ {export_start:%d/%m/%Y} "
                                    f"đến {export_end:%d/%m/%Y}."
                                ]
                            }
                        )
                    worksheet_name = sheet_name[:31]
                    table_frame.to_excel(writer, sheet_name=worksheet_name, index=False)
                    worksheet = writer.sheets[worksheet_name]
                    worksheet.freeze_panes = "A2"
                    worksheet.auto_filter.ref = worksheet.dimensions
                    for cell in worksheet[1]:
                        cell.font = cell.font.copy(bold=True, color="FFFFFF")
                        cell.fill = cell.fill.copy(fill_type="solid", fgColor="1F4E78")
                    for column_cells in worksheet.columns:
                        column_letter = column_cells[0].column_letter
                        max_length = max(
                            len(str(cell.value)) if cell.value is not None else 0
                            for cell in column_cells
                        )
                        worksheet.column_dimensions[column_letter].width = min(
                            max(max_length + 2, 12), 45
                        )
                        for cell in column_cells:
                            cell.alignment = cell.alignment.copy(
                                vertical="top", wrap_text=True
                            )
            output.seek(0)
            if missing_tables:
                st.warning(
                    "Chưa có dữ liệu. Các sheet tương ứng được xuất kèm ghi chú."
                )
            st.download_button(
                "Tải báo cáo Excel",
                data=output.getvalue(),
                file_name=(
                    f"bao_cao_van_hanh_{export_start:%Y-%m-%d}.xlsx"
                    if export_start == export_end
                    else f"bao_cao_van_hanh_{export_start:%Y-%m-%d}_"
                    f"{export_end:%Y-%m-%d}.xlsx"
                ),
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                key="download_excel_report",
            )
            if st.session_state.get("cleanup_last_run") != date.today():
                deleted_counts, missing_cleanup_tables, cleanup_errors = (
                    cleanup_old_report_data(supabase, cleanup_cutoff_date)
                    if db_connected
                    else ({}, [], [])
                )
                st.session_state.cleanup_last_run = date.today()
                deleted_total = sum(deleted_counts.values())
                if deleted_total:
                    st.info(
                        f"Hệ thống đã tự động dọn {deleted_total} bản ghi cũ hơn 10 ngày "
                        f"(trước {cleanup_cutoff_date:%d/%m/%Y})."
                    )
                if missing_cleanup_tables:
                    st.caption(
                        "Bỏ qua bảng chưa có: "
                        + ", ".join(missing_cleanup_tables)
                        + "."
                    )
                if cleanup_errors:
                    st.error(
                        "Một số bảng chưa được dọn dẹp: "
                        + " | ".join(cleanup_errors)
                    )

selected_account = st.session_state.tab_accounts[menu]
can_edit_tab = (
    st.session_state.is_admin
    or (
        st.session_state.logged_in_user
        and st.session_state.logged_in_user == selected_account["username"]
    )
)

# ==================== 1. QUẢN LÝ BÁO CÁO CA TRỰC ====================
if menu == "Báo Cáo Ca Trực":
    # Lấy dữ liệu thật từ Database (Bảng: shift_reports)
    if db_connected:
        try:
            response = supabase.table("shift_reports").select("*").execute()
            data = response.data or []
        except Exception as error:
            data = []
            st.warning(f"Không thể đọc dữ liệu báo cáo ca trực: {error}")
    else:
        # Dữ liệu mẫu nếu chưa kết nối DB để test giao diện
        data = [
            {"id": 1, "ngay": "06/10/2026", "ca": "Ca 2 (14h-22h)", "phan_muc": "I. Phòng Vận hành", "bo_phan": "Tổ ITS", "vi_tri": "TMC TP.HCM-TL", "ho_ten": "Huỳnh Anh Tuấn", "so_nguoi": 1, "noi_dung": "Giám sát camera, trực hotline", "sdt": "0343089866"}
        ]
    
    df = pd.DataFrame(data)
    for column in ("ngay", "ca", "ho_ten", "bo_phan", "chuc_vu", "vi_tri", "noi_dung", "sdt"):
        if column not in df:
            df[column] = ""
    # Luôn mở lịch ở ngày hiện tại; nếu hôm nay chưa có dữ liệu, bảng sẽ để trống.
    default_date = date.today()
    selected_date = st.session_state.get("selected_date", default_date)
    if isinstance(selected_date, str):
        selected_date = pd.to_datetime(selected_date, dayfirst=True, errors="coerce")
        selected_date = selected_date.date() if pd.notna(selected_date) else default_date
    st.markdown('<div class="section-caption">LỊCH TRỰC VẬN HÀNH</div>', unsafe_allow_html=True)
    selected_date = st.date_input("Tìm ngày", value=selected_date, format="DD/MM/YYYY", key="selected_date")
    if not df.empty:
        df = df[pd.to_datetime(df["ngay"], dayfirst=True, errors="coerce").dt.date == selected_date]

    if not df.empty:
        df = df.assign(
            _team_sort=df["bo_phan"].fillna("").astype(str).str.casefold(),
            _location_sort=df["vi_tri"].fillna("").astype(str).str.casefold(),
            _role_name_sort=df["chuc_vu"].fillna("").astype(str).str.casefold(),
            _role_order=df["chuc_vu"].fillna("").map(
                lambda value: SHIFT_ROLE_PRIORITY.get(str(value).strip(), 99)
            )
        ).sort_values(
            ["_team_sort", "_location_sort", "_role_order", "_role_name_sort"],
            kind="stable",
        ).drop(columns=["_team_sort", "_location_sort", "_role_name_sort"])

    def make_schedule(source_df):
        def source_column_or_blank(name):
            if name in source_df:
                return source_df[name].fillna("")
            return pd.Series([""] * len(source_df), index=source_df.index)

        return pd.DataFrame({
            "NGÀY LÀM VIỆC": source_column_or_blank("ngay"),
            "CA TRỰC": source_column_or_blank("ca"),
            "HỌ VÀ TÊN": source_column_or_blank("ho_ten"),
            "ĐỘI/BỘ PHẬN": source_column_or_blank("bo_phan"),
            "CHỨC VỤ": source_column_or_blank("chuc_vu"),
            "VỊ TRÍ TRỰC": source_column_or_blank("vi_tri"),
            "NỘI DUNG CÔNG VIỆC": source_column_or_blank("noi_dung"),
            "SỐ ĐIỆN THOẠI": source_column_or_blank("sdt"),
        })

    def render_schedule_table(source_df):
        schedule = make_schedule(source_df)
        headers = "".join(f"<th>{html.escape(str(column))}</th>" for column in schedule.columns)
        rows = []
        previous_group = None
        group_index = -1
        for _, row in schedule.iterrows():
            group = (
                str(row["ĐỘI/BỘ PHẬN"]).strip() or "Chưa phân loại",
                str(row["VỊ TRÍ TRỰC"]).strip() or "Chưa phân loại",
            )
            if group != previous_group:
                group_index += 1
                background, foreground = REPORT_GROUP_COLORS[
                    group_index % len(REPORT_GROUP_COLORS)
                ]
                group_label = (
                    f"Đội/Bộ phận: {html.escape(group[0])}"
                    f" &nbsp;|&nbsp; Vị trí làm việc: {html.escape(group[1])}"
                )
                rows.append(
                    f'<tr class="schedule-group-row" style="background:{background};'
                    f'color:{foreground};"><td colspan="{len(schedule.columns)}">'
                    f"{group_label}</td></tr>"
                )
                previous_group = group
            cells = []
            for value in row:
                cell_value = html.escape(str(value) if pd.notna(value) else "").replace("\n", "<br>")
                cells.append(
                    f'<td style="background-color:{background};">{cell_value}</td>'
                )
            rows.append(f"<tr>{''.join(cells)}</tr>")
        table_html = f"""
        <div class="schedule-table-wrap">
            <table class="schedule-table">
                <thead><tr>{headers}</tr></thead>
                <tbody>{''.join(rows)}</tbody>
            </table>
        </div>
        """
        st.markdown(table_html, unsafe_allow_html=True)

    team_values = df["bo_phan"].map(normalize_report_label)
    shift_values = df["ca"].map(normalize_report_label)
    supplementary_mask = shift_values.str.startswith(
        normalize_report_label(SUPPLEMENTARY_SHIFT)
    )
    leave_mask = shift_values.str.startswith(
        (
            normalize_report_label("Nghỉ Phép"),
            normalize_report_label("Nghỉ Không Lương"),
        )
    )
    project_mask = (
        (team_values == normalize_report_label(PROJECT_TEAM))
        & ~leave_mask
    )
    traffic_safety_mask = (
        (team_values == normalize_report_label(TRAFFIC_SAFETY_TEAM))
        & ~leave_mask
    )
    special_assignment_mask = (
        project_mask | traffic_safety_mask | supplementary_mask | leave_mask
    )

    ca1_tab, ca2_tab, ca3_tab, project_tab, traffic_safety_tab, leave_tab, supplementary_tab = st.tabs(
        [
            "CA 1", "CA 2", "CA 3", "DỰ ÁN", "ĐẢM BẢO ATGT",
            "NGHỈ PHÉP, NGHỈ KHÔNG LƯƠNG", "NHÂN SỰ TĂNG CƯỜNG",
        ]
    )
    with ca1_tab:
        st.caption("Danh sách nhân sự trực HC, Ca 1 và Ca gãy.")
        if not df.empty:
            ca1_df = df[
                shift_values.str.startswith(("ca 1", "ca gãy", "hc"))
                & ~special_assignment_mask
            ]
            render_schedule_table(ca1_df)
        else:
            st.info("Chưa có dữ liệu.")
    with ca2_tab:
        st.caption("Danh sách nhân sự trực Ca 2.")
        if not df.empty:
            ca2_df = df[shift_values.str.startswith("ca 2") & ~special_assignment_mask]
            render_schedule_table(ca2_df)
        else:
            st.info("Chưa có dữ liệu.")
    with ca3_tab:
        st.caption("Danh sách nhân sự trực Ca 3.")
        if not df.empty:
            ca3_df = df[shift_values.str.startswith("ca 3") & ~special_assignment_mask]
            render_schedule_table(ca3_df)
        else:
            st.info("Chưa có dữ liệu.")
    with project_tab:
        st.caption(f"Danh sách nhân sự thuộc bộ phận {PROJECT_TEAM}.")
        if not df.empty:
            render_schedule_table(df[project_mask])
        else:
            st.info("Chưa có dữ liệu.")
    with traffic_safety_tab:
        st.caption(f"Danh sách nhân sự thuộc bộ phận {TRAFFIC_SAFETY_TEAM}.")
        if not df.empty:
            render_schedule_table(df[traffic_safety_mask])
        else:
            st.info("Chưa có dữ liệu.")
    with leave_tab:
        st.caption("Theo dõi nhân sự nghỉ phép và nghỉ không lương.")
        if not df.empty:
            render_schedule_table(df[leave_mask])
        else:
            st.info("Chưa có dữ liệu.")
    with supplementary_tab:
        st.caption("Danh sách nhân sự tăng cường.")
        if not df.empty:
            render_schedule_table(df[supplementary_mask])
        else:
            st.info("Chưa có dữ liệu.")

    # Chỉ Admin hoặc tài khoản được cấp cho tab này mới được thao tác dữ liệu.
    if can_edit_tab:
        st.markdown("---")
        if st.session_state.is_admin:
            st.info("**Khu vực thao tác dành cho Admin (Thêm / Sửa / Xóa trực tiếp vào Database)**")
        else:
            st.info("**Khu vực thao tác dành cho tài khoản Báo Cáo Ca Trực**")
        
        tab1, tab2 = st.tabs(["Thêm báo cáo mới", "Sửa / Xóa báo cáo"])
        
        with tab1:
            shift_form_version = st.session_state.get("shift_form_version", 0)
            role_options = [
                "Phó Giám Đốc", "Hạt Trưởng", "Hạt Phó", "Trưởng Phòng",
                "Phó Phòng","Trạm Phó", "Đội Trưởng", "Đội Phó", "Ca Trưởng",
                "Tổ Trưởng", "Kíp Trưởng", "HCNS", "Giám Đốc", "Nhân viên",
            ]
            add_errors = st.session_state.get("add_errors", {})
            team_options = sorted(set(df.get("bo_phan", pd.Series(dtype=str)).dropna().astype(str)) | {
                "Tổ ITS", "Đội PCCC&CHCN TLMT", "Đội PCCC&CHCN TPHCM-TL",
                "Hạt QLĐB", "TTP", "Tổ Điện", "Hotline", "Tuần Đường",
                "Ban Lãnh Đạo", "Phòng Tổng Hợp", "GSHK",
                TRAFFIC_SAFETY_TEAM, PROJECT_TEAM, "Lái Xe",
            })
            location_options = sorted(set(df.get("vi_tri", pd.Series(dtype=str)).dropna().astype(str)) | {
                "TMC TL-MT", "TMC TP.HCM-TL", "Tuyến cao tốc TL-MT", "Tuyến cao tốc TP.HCM-TL",
                "Tuyến cao tốc MT-CT", "TTP Cai Lậy", "TTP Thân Cửu Nghĩa"
            })
            ca_options = [
                "Ca 1 (06h-14h)", "Ca 2 (14h-22h)", "Ca 3 (22h-06h)",
                "Ca gãy (10h-18h)",
                "HC (Hành Chính)", "Nhân sự tăng cường", "Nghỉ Phép",
                "Nghỉ Không Lương",
            ]

            row_one = st.columns(3)
            with row_one[0]:
                r_ngay = st.date_input(
                    "Ngày làm việc", value=selected_date, format="DD/MM/YYYY",
                    key=f"add_date_{shift_form_version}",
                )
            with row_one[1]:
                r_bophan = st.selectbox(
                    "Đội / Bộ phận", ["", *team_options], index=0,
                    format_func=lambda value: value or " ",
                    key=f"add_team_{shift_form_version}",
                )
                if add_errors.get("bo_phan"):
                    st.error(add_errors["bo_phan"])
            with row_one[2]:
                r_vitri = st.selectbox(
                    "Vị trí trực", ["", *location_options], index=0,
                    format_func=lambda value: value or " ",
                    key=f"add_location_{shift_form_version}",
                )
                if add_errors.get("vi_tri"):
                    st.error(add_errors["vi_tri"])

            row_two = st.columns(3)
            with row_two[0]:
                r_ca = st.selectbox(
                    "Ca trực", ["", *ca_options], index=0,
                    format_func=lambda value: value or " ",
                    key=f"add_shift_{shift_form_version}",
                )
                if add_errors.get("ca"):
                    st.error(add_errors["ca"])
            with row_two[2]:
                r_songuoi = st.number_input(
                    "Số người", min_value=1, max_value=50, value=1, step=1,
                    key=f"add_people_count_{shift_form_version}",
                )

            with st.form("add_form"):
                person_names = []
                person_phones = []
                person_roles = []
                for person_index in range(r_songuoi):
                    st.markdown(f"**Nhân sự {person_index + 1}**")
                    person_col1, person_col2, person_col3 = st.columns(3)
                    with person_col1:
                        person_name = st.text_input(
                            "Họ và tên",
                            key=f"add_person_name_{shift_form_version}_{person_index}",
                        ).strip()
                    with person_col2:
                        person_phone = st.text_input(
                            "Số điện thoại (10 hoặc 11 chữ số)",
                            max_chars=11,
                            key=(
                                f"add_person_phone_{shift_form_version}_"
                                f"{person_index}"
                            ),
                        ).strip()
                        if add_errors.get(f"phone_{person_index}"):
                            st.error(add_errors[f"phone_{person_index}"])
                    with person_col3:
                        person_role = st.selectbox(
                            "Chức vụ",
                            ["", *role_options],
                            index=0,
                            format_func=lambda value: value or " ",
                            key=(
                                f"add_person_role_{shift_form_version}_"
                                f"{person_index}"
                            ),
                        )
                        if add_errors.get(f"role_{person_index}"):
                            st.error(add_errors[f"role_{person_index}"])
                    if add_errors.get(f"name_{person_index}"):
                        st.error(add_errors[f"name_{person_index}"])
                    person_names.append(person_name)
                    person_phones.append(person_phone)
                    person_roles.append(person_role)

                r_noidung = st.text_area(
                    "Nội dung công việc",
                    key=f"add_group_work_{shift_form_version}",
                )
                if add_errors.get("noi_dung"):
                    st.error(add_errors["noi_dung"])
                r_hoten = "\n".join(person_names)
                r_sdt = "\n".join(person_phones)
                
                if st.form_submit_button("Lưu vào cơ sở dữ liệu"):
                    validation_errors = {}
                    if not r_ca:
                        validation_errors["ca"] = "Vui lòng chọn Ca trực."
                    if not r_bophan:
                        validation_errors["bo_phan"] = "Vui lòng chọn Đội / Bộ phận."
                    if not r_vitri:
                        validation_errors["vi_tri"] = "Vui lòng chọn Vị trí trực."
                    if not r_noidung.strip():
                        validation_errors["noi_dung"] = "Nội dung công việc không được để trống."
                    for person_index, (name, phone, role) in enumerate(
                        zip(person_names, person_phones, person_roles)
                    ):
                        if not name.strip():
                            validation_errors[f"name_{person_index}"] = "Họ và tên không được để trống."
                        if not re.fullmatch(r"\d{10,11}", phone.strip()):
                            validation_errors[f"phone_{person_index}"] = "Số điện thoại phải đúng 10 hoặc 11 chữ số."
                        if not role:
                            validation_errors[f"role_{person_index}"] = "Vui lòng chọn Chức vụ."

                    if validation_errors:
                        st.session_state["add_errors"] = validation_errors
                        st.rerun()
                    elif db_connected:
                        st.session_state["add_errors"] = {}
                        try:
                            record = {
                                "ngay": r_ngay.strftime("%d/%m/%Y"), "ca": r_ca,
                                "phan_muc": "I. Phòng Vận hành",
                                "bo_phan": r_bophan, "vi_tri": r_vitri, "ho_ten": r_hoten,
                                "chuc_vu": "\n".join(person_roles), "so_nguoi": r_songuoi,
                                "noi_dung": r_noidung, "sdt": r_sdt
                            }
                            insert_response = (
                                supabase.table("shift_reports")
                                .insert(record)
                                .select("*")
                                .execute()
                            )
                            if not insert_response.data:
                                raise RuntimeError(
                                    "Supabase không trả về bản ghi sau khi thêm. "
                                    "Kiểm tra bảng shift_reports và quyền INSERT/SELECT (RLS)."
                                )
                        except Exception as error:
                            error_text = str(error)
                            if "42501" in error_text or "row-level security" in error_text:
                                st.error(
                                    "Không thể lưu dữ liệu vì Supabase đang chặn quyền INSERT "
                                    "bởi RLS của bảng shift_reports. Hãy chạy các policy "
                                    "shift_reports trong file vehicles_schema.sql trên "
                                    "Supabase SQL Editor, sau đó thử lại."
                                )
                            else:
                                st.error(f"Không thể lưu dữ liệu: {error}")
                        else:
                            clear_shift_form_state()
                            st.success("Đã thêm dữ liệu thành công vào Database!")
                            st.rerun()
                    else:
                        st.warning("Vui lòng cấu hình kết nối Supabase để lưu trữ.")

        with tab2:
            if data:
                search_text = st.text_input(
                    "Tìm nhanh báo cáo",
                    placeholder="Nhập ID, họ tên, đội/bộ phận, ca hoặc ngày...",
                    key="shift_report_edit_search",
                ).strip().casefold()
                filtered_reports = [
                    item
                    for item in data
                    if not search_text
                    or search_text in " ".join(
                        str(item.get(field, ""))
                        for field in (
                            "id", "ngay", "ca", "ho_ten", "bo_phan",
                            "chuc_vu", "vi_tri", "noi_dung",
                        )
                    ).casefold()
                ]
                if not filtered_reports:
                    st.info("Không tìm thấy báo cáo phù hợp.")
                    filtered_reports = []
                report_ids = [item["id"] for item in filtered_reports]
                selected_id = st.selectbox(
                    "Chọn ID mục cần sửa hoặc xóa",
                    report_ids,
                    format_func=lambda value: next(
                        (
                            f"{value} - {item.get('ho_ten', '')} - "
                            f"{item.get('ngay', '')}"
                            for item in filtered_reports
                            if item.get("id") == value
                        ),
                        str(value),
                    ),
                    key="shift_report_edit_id",
                ) if report_ids else None
                target = next(
                    (x for x in filtered_reports if x["id"] == selected_id),
                    None,
                )
                
                if target:
                    with st.form("edit_form"):
                        edit_date_value = pd.to_datetime(
                            target.get("ngay"), dayfirst=True, errors="coerce",
                        )
                        e_ngay = st.date_input(
                            "Ngày làm việc",
                            value=(
                                edit_date_value.date()
                                if pd.notna(edit_date_value)
                                else date.today()
                            ),
                            format="DD/MM/YYYY",
                            key=f"edit_shift_date_{selected_id}",
                        )
                        e_ca_options = list(ca_options)
                        if target.get("ca") and target["ca"] not in e_ca_options:
                            e_ca_options.append(target["ca"])
                        e_ca = st.selectbox(
                            "Ca trực",
                            ["", *e_ca_options],
                            index=(
                                e_ca_options.index(target.get("ca")) + 1
                                if target.get("ca") in e_ca_options else 0
                            ),
                            format_func=lambda value: value or " ",
                            key=f"edit_shift_{selected_id}",
                        )
                        e_team_options = list(team_options)
                        if target.get("bo_phan") and target["bo_phan"] not in e_team_options:
                            e_team_options.append(target["bo_phan"])
                        e_bophan = st.selectbox(
                            "Đội / Bộ phận",
                            ["", *e_team_options],
                            index=(
                                e_team_options.index(target.get("bo_phan")) + 1
                                if target.get("bo_phan") in e_team_options else 0
                            ),
                            format_func=lambda value: value or " ",
                            key=f"edit_shift_team_{selected_id}",
                        )
                        e_location_options = list(location_options)
                        if target.get("vi_tri") and target["vi_tri"] not in e_location_options:
                            e_location_options.append(target["vi_tri"])
                        e_vitri = st.selectbox(
                            "Vị trí trực",
                            ["", *e_location_options],
                            index=(
                                e_location_options.index(target.get("vi_tri")) + 1
                                if target.get("vi_tri") in e_location_options else 0
                            ),
                            format_func=lambda value: value or " ",
                            key=f"edit_shift_location_{selected_id}",
                        )
                        e_chucvu = st.text_area(
                            "Chức vụ",
                            value=str(target.get("chuc_vu", "")),
                            help="Nếu có nhiều nhân sự, nhập mỗi chức vụ trên một dòng tương ứng.",
                            key=f"edit_shift_role_{selected_id}",
                        )
                        e_songuoi = st.number_input(
                            "Số người", min_value=1, max_value=50,
                            value=max(1, int(target.get("so_nguoi") or 1)),
                            step=1,
                            key=f"edit_shift_people_{selected_id}",
                        )
                        e_hoten = st.text_input(
                            "Họ tên", value=str(target.get("ho_ten", "")),
                            key=f"edit_shift_name_{selected_id}",
                        )
                        e_sdt = st.text_input(
                            "Số điện thoại",
                            value=str(target.get("sdt", "")),
                            key=f"edit_shift_phone_{selected_id}",
                        )
                        e_noidung = st.text_area(
                            "Nội dung công việc",
                            value=str(target.get("noi_dung", "")),
                            key=f"edit_shift_work_{selected_id}",
                        )
                        
                        col_u, col_d = st.columns(2)
                        if col_u.form_submit_button("Cập nhật thay đổi"):
                            validation_error = None
                            if not e_ca or not e_bophan or not e_vitri or not e_chucvu:
                                validation_error = (
                                    "Vui lòng nhập đủ Ca trực, Đội/Bộ phận, "
                                    "Vị trí trực và Chức vụ."
                                )
                            elif not e_hoten.strip() or not e_noidung.strip():
                                validation_error = "Họ tên và nội dung công việc không được để trống."
                            elif any(
                                not re.fullmatch(r"\d{10,11}", phone.strip())
                                for phone in e_sdt.splitlines()
                                if phone.strip()
                            ):
                                validation_error = (
                                    "Mỗi số điện thoại phải có 10 hoặc 11 chữ số."
                                )
                            if validation_error:
                                st.error(validation_error)
                            elif db_connected:
                                try:
                                    update_payload = {
                                        "ngay": e_ngay.strftime("%d/%m/%Y"),
                                        "ca": e_ca,
                                        "bo_phan": e_bophan,
                                        "vi_tri": e_vitri,
                                        "chuc_vu": e_chucvu.strip(),
                                        "so_nguoi": e_songuoi,
                                        "ho_ten": e_hoten.strip(),
                                        "sdt": e_sdt.strip(),
                                        "noi_dung": e_noidung.strip(),
                                    }
                                    (
                                        supabase.table("shift_reports")
                                        .update(update_payload)
                                        .eq("id", selected_id)
                                        .execute()
                                    )
                                    updated_rows = (
                                        supabase.table("shift_reports")
                                        .select("*")
                                        .eq("id", selected_id)
                                        .execute()
                                        .data
                                        or []
                                    )
                                    if not updated_rows:
                                        raise RuntimeError(
                                            "Không tìm thấy bản ghi sau khi cập nhật. "
                                            "Kiểm tra ID và quyền SELECT trên Supabase."
                                        )
                                    saved_row = updated_rows[0]
                                    mismatched_fields = [
                                        field
                                        for field, expected in update_payload.items()
                                        if str(saved_row.get(field, "")) != str(expected)
                                    ]
                                    if mismatched_fields:
                                        raise RuntimeError(
                                            "Supabase không lưu được các trường: "
                                            + ", ".join(mismatched_fields)
                                            + ". Kiểm tra policy UPDATE/RLS của bảng "
                                            "shift_reports."
                                        )
                                except Exception as error:
                                    st.error(f"Không thể cập nhật ID {selected_id}: {error}")
                                else:
                                    saved_team = saved_row.get("bo_phan", "")
                                    st.success(
                                        f"Đã cập nhật ID {selected_id} thành công "
                                        f"(Đội/Bộ phận: {saved_team})."
                                    )
                                    st.rerun()
                            else:
                                st.warning("Vui lòng cấu hình kết nối Supabase để cập nhật.")
                                
                        if col_d.form_submit_button("Xóa mục này", type="primary"):
                            if db_connected:
                                try:
                                    delete_response = (
                                        supabase.table("shift_reports")
                                        .delete()
                                        .eq("id", selected_id)
                                        .select("id")
                                        .execute()
                                    )
                                    if not delete_response.data:
                                        raise RuntimeError(
                                            "Supabase không trả về bản ghi sau khi xóa. "
                                            "Kiểm tra ID hoặc quyền DELETE/SELECT (RLS)."
                                        )
                                except Exception as error:
                                    st.error(f"Không thể xóa ID {selected_id}: {error}")
                                else:
                                    st.error(f"Đã xóa ID {selected_id} khỏi Database!")
                                    st.rerun()
                            else:
                                st.warning("Vui lòng cấu hình kết nối Supabase để xóa.")

# ==================== 2. QUẢN LÝ PHƯƠNG TIỆN ====================
elif menu == "Phương Tiện":
    st.markdown('<div class="section-caption">QUẢN LÝ PHƯƠNG TIỆN</div>', unsafe_allow_html=True)
    vehicle_types = {
        "43C-264.94": "Xe bán tải",
        "43B-056.03": "Xe cứu thương Hyundai",
        "43H-021.35": "Xe tải thùng 3,5T",
        "43C-262.53": "Xe quét rác",
        "43C-270.17": "Xe cẩu thùng Hyundai",
        "29K-086.84": "Xe bán tải",
        "29K-213.98": "Xe bán tải",
        "29B-428.01": "Xe cứu thương Transit",
        "29K-292.08": "Xe quét rác",
        "51M-722.40": "Xe chữa cháy",
        "51M-679.34": "Xe stec nước",
        "29K-214.46": "Xe bán tải",
        "30B-402.28": "Xe bán tải",
        "30B-402.00": "Xe bán tải",
        "51E-041.51": "Xe chữa cháy",
        "30B-456.83": "Xe tải Cabin kép",
        "51K-061.29": "Xe tải thùng 3,5T",
    }
    vehicle_type_options = [
        "",
        "Xe tải thùng 3,5T",
        "Xe quét rác",
        "Xe cẩu thùng Hyundai",
        "Xe bán tải",
        "Xe cứu thương Hyundai",
        "Xe cứu thương Transit",
        "Xe chữa cháy",
        "Xe stec nước",
        "Xe tải Cabin kép",
    ]
    vehicle_statuses = ["Hoạt động bình thường", "Bảo dưỡng sửa chữa", "Hư hỏng"]
    vehicle_locations = [
        "BĐH CT MT-CT", "XN QLVH TL-MT", "BĐH CT HCM-TL",
        "BĐH Đảm bảo ATGT",
    ]

    if "vehicle_reports" not in st.session_state:
        st.session_state.vehicle_reports = []

    vehicle_db_available = db_connected
    if vehicle_db_available:
        try:
            vehicle_response = supabase.table("vehicles").select("*").execute()
            vehicle_data = vehicle_response.data or []
        except Exception as error:
            vehicle_db_available = False
            vehicle_data = []
            if "PGRST205" in str(error) or "public.vehicles" in str(error):
                st.warning("Chưa có bảng dữ liệu phương tiện trên Supabase. Vui lòng tạo bảng `vehicles` trước khi sử dụng lưu dữ liệu.")
            else:
                st.error(f"Không thể đọc dữ liệu phương tiện: {error}")
    else:
        vehicle_data = st.session_state.vehicle_reports
        st.warning("Chưa cấu hình Supabase. Dữ liệu phương tiện hiện chỉ lưu trong phiên làm việc.")

    vehicle_df = pd.DataFrame(vehicle_data)
    for item in vehicle_data:
        plate = str(item.get("bien_so", "")).strip()
        vehicle_type = str(item.get("loai_xe", "")).strip()
        if plate and vehicle_type:
            vehicle_types.setdefault(plate, vehicle_type)
    vehicle_display_df = vehicle_df.copy()
    if not vehicle_display_df.empty:
        for column in (
            "id", "ngay", "ngay_nhan_xe", "bien_so", "loai_xe", "tinh_trang",
            "vi_tri", "so_km_hien_tai", "ngay_bao_duong_gan_nhat",
            "so_km_bao_duong_gan_nhat", "so_km_bao_duong_du_kien",
        ):
            if column not in vehicle_display_df:
                vehicle_display_df[column] = ""
        selected_vehicle_date = st.date_input(
            "Tìm ngày", value=date.today(), format="DD/MM/YYYY",
            key="vehicle_selected_date",
        )
        parsed_vehicle_dates = pd.to_datetime(
            vehicle_display_df["ngay"], dayfirst=True, errors="coerce",
        ).dt.date
        vehicle_display_df = vehicle_display_df[parsed_vehicle_dates == selected_vehicle_date]
        vehicle_display_df = vehicle_display_df.sort_values(
            "vi_tri",
            key=lambda values: values.fillna("").astype(str).str.casefold(),
            kind="stable",
        )
        vehicle_display_df = vehicle_display_df[
            [
                "id", "ngay", "ngay_nhan_xe", "bien_so", "loai_xe", "tinh_trang",
                "vi_tri", "so_km_hien_tai", "ngay_bao_duong_gan_nhat",
                "so_km_bao_duong_gan_nhat", "so_km_bao_duong_du_kien",
            ]
        ]
        vehicle_display_df = vehicle_display_df.rename(columns={
            "ngay": "NGÀY", "ngay_nhan_xe": "NGÀY NHẬN XE",
            "bien_so": "BIỂN SỐ", "loai_xe": "LOẠI XE",
            "tinh_trang": "TÌNH TRẠNG", "vi_tri": "VỊ TRÍ HOẠT ĐỘNG",
            "so_km_hien_tai": "SỐ KM HIỆN TẠI",
            "ngay_bao_duong_gan_nhat": "NGÀY BẢO DƯỠNG GẦN NHẤT",
            "so_km_bao_duong_gan_nhat": "SỐ KM BẢO DƯỠNG GẦN NHẤT",
            "so_km_bao_duong_du_kien": "SỐ KM BẢO DƯỠNG DỰ KIẾN",
        })
        if not vehicle_display_df.empty:
            st.dataframe(vehicle_display_df.drop(columns=["id"]), use_container_width=True, hide_index=True)
        else:
            st.info("Chưa có báo cáo phương tiện trong ngày đã chọn.")
    else:
        st.date_input(
            "Tìm ngày", value=date.today(), format="DD/MM/YYYY",
            key="vehicle_selected_date",
        )
        st.info("Chưa có báo cáo phương tiện.")

    if can_edit_tab:
        st.markdown("---")
        if st.session_state.is_admin:
            st.info("**Khu vực thao tác dành cho Admin (Thêm / Sửa / Xóa trực tiếp vào Database)**")
        else:
            st.info("**Khu vực thao tác dành cho tài khoản Phương Tiện**")

        add_vehicle_tab, add_new_vehicle_tab, edit_vehicle_tab = st.tabs(
            ["Thêm báo cáo", "Thêm xe mới", "Sửa / Xóa báo cáo"]
        )
        known_plates = list(vehicle_types)
        if not vehicle_df.empty and "bien_so" in vehicle_df:
            known_plates = list(dict.fromkeys(
                known_plates + [
                    str(value).strip()
                    for value in vehicle_df["bien_so"].tolist()
                    if str(value).strip()
                ]
            ))

        with add_vehicle_tab:
            vehicle_form_version = st.session_state.get("vehicle_form_version", 0)
            with st.form("add_vehicle_report"):
                add_date = st.date_input(
                    "Ngày báo cáo", value=date.today(), format="DD/MM/YYYY",
                    key=f"vehicle_add_date_{vehicle_form_version}",
                )
                add_received_date = st.date_input(
                    "Ngày nhận xe", value=date.today(), format="DD/MM/YYYY",
                    key=f"vehicle_add_received_date_{vehicle_form_version}",
                )
                selected_plate = st.selectbox(
                    "Biển số", ["", *known_plates],
                    format_func=lambda value: value or " ",
                    key=f"vehicle_add_plate_{vehicle_form_version}",
                )
                add_plate = selected_plate
                suggested_type = vehicle_types.get(selected_plate, "")
                suggested_type_index = (
                    vehicle_type_options.index(suggested_type)
                    if suggested_type in vehicle_type_options else 0
                )
                add_type = st.selectbox(
                    "Loại xe", vehicle_type_options,
                    index=suggested_type_index,
                    format_func=lambda value: value or " ",
                    key=f"vehicle_add_type_{vehicle_form_version}_{selected_plate or 'blank'}",
                )
                add_status = st.selectbox(
                    "Tình trạng", ["", *vehicle_statuses],
                    format_func=lambda value: value or " ",
                    key=f"vehicle_add_status_{vehicle_form_version}",
                )
                add_location = st.selectbox(
                    "Vị trí hoạt động", ["", *vehicle_locations],
                    format_func=lambda value: value or " ",
                    key=f"vehicle_add_location_{vehicle_form_version}",
                )
                add_current_km = st.number_input(
                    "Số Km hiện tại", min_value=0, step=1,
                    key=f"vehicle_add_current_km_{vehicle_form_version}",
                )
                add_last_service_date = st.date_input(
                    "Ngày bảo dưỡng gần nhất", value=date.today(),
                    format="DD/MM/YYYY",
                    key=f"vehicle_add_last_service_date_{vehicle_form_version}",
                )
                add_last_service_km = st.number_input(
                    "Số Km bảo dưỡng gần nhất", min_value=0, step=1,
                    key=f"vehicle_add_last_service_km_{vehicle_form_version}",
                )
                add_expected_service_km = st.number_input(
                    "Số Km bảo dưỡng dự kiến", min_value=0, step=1,
                    key=f"vehicle_add_expected_service_km_{vehicle_form_version}",
                )

                if st.form_submit_button("Lưu báo cáo"):
                    if not add_plate:
                        st.error("Vui lòng chọn hoặc nhập biển số xe.")
                    elif not add_type.strip():
                        st.error("Loại xe không được để trống.")
                    elif not add_status:
                        st.error("Vui lòng chọn tình trạng xe.")
                    elif not add_location:
                        st.error("Vui lòng chọn vị trí hoạt động.")
                    else:
                        record = {
                            "ngay": add_date.strftime("%d/%m/%Y"),
                            "ngay_nhan_xe": add_received_date.strftime("%d/%m/%Y"),
                            "bien_so": add_plate,
                            "loai_xe": add_type.strip(),
                            "tinh_trang": add_status,
                            "vi_tri": add_location,
                            "so_km_hien_tai": add_current_km,
                            "ngay_bao_duong_gan_nhat": add_last_service_date.strftime("%d/%m/%Y"),
                            "so_km_bao_duong_gan_nhat": add_last_service_km,
                            "so_km_bao_duong_du_kien": add_expected_service_km,
                        }
                        if vehicle_db_available:
                            try:
                                supabase.table("vehicles").insert(record).execute()
                            except Exception as error:
                                st.error(f"Không thể lưu báo cáo phương tiện: {error}")
                            else:
                                clear_vehicle_form_state()
                                st.success("Đã thêm báo cáo phương tiện.")
                                st.rerun()
                        else:
                            record["id"] = len(st.session_state.vehicle_reports) + 1
                            st.session_state.vehicle_reports.append(record)
                            clear_vehicle_form_state()
                            st.success("Đã thêm báo cáo trong phiên làm việc.")
                            st.rerun()

        with add_new_vehicle_tab:
            vehicle_form_version = st.session_state.get("vehicle_form_version", 0)
            st.info(
                "Nhập thủ công biển số và loại xe mới. Có thể sử dụng mục này "
                "khi danh mục chưa có xe hoặc bảng `vehicles` chưa được tạo."
            )
            with st.form("add_new_vehicle"):
                new_vehicle_date = st.date_input(
                    "Ngày báo cáo", value=date.today(), format="DD/MM/YYYY",
                    key=f"vehicle_new_date_{vehicle_form_version}",
                )
                new_vehicle_received_date = st.date_input(
                    "Ngày nhận xe", value=date.today(), format="DD/MM/YYYY",
                    key=f"vehicle_new_received_date_{vehicle_form_version}",
                )
                new_vehicle_plate = st.text_input(
                    "Biển số xe mới",
                    key=f"vehicle_new_plate_{vehicle_form_version}",
                ).strip().upper()
                new_vehicle_type = st.text_input(
                    "Loại xe",
                    key=f"vehicle_new_type_{vehicle_form_version}",
                    help="Nhập đúng tên loại xe theo thực tế.",
                ).strip()
                new_vehicle_status = st.selectbox(
                    "Tình trạng", ["", *vehicle_statuses],
                    format_func=lambda value: value or " ",
                    key=f"vehicle_new_status_{vehicle_form_version}",
                )
                new_vehicle_location = st.selectbox(
                    "Vị trí hoạt động", ["", *vehicle_locations],
                    format_func=lambda value: value or " ",
                    key=f"vehicle_new_location_{vehicle_form_version}",
                )
                new_vehicle_current_km = st.number_input(
                    "Số Km hiện tại", min_value=0, step=1,
                    key=f"vehicle_new_current_km_{vehicle_form_version}",
                )
                new_vehicle_last_service_date = st.date_input(
                    "Ngày bảo dưỡng gần nhất", value=date.today(),
                    format="DD/MM/YYYY",
                    key=f"vehicle_new_last_service_date_{vehicle_form_version}",
                )
                new_vehicle_last_service_km = st.number_input(
                    "Số Km bảo dưỡng gần nhất", min_value=0, step=1,
                    key=f"vehicle_new_last_service_km_{vehicle_form_version}",
                )
                new_vehicle_expected_service_km = st.number_input(
                    "Số Km bảo dưỡng dự kiến", min_value=0, step=1,
                    key=f"vehicle_new_expected_service_km_{vehicle_form_version}",
                )

                if st.form_submit_button("Lưu xe mới"):
                    if not new_vehicle_plate:
                        st.error("Vui lòng nhập biển số xe.")
                    elif not new_vehicle_type:
                        st.error("Vui lòng nhập loại xe.")
                    elif not new_vehicle_status:
                        st.error("Vui lòng chọn tình trạng xe.")
                    elif not new_vehicle_location:
                        st.error("Vui lòng chọn vị trí hoạt động.")
                    else:
                        new_vehicle_record = {
                            "ngay": new_vehicle_date.strftime("%d/%m/%Y"),
                            "ngay_nhan_xe": new_vehicle_received_date.strftime("%d/%m/%Y"),
                            "bien_so": new_vehicle_plate,
                            "loai_xe": new_vehicle_type,
                            "tinh_trang": new_vehicle_status,
                            "vi_tri": new_vehicle_location,
                            "so_km_hien_tai": new_vehicle_current_km,
                            "ngay_bao_duong_gan_nhat": new_vehicle_last_service_date.strftime("%d/%m/%Y"),
                            "so_km_bao_duong_gan_nhat": new_vehicle_last_service_km,
                            "so_km_bao_duong_du_kien": new_vehicle_expected_service_km,
                        }
                        if vehicle_db_available:
                            try:
                                supabase.table("vehicles").insert(new_vehicle_record).execute()
                            except Exception as error:
                                st.error(f"Không thể lưu xe mới: {error}")
                            else:
                                clear_vehicle_form_state()
                                st.success("Đã thêm xe mới.")
                                st.rerun()
                        else:
                            new_vehicle_record["id"] = len(st.session_state.vehicle_reports) + 1
                            st.session_state.vehicle_reports.append(new_vehicle_record)
                            clear_vehicle_form_state()
                            st.success("Đã thêm xe mới trong phiên làm việc.")
                            st.rerun()

        with edit_vehicle_tab:
            if vehicle_data:
                report_ids = [item.get("id") for item in vehicle_data if item.get("id") is not None]
                selected_vehicle_id = st.selectbox("Chọn ID mục cần sửa hoặc xóa", report_ids)
                vehicle_target = next(
                    (item for item in vehicle_data if item.get("id") == selected_vehicle_id),
                    None,
                )
                if vehicle_target:
                    with st.form("edit_vehicle_report"):
                        edit_date_value = pd.to_datetime(
                            vehicle_target.get("ngay"), dayfirst=True, errors="coerce",
                        )
                        edit_date = st.date_input(
                            "Ngày báo cáo",
                            value=edit_date_value.date() if pd.notna(edit_date_value) else date.today(),
                            format="DD/MM/YYYY",
                            key="vehicle_edit_date",
                        )
                        edit_received_date_value = pd.to_datetime(
                            vehicle_target.get("ngay_nhan_xe"), dayfirst=True, errors="coerce",
                        )
                        edit_received_date = st.date_input(
                            "Ngày nhận xe",
                            value=(
                                edit_received_date_value.date()
                                if pd.notna(edit_received_date_value)
                                else date.today()
                            ),
                            format="DD/MM/YYYY",
                            key="vehicle_edit_received_date",
                        )
                        edit_plate = st.text_input(
                            "Biển số", value=str(vehicle_target.get("bien_so", "")),
                            key="vehicle_edit_plate",
                        ).strip().upper()
                        edit_type = st.text_input(
                            "Loại xe", value=str(vehicle_target.get("loai_xe", "")),
                            key="vehicle_edit_type",
                        )
                        edit_status = st.selectbox(
                            "Tình trạng", vehicle_statuses,
                            index=vehicle_statuses.index(vehicle_target.get("tinh_trang"))
                            if vehicle_target.get("tinh_trang") in vehicle_statuses else 0,
                            key="vehicle_edit_status",
                        )
                        edit_location = st.selectbox(
                            "Vị trí hoạt động", vehicle_locations,
                            index=vehicle_locations.index(vehicle_target.get("vi_tri"))
                            if vehicle_target.get("vi_tri") in vehicle_locations else 0,
                            key="vehicle_edit_location",
                        )
                        edit_current_km = st.number_input(
                            "Số Km hiện tại", min_value=0, step=1,
                            value=vehicle_km_value(vehicle_target.get("so_km_hien_tai")),
                            key="vehicle_edit_current_km",
                        )
                        edit_last_service_date_value = pd.to_datetime(
                            vehicle_target.get("ngay_bao_duong_gan_nhat"),
                            dayfirst=True, errors="coerce",
                        )
                        edit_last_service_date = st.date_input(
                            "Ngày bảo dưỡng gần nhất",
                            value=(
                                edit_last_service_date_value.date()
                                if pd.notna(edit_last_service_date_value)
                                else date.today()
                            ),
                            format="DD/MM/YYYY",
                            key="vehicle_edit_last_service_date",
                        )
                        edit_last_service_km = st.number_input(
                            "Số Km bảo dưỡng gần nhất", min_value=0, step=1,
                            value=vehicle_km_value(
                                vehicle_target.get("so_km_bao_duong_gan_nhat")
                            ),
                            key="vehicle_edit_last_service_km",
                        )
                        edit_expected_service_km = st.number_input(
                            "Số Km bảo dưỡng dự kiến", min_value=0, step=1,
                            value=vehicle_km_value(
                                vehicle_target.get("so_km_bao_duong_du_kien")
                            ),
                            key="vehicle_edit_expected_service_km",
                        )
                        update_vehicle, delete_vehicle = st.columns(2)
                        update_clicked = update_vehicle.form_submit_button("Cập nhật thay đổi")
                        delete_clicked = delete_vehicle.form_submit_button("Xóa báo cáo", type="secondary")

                    if update_clicked:
                        if not edit_plate or not edit_type.strip():
                            st.error("Biển số và loại xe không được để trống.")
                        else:
                            updated_record = {
                                "ngay": edit_date.strftime("%d/%m/%Y"),
                                "ngay_nhan_xe": edit_received_date.strftime("%d/%m/%Y"),
                                "bien_so": edit_plate,
                                "loai_xe": edit_type.strip(),
                                "tinh_trang": edit_status,
                                "vi_tri": edit_location,
                                "so_km_hien_tai": edit_current_km,
                                "ngay_bao_duong_gan_nhat": edit_last_service_date.strftime("%d/%m/%Y"),
                                "so_km_bao_duong_gan_nhat": edit_last_service_km,
                                "so_km_bao_duong_du_kien": edit_expected_service_km,
                            }
                            if vehicle_db_available:
                                try:
                                    supabase.table("vehicles").update(updated_record).eq(
                                        "id", selected_vehicle_id
                                    ).execute()
                                except Exception as error:
                                    st.error(f"Không thể cập nhật báo cáo phương tiện: {error}")
                                else:
                                    st.success("Đã cập nhật báo cáo phương tiện.")
                                    st.rerun()
                            else:
                                for index, item in enumerate(st.session_state.vehicle_reports):
                                    if item.get("id") == selected_vehicle_id:
                                        st.session_state.vehicle_reports[index] = {
                                            **updated_record, "id": selected_vehicle_id,
                                        }
                                        break
                                st.success("Đã cập nhật báo cáo trong phiên làm việc.")
                                st.rerun()

                    if delete_clicked:
                        if vehicle_db_available:
                            try:
                                supabase.table("vehicles").delete().eq(
                                    "id", selected_vehicle_id
                                ).execute()
                            except Exception as error:
                                st.error(f"Không thể xóa báo cáo phương tiện: {error}")
                            else:
                                st.success("Đã xóa báo cáo phương tiện.")
                                st.rerun()
                        else:
                            st.session_state.vehicle_reports = [
                                item for item in st.session_state.vehicle_reports
                                if item.get("id") != selected_vehicle_id
                            ]
                            st.success("Đã xóa báo cáo trong phiên làm việc.")
                            st.rerun()
            else:
                st.info("Chưa có báo cáo để sửa hoặc xóa.")

# ==================== 3. QUẢN LÝ NHIÊN LIỆU ====================
elif menu == "Nhiên Liệu":
    st.markdown('<div class="section-caption">QUẢN LÝ NHIÊN LIỆU</div>', unsafe_allow_html=True)
    st.info("Khu vực theo dõi số lít xăng/dầu và chi phí cấp phát cho từng xe.")