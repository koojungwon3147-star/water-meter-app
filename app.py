import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import pandas as pd
from datetime import datetime

st.set_page_config(
    page_title="대전회관 수도계량기 검침 대장",
    page_icon="💧",
    layout="centered"
)

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
    sheet_url = st.secrets.get("spreadsheet_url", None)
    if sheet_url:
        doc = client.open_by_url(sheet_url)
    else:
        doc = client.open("대전회관 수도계량기 검침")
    return doc.get_worksheet(0)

# --- 계량기 정보 정의 (시트의 행 번호와 정확히 매핑) ---
# D열 = 1월(4번째 열) ~ O열 = 12월(15번째 열)
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

# --- 커스텀 스타일 헤더 UI ---
header_html = """
<div style="background-color: #1a1e36; border-radius: 8px; padding: 12px 18px; margin-bottom: 20px; border: 1px solid #2d3356;">
    <div style="color: #ffffff; font-size: 13px; font-weight: bold; margin-bottom: 8px; letter-spacing: 0.5px;">
        티피에스 주식회사 | 대전회관
    </div>
    <div style="border-top: 1px solid #3b426e; padding-top: 10px; display: flex; align-items: center;">
        <span style="font-size: 24px; margin-right: 10px;">💧</span>
        <span style="color: #38bdf8; font-size: 20px; font-weight: 800; margin-right: 8px;">대전회관</span>
        <span style="color: #ffffff; font-size: 20px; font-weight: 800;">수도계량기 검침 대장</span>
    </div>
</div>
"""
st.markdown(header_html, unsafe_allow_html=True)

# 검침 월 선택 (현재 월 자동 선택)
current_month = datetime.today().month
selected_month = st.selectbox(
    "📅 검침 월 선택",
    options=list(range(1, 13)),
    index=current_month - 1,
    format_func=lambda x: f"{x}월"
)

# 구글 시트 해당 월 컬럼 (D열 = 4열)
col_idx = selected_month + 3

# 시트 데이터 불러오기
try:
    ws = get_worksheet()
    current_values = ws.col_values(col_idx)
    prev_values = ws.col_values(col_idx - 1) if col_idx > 4 else []
except Exception as e:
    st.error(f"구글 시트를 불러오지 못했습니다. 연동 설정을 확인해주세요: {e}")
    st.stop()

st.divider()

# 계량기 선택
meter_names = [m["name"] for m in METERS]
selected_meter_name = st.selectbox("📍 검침 대상 선택", meter_names)

target_meter = next(m for m in METERS if m["name"] == selected_meter_name)
meter_row = target_meter["row"]

# 기존 지침값
existing_val = ""
if len(current_values) >= meter_row:
    existing_val = current_values[meter_row - 1]

# 전월 지침값
prev_val = ""
if prev_values and len(prev_values) >= meter_row:
    prev_val = prev_values[meter_row - 1]

# 정보 표시 메트릭
col1, col2 = st.columns(2)
with col1:
    st.metric("계량기 종류", target_meter["type"])
with col2:
    st.metric(
        f"전월({selected_month-1}월) 지침" if selected_month > 1 else "전월 지침", 
        prev_val if prev_val else "기록 없음"
    )

# 입력 폼
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
                ws.update_cell(meter_row, col_idx, input_val.strip())
                st.success(f"✅ [{selected_meter_name}] {selected_month}월 지침 ({input_val.strip()}) 저장 완료!")
                st.rerun()
            except Exception as ex:
                st.error(f"저장 실패: {ex}")

# 하단 전체 진행 현황표
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
