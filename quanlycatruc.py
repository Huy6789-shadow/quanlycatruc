import base64
from pathlib import Path

import streamlit as st
import pandas as pd
from supabase import create_client, Client

st.set_page_config(page_title="Lịch trực công tác quản lý vận hành", layout="wide", initial_sidebar_state="collapsed")

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Roboto+Condensed:wght@400;600;700&display=swap');
:root { --navy:#142b78; --red:#c62f2f; --line:#d8d8d8; --paper:#fffef8; }
.stApp { background:#f7f4df; color:#414141; font-family:'Roboto Condensed','Arial Narrow',Arial,sans-serif; }
.block-container { max-width:1440px; padding:.5rem .35rem 2rem; }
[data-testid="stHeader"] { background:transparent; }
.stSidebar, [data-testid="stSidebar"] { width:300px !important; }
[data-testid="stSidebar"] > div:first-child { width:300px !important; }
.agency-header { background:var(--paper); border-bottom:4px solid #edcf62; min-height:112px; display:grid; grid-template-columns:minmax(180px,28%) minmax(0,1fr) 44px; align-items:center; gap:1rem; padding:.45rem 1rem; }
.agency-logo { display:block; width:100%; max-width:245px; height:94px; object-fit:contain; object-position:left center; }
.agency-copy { flex:1; text-align:center; }
.agency-copy h1 { color:var(--navy); font-size:clamp(1rem,2.1vw,1.9rem); line-height:1.1; margin:0; font-weight:700; text-wrap:balance; }
.agency-copy p { color:var(--red); font-weight:700; font-size:clamp(.75rem,1.25vw,1.2rem); line-height:1.15; margin:.55rem 0 0; text-wrap:balance; }
.print-box { width:28px; height:28px; border:1px solid #888; background:#fff; justify-self:end; align-self:start; margin:.8rem .1rem 0 0; }
.date-strip { background:#fff; border:1px solid #eadb98; color:var(--red); text-align:center; font-weight:700; font-size:1.2rem; padding:.45rem .5rem; margin:.6rem 0; }
.section-caption { background:#fff; border:1px solid var(--line); color:var(--red); font-weight:700; text-align:center; padding:.55rem; margin-top:.25rem; }
.stTabs [data-baseweb="tab-list"] { gap:0; background:#e5ebf0; border:1px solid var(--line); }
.stTabs [data-baseweb="tab"] { flex:1; justify-content:center; border-right:1px solid #fff; color:#222; font-weight:700; padding:.65rem; }
.stTabs [aria-selected="true"] { background:#fff; color:var(--red); }
.stDataFrame { background:#fff; }
.admin-panel { background:#fff; border-top:3px solid var(--navy); padding:.75rem; margin-top:1rem; }
@media (max-width:650px) { .agency-header{min-height:78px;grid-template-columns:92px 1fr 0;padding:.25rem;gap:.4rem;} .agency-logo{height:66px;} .agency-copy p{font-size:.7rem;} .print-box{display:none;} .date-strip{font-size:.85rem;} }
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

# --- QUẢN LÝ PHÂN QUYỀN ADMIN ---
if "is_admin" not in st.session_state:
    st.session_state.is_admin = False

st.sidebar.title(" Quản Lý Vận Hành")
menu = st.sidebar.selectbox("Chức năng", [
    " Quản Lý Báo Cáo Ca Trực", 
    " Quản Lý Phương Tiện", 
    " Quản Lý Nhiên Liệu",
    " Nhân Sự Nghỉ Phép"
])

st.sidebar.markdown("---")
st.sidebar.subheader("Quyền Quản Trị")
if not st.session_state.is_admin:
    with st.sidebar.form("login"):
        pwd = st.text_input("Mật khẩu Admin", type="password")
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
if menu == " Quản Lý Báo Cáo Ca Trực":
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
    available_dates = []
    if not df.empty and "ngay" in df:
        parsed_dates = pd.to_datetime(df["ngay"], dayfirst=True, errors="coerce")
        available_dates = sorted(parsed_dates.dropna().dt.strftime("%d/%m/%Y").unique(), reverse=True)

    logo_path = Path(__file__).with_name("deocalogo.jpg")
    logo_data = base64.b64encode(logo_path.read_bytes()).decode("ascii") if logo_path.exists() else ""
    default_date = available_dates[0] if available_dates else "Tất cả ngày"
    selected_date = st.session_state.get("selected_date", default_date)
    if selected_date not in ["Tất cả ngày", *available_dates]:
        selected_date = "Tất cả ngày"
    display_date = selected_date if selected_date != "Tất cả ngày" else (available_dates[0] if available_dates else "Chưa có dữ liệu")

    st.markdown(f"""
    <header class="agency-header">
        <img class="agency-logo" src="data:image/jpeg;base64,{logo_data}" alt="DEOCA GROUP">
        <div class="agency-copy">
            <h1>CÔNG TY CỔ PHẦN TẬP ĐOÀN ĐÈO CẢ</h1>
            <p>LỊCH TRỰC CÔNG TÁC QUẢN LÝ VẬN HÀNH TPHCM - TL - MT</p>
        </div>
        <div class="print-box" aria-label="Trạng thái in"></div>
    </header>
    <div class="date-strip">CA TRỰC - NGÀY: {display_date}</div>
    """, unsafe_allow_html=True)

    st.markdown('<div class="section-caption">LỊCH TRỰC VẬN HÀNH</div>', unsafe_allow_html=True)
    filter_options = ["Tất cả ngày", *available_dates]
    selected_date = st.selectbox("Tìm ngày ca trực", filter_options, index=filter_options.index(selected_date), key="selected_date")
    if selected_date != "Tất cả ngày" and not df.empty:
        df = df[pd.to_datetime(df["ngay"], dayfirst=True, errors="coerce").dt.strftime("%d/%m/%Y") == selected_date]

    if not df.empty:
        def column_or_blank(name):
            if name in df:
                return df[name].fillna("")
            return pd.Series([""] * len(df), index=df.index)

        schedule = pd.DataFrame({
            "STT": range(1, len(df) + 1),
            "VỊ TRÍ": column_or_blank("vi_tri"),
            "HỌ VÀ TÊN": column_or_blank("ho_ten"),
            "ĐIỆN THOẠI": column_or_blank("sdt"),
            "GHI CHÚ": column_or_blank("noi_dung"),
        })
        st.dataframe(schedule, use_container_width=True, hide_index=True, height=440)
    else:
        st.info("Chưa có dữ liệu báo cáo trong hệ thống.")

    plan_tab, work_tab, schedule_tab = st.tabs(["CA TRỰC VẬN HÀNH", "KẾ HOẠCH CÔNG VIỆC", "LỊCH TRỰC"])
    with plan_tab:
        st.caption("Danh sách nhân sự và vị trí đang trực trong ca hiện tại.")
    with work_tab:
        st.caption("Các công việc quan trọng được phân công trong ngày.")
    with schedule_tab:
        st.caption("Theo dõi lịch trực theo từng ca vận hành.")

    # NẾU LÀ ADMIN THÌ ĐƯỢC THÊM / SỬA / XÓA THẬT
    if st.session_state.is_admin:
        st.markdown("---")
        st.info("⚙️ **Khu vực thao tác dành cho Admin (Thêm / Sửa / Xóa trực tiếp vào Database)**")
        
        tab1, tab2 = st.tabs(["➕ Thêm báo cáo mới", "✏️ Sửa / Xóa báo cáo"])
        
        with tab1:
            with st.form("add_form"):
                c1, c2, c3 = st.columns(3)
                with c1:
                    r_ngay = st.text_input("Ngày báo cáo", value="06/10/2026")
                    r_ca = st.selectbox("Ca trực", ["Ca 1 (06h-14h)", "Ca 2 (14h-22h)", "Ca 3 (22h-06h)"])
                with c2:
                    r_phanmuc = st.selectbox("Phân mục", ["I. Phòng Vận hành", "II. Đội PCCC & CNCN", "III. Hạt QLDB", "IV. TTP TL-MT"])
                    r_bophan = st.text_input("Đội / Bộ phận")
                with c3:
                    r_vitri = st.text_input("Vị trí trực")
                    r_songuoi = st.number_input("Số người", min_value=1, value=1)
                
                r_hoten = st.text_input("Họ và tên")
                r_sdt = st.text_input("Số điện thoại")
                r_noidung = st.text_area("Nội dung công việc")
                
                if st.form_submit_button("Lưu vào cơ sở dữ liệu"):
                    if db_connected:
                        supabase.table("shift_reports").insert({
                            "ngay": r_ngay, "ca": r_ca, "phan_muc": r_phanmuc,
                            "bo_phan": r_bophan, "vi_tri": r_vitri, "ho_ten": r_hoten,
                            "so_nguoi": r_songuoi, "noi_dung": r_noidung, "sdt": r_sdt
                        }).execute()
                        st.success("Đã thêm dữ liệu thành công vào Database!")
                        st.rerun()
                    else:
                        st.warning("Vui lòng cấu hình kết nối Supabase để lưu trữ thật.")

        with tab2:
            if data:
                report_ids = [item["id"] for item in data]
                selected_id = st.selectbox("Chọn ID mục cần sửa hoặc xóa", report_ids)
                target = next((x for x in data if x["id"] == selected_id), None)
                
                if target:
                    with st.form("edit_form"):
                        e_hoten = st.text_input("Họ tên", value=target["ho_ten"])
                        e_noidung = st.text_area("Nội dung", value=target["noi_dung"])
                        
                        col_u, col_d = st.columns(2)
                        if col_u.form_submit_button("Cập nhật thay đổi"):
                            if db_connected:
                                supabase.table("shift_reports").update({
                                    "ho_ten": e_hoten, "noi_dung": e_noidung
                                }).eq("id", selected_id).execute()
                                st.success(f"Đã cập nhật ID {selected_id} thành công!")
                                st.rerun()
                                
                        if col_d.form_submit_button("Xóa mục này", type="primary"):
                            if db_connected:
                                supabase.table("shift_reports").delete().eq("id", selected_id).execute()
                                st.error(f"Đã xóa ID {selected_id} khỏi Database!")
                                st.rerun()

# ==================== 2. QUẢN LÝ PHƯƠNG TIỆN ====================
elif menu == " Quản Lý Phương Tiện":
    st.subheader(" Quản Lý Trạng Thái Phương Tiện & Xe Tuần Tra")
    # Tương tự cấu trúc bảng vehicles trên Database
    st.info("Khu vực quản lý danh sách xe, biển số và trạng thái hoạt động thực tế.")

# ==================== 3. QUẢN LÝ NHIÊN LIỆU ====================
elif menu == " Quản Lý Nhiên Liệu":
    st.subheader(" Quản Lý Cấp Phát Nhiên Liệu Xe")
    st.info("Khu vực theo dõi số lít xăng/dầu và chi phí cấp phát cho từng xe.")

# ==================== 4. NHÂN SỰ NGHỈ PHÉP ====================
elif menu == " Nhân Sự Nghỉ Phép":
    st.subheader(" Quản Lý Biến Động Nhân Sự Ca Trực")
    st.info("Khu vực ghi nhận nhân sự nghỉ phép, nghỉ ốm trong ngày.")