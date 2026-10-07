import base64
import html
import re
from datetime import date
from pathlib import Path

import streamlit as st
import pandas as pd
from supabase import create_client, Client

st.set_page_config(page_title="Quản lý vận hành", layout="wide", initial_sidebar_state="collapsed")

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Roboto+Condensed:wght@400;600;700&display=swap');
:root { --navy:#142b78; --red:#c62f2f; --line:#d8d8d8; --paper:#fffef8; }
.stApp { background:#f7f4df; color:#414141; font-family:'Roboto Condensed','Arial Narrow',Arial,sans-serif; width:100%; overflow-x:hidden; }
.block-container { width:100%; max-width:1440px; box-sizing:border-box; margin:0 auto; padding:.5rem clamp(.3rem,1vw,.75rem) 2rem; }
[data-testid="stHeader"] { background:transparent; }
.stSidebar, [data-testid="stSidebar"] { width:300px !important; }
[data-testid="stSidebar"] > div:first-child { width:300px !important; }
.agency-header { background:var(--paper); border-bottom:4px solid #edcf62; min-height:112px; display:grid; grid-template-columns:minmax(180px,25%) minmax(0,50%) minmax(0,25%); align-items:center; gap:1rem; padding:.45rem 1rem; }
.agency-logo { display:block; width:100%; max-width:245px; height:94px; object-fit:contain; object-position:left center; }
.agency-copy { grid-column:2; min-width:0; text-align:center; }
.agency-copy h1 { color:var(--navy); font-size:clamp(1.15rem,2.5vw,2.3rem); line-height:1.1; margin:0; font-weight:700; text-wrap:balance; }
.agency-copy p { color:var(--red); font-weight:700; font-size:clamp(.95rem,1.8vw,1.6rem); line-height:1.15; letter-spacing:.01em; margin:.55rem 0 0; text-wrap:balance; }
.date-strip { background:#fff; border:1px solid #eadb98; color:var(--red); text-align:center; font-weight:700; font-size:1.2rem; padding:.45rem .5rem; margin:.6rem 0; }
.section-caption { background:#fff; border:1px solid var(--line); color:var(--red); font-weight:700; text-align:center; padding:.55rem; margin-top:.25rem; }
/* Xóa khoảng cách (gap) giữa các ô Tab để chúng dính sát vào nhau */
div[role="tablist"] {
    gap: 0 !important;
}

/* Tùy chỉnh thiết kế cơ bản cho từng ô Tab */
button[data-testid="stTab"] { 
    flex: 1 1 0 !important; 
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
button[data-testid="stTab"]:not(:first-child) {
    border-left: none !important;
}

/* Tùy chỉnh nút Tab đang được chọn (Active) */
button[data-testid="stTab"][aria-selected="true"] { 
    background: #fff !important; 
    color: var(--red) !important; 
    border-bottom: 2px solid var(--red) !important; /* Chỉ tạo gạch đỏ nhẹ ở dưới */
    box-shadow: none !important; /* Xóa bỏ vạch đỏ mập ở phía trên */
}
.stDataFrame { background:#fff; }
.schedule-table-wrap { width:100%; overflow-x:auto; margin:.4rem 0 1rem; }
.schedule-table { width:100%; border-collapse:collapse; background:#fff; color:#111; font-size:.9rem; }
.schedule-table th, .schedule-table td { border:1px solid #d9d9d9; padding:.55rem .5rem; text-align:left; vertical-align:top; white-space:normal; }
.schedule-table th { background:#edf1f5; color:#111; font-weight:700; }
.schedule-table td { background:#fff; color:#111; line-height:1.45; }
.admin-panel { background:#fff; border-top:3px solid var(--navy); padding:.75rem; margin-top:1rem; }
@media (max-width:650px) {
    .stSidebar, [data-testid="stSidebar"] { width:85vw !important; max-width:300px !important; }
    [data-testid="stSidebar"] > div:first-child { width:85vw !important; max-width:300px !important; }
    .block-container { padding:.25rem .3rem 1.25rem; }
    .agency-header { min-height:0; display:flex; flex-direction:column; justify-content:center; padding:.5rem .35rem .6rem; gap:.2rem; }
    .agency-logo { order:1; width:150px; height:70px; max-width:150px; object-position:center; }
    .agency-copy { order:2; grid-column:auto; width:100%; text-align:center; }
    .agency-copy h1 { font-size:clamp(1.15rem,5.5vw,1.55rem); line-height:1.08; text-align:center; }
    .agency-copy p { font-size:clamp(.78rem,3.5vw,.95rem); line-height:1.12; margin:.35rem auto 0; text-align:center; max-width:360px; }
    .date-strip { font-size:.78rem; padding:.42rem .25rem; margin:.4rem 0; }
    .section-caption { font-size:.9rem; padding:.5rem .25rem; }
    .stTabs [data-baseweb="tab"] { font-size:.62rem; line-height:1.1; padding:.55rem .18rem; white-space:normal; text-align:center; }
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

# --- QUẢN LÝ PHÂN QUYỀN ADMIN ---
if "is_admin" not in st.session_state:
    st.session_state.is_admin = False

st.sidebar.title(" Quản Lý Vận Hành")
menu = st.sidebar.selectbox("Chức năng", [
    " Báo Cáo Ca Trực", 
    " Phương Tiện", 
    " Nhiên Liệu"
])

st.sidebar.markdown("---")
st.sidebar.subheader("Quản trị")
if not st.session_state.is_admin:
    with st.sidebar.form("login"):
        pwd = st.text_input("Mật khẩu", type="password")
        if st.form_submit_button("Đăng nhập"):
            if pwd == "admin123":
                st.session_state.is_admin = True
                st.rerun()
            else:
                st.sidebar.error("Sai mật khẩu!")
else:
    st.sidebar.success("Đang đăng nhập: **ADMIN**")
    if st.sidebar.button("Đăng xuất"):
        st.session_state.is_admin = False
        st.rerun()

# ==================== 1. QUẢN LÝ BÁO CÁO CA TRỰC ====================
if menu == " Báo Cáo Ca Trực":
    # Lấy dữ liệu thật từ Database (Bảng: shift_reports)
    if db_connected:
        try:
            response = supabase.table("shift_reports").select("*").execute()
            data = response.data
        except:
            data = []
    else:
        # Dữ liệu mẫu nếu chưa kết nối DB để test giao diện
        data = [
            {"id": 1, "ngay": "06/10/2026", "ca": "Ca 2 (14h-22h)", "phan_muc": "I. Phòng Vận hành", "bo_phan": "Tổ ITS", "vi_tri": "TMC TP.HCM-TL", "ho_ten": "Huỳnh Anh Tuấn", "so_nguoi": 1, "noi_dung": "Giám sát camera, trực hotline", "sdt": "0343089866"}
        ]
    
    df = pd.DataFrame(data)
    parsed_dates = pd.to_datetime(df["ngay"], dayfirst=True, errors="coerce") if "ngay" in df else pd.Series(dtype="datetime64[ns]")
    latest_date = parsed_dates.max()
    default_date = latest_date.date() if pd.notna(latest_date) else pd.Timestamp.today().date()
    selected_date = st.session_state.get("selected_date", default_date)
    if isinstance(selected_date, str):
        selected_date = pd.to_datetime(selected_date, dayfirst=True, errors="coerce")
        selected_date = selected_date.date() if pd.notna(selected_date) else default_date
    display_date = selected_date.strftime("%d/%m/%Y")

    render_agency_header(display_date)

    st.markdown('<div class="section-caption">LỊCH TRỰC VẬN HÀNH</div>', unsafe_allow_html=True)
    selected_date = st.date_input("Tìm ngày", value=selected_date, format="DD/MM/YYYY", key="selected_date")
    if not df.empty:
        df = df[pd.to_datetime(df["ngay"], dayfirst=True, errors="coerce").dt.date == selected_date]

    if not df.empty:
        df = df.sort_values("bo_phan", key=lambda values: values.fillna("").astype(str).str.casefold())

    def make_schedule(source_df):
        def source_column_or_blank(name):
            if name in source_df:
                return source_df[name].fillna("")
            return pd.Series([""] * len(source_df), index=source_df.index)

        return pd.DataFrame({
            "NGÀY LÀM VIỆC": source_column_or_blank("ngay"),
            "ĐỘI/BỘ PHẬN": source_column_or_blank("bo_phan"),
            "CA TRỰC": source_column_or_blank("ca"),
            "VỊ TRÍ TRỰC": source_column_or_blank("vi_tri"),
            "HỌ VÀ TÊN": source_column_or_blank("ho_ten"),
            "CHỨC VỤ": source_column_or_blank("chuc_vu"),
            "NỘI DUNG CÔNG VIỆC": source_column_or_blank("noi_dung"),
            "SỐ ĐIỆN THOẠI": source_column_or_blank("sdt"),
        })

    def render_schedule_table(source_df):
        schedule = make_schedule(source_df)
        headers = "".join(f"<th>{html.escape(str(column))}</th>" for column in schedule.columns)
        rows = []
        for _, row in schedule.iterrows():
            cells = []
            for value in row:
                cell_value = html.escape(str(value) if pd.notna(value) else "").replace("\n", "<br>")
                cells.append(f"<td>{cell_value}</td>")
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

    ca1_tab, ca2_tab, ca3_tab, leave_tab = st.tabs(["CA 1", "CA 2", "CA 3", "NHÂN SỰ NGHỈ PHÉP"])
    with ca1_tab:
        st.caption("Danh sách nhân sự trực Ca 1.")
        if not df.empty:
            ca1_df = df[df["ca"].fillna("").astype(str).str.startswith(("Ca 1", "HC"))]
            render_schedule_table(ca1_df)
        else:
            st.info("Chưa có dữ liệu Ca 1.")
    with ca2_tab:
        st.caption("Danh sách nhân sự trực Ca 2.")
        if not df.empty:
            ca2_df = df[df["ca"].fillna("").astype(str).str.startswith("Ca 2")]
            render_schedule_table(ca2_df)
        else:
            st.info("Chưa có dữ liệu Ca 2.")
    with ca3_tab:
        st.caption("Danh sách nhân sự trực Ca 3.")
        if not df.empty:
            ca3_df = df[df["ca"].fillna("").astype(str).str.startswith("Ca 3")]
            render_schedule_table(ca3_df)
        else:
            st.info("Chưa có dữ liệu Ca 3.")
    with leave_tab:
        st.caption("Theo dõi nhân sự nghỉ phép.")
        if not df.empty:
            leave_df = df[df["ca"].fillna("").astype(str).str.startswith("Nghỉ Phép")]
            render_schedule_table(leave_df)
        else:
            st.info("Chưa có dữ liệu nghỉ phép.")

    # NẾU LÀ ADMIN THÌ ĐƯỢC THÊM / SỬA / XÓA THẬT
    if st.session_state.is_admin:
        st.markdown("---")
        st.info("**Khu vực thao tác dành cho Admin (Thêm / Sửa / Xóa trực tiếp vào Database)**")
        
        tab1, tab2 = st.tabs(["Thêm báo cáo mới", "Sửa / Xóa báo cáo"])
        
        with tab1:
            role_options = [
                "Phó Giám Đốc", "Tổ Trưởng", "Đội Trưởng", "Đội Phó",
                "Hạt Trưởng", "Hạt Phó", "Trưởng Phòng", "Phó Phòng",
                "Nhân viên",
            ]
            add_errors = st.session_state.get("add_errors", {})
            team_options = sorted(set(df.get("bo_phan", pd.Series(dtype=str)).dropna().astype(str)) | {
                "Tổ ITS", "Đội PCCC&CHCN TLMT", "Đội PCCC&CHCN TPHCM-TL",
                "Hạt QLĐB", "TTP", "Tổ Điện", "Hotline", "Tuần Đường",
                "Ban Lãnh Đạo", "Phòng Tổng Hợp"
            })
            location_options = sorted(set(df.get("vi_tri", pd.Series(dtype=str)).dropna().astype(str)) | {
                "TMC TL-MT", "TMC TP.HCM-TL", "Tuyến cao tốc TL-MT", "Tuyến cao tốc TP.HCM-TL",
                "Tuyến cao tốc MT-CT", "TTP Cai Lậy", "TTP Thân Cửu Nghĩa"
            })
            ca_options = [
                "Ca 1 (06h-14h)", "Ca 2 (14h-22h)", "Ca 3 (22h-06h)",
                "HC (Hành Chính)", "Nghỉ Phép"
            ]

            row_one = st.columns(3)
            with row_one[0]:
                r_ngay = st.date_input("Ngày làm việc", value=selected_date, format="DD/MM/YYYY")
            with row_one[1]:
                r_bophan = st.selectbox(
                    "Đội / Bộ phận", ["", *team_options], index=0,
                    format_func=lambda value: value or " ", key="add_team",
                )
                if add_errors.get("bo_phan"):
                    st.error(add_errors["bo_phan"])
            with row_one[2]:
                r_vitri = st.selectbox(
                    "Vị trí trực", ["", *location_options], index=0,
                    format_func=lambda value: value or " ", key="add_location",
                )
                if add_errors.get("vi_tri"):
                    st.error(add_errors["vi_tri"])

            row_two = st.columns(3)
            with row_two[0]:
                r_ca = st.selectbox(
                    "Ca trực", ["", *ca_options], index=0,
                    format_func=lambda value: value or " ", key="add_shift",
                )
                if add_errors.get("ca"):
                    st.error(add_errors["ca"])
            with row_two[1]:
                r_chucvu = st.selectbox(
                    "Chức vụ", ["", *role_options], index=0,
                    format_func=lambda value: value or " ", key="add_role",
                )
                if add_errors.get("chuc_vu"):
                    st.error(add_errors["chuc_vu"])
            with row_two[2]:
                r_songuoi = st.number_input(
                    "Số người", min_value=1, max_value=50, value=1, step=1,
                    key="add_people_count",
                )

            with st.form("add_form"):
                person_names = []
                person_phones = []
                for person_index in range(r_songuoi):
                    st.markdown(f"**Nhân sự {person_index + 1}**")
                    person_col1, person_col2 = st.columns(2)
                    with person_col1:
                        person_name = st.text_input(
                            "Họ và tên",
                            key=f"add_person_name_{person_index}",
                        )
                    with person_col2:
                        person_phone = st.text_input(
                            "Số điện thoại",
                            key=f"add_person_phone_{person_index}",
                        )
                        if add_errors.get(f"phone_{person_index}"):
                            st.error(add_errors[f"phone_{person_index}"])
                    if add_errors.get(f"name_{person_index}"):
                        st.error(add_errors[f"name_{person_index}"])
                    person_names.append(person_name)
                    person_phones.append(person_phone)

                r_noidung = st.text_area("Nội dung công việc", key="add_group_work")
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
                    if not r_chucvu:
                        validation_errors["chuc_vu"] = "Vui lòng chọn Chức vụ."
                    if not r_noidung.strip():
                        validation_errors["noi_dung"] = "Nội dung công việc không được để trống."
                    for person_index, (name, phone) in enumerate(zip(person_names, person_phones)):
                        if not name.strip():
                            validation_errors[f"name_{person_index}"] = "Họ và tên không được để trống."
                        if not re.fullmatch(r"\d{10}", phone.strip()):
                            validation_errors[f"phone_{person_index}"] = "Số điện thoại phải đúng 10 chữ số."

                    if validation_errors:
                        st.session_state["add_errors"] = validation_errors
                        st.rerun()
                    elif db_connected:
                        st.session_state["add_errors"] = {}
                        try:
                            supabase.table("shift_reports").insert({
                                "ngay": r_ngay.strftime("%d/%m/%Y"), "ca": r_ca,
                                "phan_muc": "I. Phòng Vận hành",
                                "bo_phan": r_bophan, "vi_tri": r_vitri, "ho_ten": r_hoten,
                                "chuc_vu": r_chucvu, "so_nguoi": r_songuoi,
                                "noi_dung": r_noidung, "sdt": r_sdt
                            }).execute()
                        except Exception as error:
                            st.error(f"Không thể lưu dữ liệu: {error}")
                        else:
                            st.success("Đã thêm dữ liệu thành công vào Database!")
                            st.rerun()
                    else:
                        st.warning("Vui lòng cấu hình kết nối Supabase để lưu trữ.")

        with tab2:
            if data:
                report_ids = [item["id"] for item in data]
                selected_id = st.selectbox("Chọn ID mục cần sửa hoặc xóa", report_ids)
                target = next((x for x in data if x["id"] == selected_id), None)
                
                if target:
                    with st.form("edit_form"):
                        e_hoten = st.text_input("Họ tên", value=target["ho_ten"])
                        e_sdt = st.text_input("Số điện thoại", value=target["sdt"])
                        e_noidung = st.text_area("Nội dung", value=target["noi_dung"])
                        
                        col_u, col_d = st.columns(2)
                        if col_u.form_submit_button("Cập nhật thay đổi"):
                            if db_connected:
                                supabase.table("shift_reports").update({
                                    "ho_ten": e_hoten, "sdt": e_sdt, "noi_dung": e_noidung
                                }).eq("id", selected_id).execute()
                                st.success(f"Đã cập nhật ID {selected_id} thành công!")
                                st.rerun()
                                
                        if col_d.form_submit_button("Xóa mục này", type="primary"):
                            if db_connected:
                                supabase.table("shift_reports").delete().eq("id", selected_id).execute()
                                st.error(f"Đã xóa ID {selected_id} khỏi Database!")
                                st.rerun()

# ==================== 2. QUẢN LÝ PHƯƠNG TIỆN ====================
elif menu == " Phương Tiện":
    render_agency_header(date.today().strftime("%d/%m/%Y"))
    st.subheader(" Quản lý trạng thái phương tiện & Xe Tuần Tra")
    # Tương tự cấu trúc bảng vehicles trên Database
    st.info("Khu vực quản lý danh sách xe, biển số và trạng thái hoạt động thực tế.")

# ==================== 3. QUẢN LÝ NHIÊN LIỆU ====================
elif menu == " Nhiên Liệu":
    render_agency_header(date.today().strftime("%d/%m/%Y"))
    st.subheader(" Quản lý cấp phát nhiên liệu cho xe")
    st.info("Khu vực theo dõi số lít xăng/dầu và chi phí cấp phát cho từng xe.")