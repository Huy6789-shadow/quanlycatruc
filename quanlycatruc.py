import streamlit as st
import pandas as pd
from supabase import create_client, Client

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

st.set_page_config(page_title="Phần Mềm Quản Lý Vận Hành Cao Tốc", layout="wide")

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

st.title(" QUẢN LÝ VẬN HÀNH CA TRỰC")
st.markdown("---")

# ==================== 1. QUẢN LÝ BÁO CÁO CA TRỰC ====================
if menu == " Quản Lý Báo Cáo Ca Trực":
    st.subheader(" Danh Sách Báo Cáo Ca Trực")
    
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
    if not df.empty:
        st.dataframe(df, use_container_width=True, hide_index=True)
    else:
        st.info("Chưa có dữ liệu báo cáo trong hệ thống.")

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