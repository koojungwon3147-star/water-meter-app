import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import pandas as pd
from datetime import datetime

st.set_page_config(page_title="대전회관 수도계량기 검침", page_icon="💧", layout="centered")

# --- 구글 시트 연동 설정 ---
SCOPE = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

@st.cache_resource
def get_gspread_client():
    creds_dict = st.secrets["gcp_service_account"]
    creds = Credentials.from_service_account_info(creds_dict, scopes=SCOPE)
    return gspread.authorize(creds)

def get_worksheet():
    client = get_gspread_client()
    # secrets에 sheet_url이 있으면 URL로, 없으면 기본 이름으로 엽니다.
    sheet_url = st.secrets.get("spreadsheet_url", None)
    if sheet_url:
        doc = client.open_by_url(sheet_url)
    else:
        doc = client.open("대전회관 수도계량기 검침")
    return doc.get_worksheet(0)

# --- 계량기 정보 정의 (시트의 행 번호와 매핑) ---
# D열이 1월(4), E=2월(5), ..., H=5월(8), ..., O=12월(15)
METERS = [
    {"name": "1F 외곽 메인 시수", "row": 2, "type": "시수"},
    {"name": "3F 식당홀", "row": 3, "type": "시수"},
    {"name": "3F 주방", "row": 4, "type": "시수"},
    {"name": "2F 예약실", "row": 5, "type": "시수"},
    {"name": "2F 박기섭 한의원 (시수)", "row": 6, "type": "시수"},
    {"name": "2F 박기섭 한의원 (온수)", "row": 7, "type": "온수"},
    {"name": "1F 헤이커피", "row": 8, "type": "시수"},
    {"name": "1F 고반식당", "row": 9, "type": "시수"},
    {"name": "1F 치과 (시수)", "row": 10, "type": "시수"},
    {"name": "1F 치과 (온수)", "row": 11, "type": "온수"},
    {"name": "1F 정수", "row": 12, "type": "정수"},
    {"name": "B1F 볼링장 세탁실 (시수)", "row": 13, "type": "시수"},
    {"name": "B1F 볼링장 세탁실 (온수)", "row": 14, "type": "온수"},
    {"name": "B1F 골프장 (시수)", "row": 15, "type": "시수"},
    {"name": "B1F 골프장 (온수)", "row": 16, "type": "온수"},
    {"name": "B5F 기계실 유량계", "row": 17, "type": "유량계"},
]

# --- UI 화면 구성 ---
st.title("💧 대전회관 수도계량기 검침")

# 검침 월 선택 (기본값: 현재 월)
current_month = datetime.today().month
selected_month = st.selectbox(
    "📅 검침 월 선택",
    options=list(range(1, 13)),
    index=current_month - 1,
    format_func=lambda x: f"{x}월"
)

# 구글 시트에서 월에 해당하는 열 번호 계산 (D열 = 1월 = 4번째 열)
col_idx = selected_month + 3

try:
    ws = get_worksheet()
    current_values = ws.col_values(col_idx)
    
    # 전월 지침(사용량 참고용) 가져오기
    prev_values = ws.col_values(col_idx - 1) if col_idx > 4 else []
except Exception as e:
    st.error(f"구글 시트를 불러오지 못했습니다. 연동 설정을 확인해주세요: {e}")
    st.stop()

st.divider()

# 계량기 선택
meter_names = [m["name"] for m in METERS]
selected_meter_name = st.selectbox("📍 검침할 계량기 선택", meter_names)

target_meter = next(m for m in METERS if m["name"] == selected_meter_name)
meter_row = target_meter["row"]

# 현재 입력되어 있는 값 확인
existing_val = ""
if len(current_values) >= meter_row:
    existing_val = current_values[meter_row - 1]

# 전월 지침값 확인
prev_val = ""
if prev_values and len(prev_values) >= meter_row:
    prev_val = prev_values[meter_row - 1]

# 정보 표시 박스
col1, col2 = st.columns(2)
with col1:
    st.metric("종류", target_meter["type"])
with col2:
    st.metric(f"전월({selected_month-1}월) 지침" if selected_month > 1 else "전월 지침", 
              prev_val if prev_val else "기록 없음")

# 지침 입력 폼
with st.form("reading_form", clear_on_submit=False):
    input_val = st.text_input(
        f"당월 ({selected_month}월) 지침 입력", 
        value=existing_val, 
        placeholder="예: 1254.3"
    )
    
    submitted = st.form_submit_button("💾 시트에 저장하기", use_container_width=True)
    
    if submitted:
        if not input_val.strip():
            st.warning("지침 값을 입력해주세요.")
        else:
            try:
                # 구글 시트에 업데이트
                ws.update_cell(meter_row, col_idx, input_val.strip())
                st.success(f"✅ [{selected_meter_name}] {selected_month}월 지침 ({input_val.strip()}) 저장 완료!")
                st.rerun()
            except Exception as ex:
                st.error(f"저장 실패: {ex}")

# 현황 요약
with st.expander(f"📋 {selected_month}월 전체 입력 현황 보기"):
    summary_data = []
    for m in METERS:
        r = m["row"]
        val = current_values[r - 1] if len(current_values) >= r else ""
        status = "✅ 완료" if val else "⬜ 미입력"
        summary_data.append({
            "계량기명": m["name"],
            "구분": m["type"],
            "지침": val,
            "상태": status
        })
    df_summary = pd.DataFrame(summary_data)
    st.dataframe(df_summary, use_container_width=True, hide_index=True)
