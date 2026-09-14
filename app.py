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

# --- 계량기 마스터 목록 (시트 행 번호 기준) ---
METERS = [
    {"id": 1, "name": "1F 외곽 메인 시수", "row": 2, "type": "시수"},
    {"id": 2, "name": "3F 식당홀", "row": 3, "type": "시수"},
    {"id": 3, "name": "3F 주방", "row": 4, "type": "시수"},
    {"id": 4, "name": "2F 예약실", "row": 5, "type": "시수"},
    {"id": 5, "name": "2F 박기섭 한의원 (시수)", "row": 6, "type": "시수"},
    {"id": 6, "name": "2F 박기섭 한의원 (온수)", "row": 7, "type": "온수"},
    {"id": 7, "name": "1F 헤이커피", "row": 8, "type": "시수"},
    {"id": 8, "name": "1F 고반식당", "row": 9, "type": "시수"},
    {"id": 9, "name": "1F 치과 (시수)", "row": 10, "type": "시수"},
    {"id": 10, "name": "1F 치과 (온수)", "row": 11, "type": "온수"},
    {"id": 11, "name": "1F 정수", "row": 12, "type": "정수"},
    {"id": 12, "name": "B1F 볼링장 세탁실 (시수)", "row": 13, "type": "시수"},
    {"id": 13, "name": "B1F 볼링장 세탁실 (온수)", "row": 14, "type": "온수"},
    {"id": 14, "name": "B1F 골프장 (시수)", "row": 15, "type": "시수"},
    {"id": 15, "name": "B1F 골프장 (온수)", "row": 16, "type": "온수"},
    {"id": 16, "name": "B5F 기계실 유량계", "row": 17, "type": "유량계"},
]

# --- 상단 헤더 ---
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

# 검침 월 선택 (1월~12월)
current_year = datetime.today().year
current_month = datetime.today().month

month_options = list(range(1, 13))
st.markdown("**검침 대상 월 선택**")
selected_month = st.selectbox(
    "검침 대상 월 선택",
    options=month_options,
    index=current_month - 1,
    format_func=lambda x: f"{current_year}년 {x}월",
    label_visibility="collapsed"
)

# 구글 시트 해당 월 컬럼 (D열 = 1월 = 4번째 열)
col_idx = selected_month + 3

# 시트 데이터 불러오기
try:
    ws = get_worksheet()
    current_values = ws.col_values(col_idx)
    prev_values = ws.col_values(col_idx - 1) if col_idx > 4 else []
except Exception as e:
    st.error(f"구글 시트를 불러오지 못했습니다. 연동 설정을 확인해주세요: {e}")
    st.stop()

# --- 상태 파악 (완료 / 미완료) ---
meter_status = []
completed_count = 0

for m in METERS:
    r = m["row"]
    val = current_values[r - 1].strip() if len(current_values) >= r else ""
    is_done = bool(val)
    if is_done:
        completed_count += 1
    
    prev_val = prev_values[r - 1].strip() if len(prev_values) >= r and prev_values else ""
    meter_status.append({
        "meter": m,
        "val": val,
        "prev_val": prev_val,
        "is_done": is_done
    })

total_count = len(METERS)
progress_ratio = completed_count / total_count
progress_percent = int(progress_ratio * 100)

# --- 진행 현황 바 ---
st.markdown(f"**검침 진행 현황: {completed_count} / {total_count}개 완료 ({progress_percent}%)**")
st.progress(progress_ratio)

# --- 필터 및 새로고침 컨트롤 ---
c_check, c_refresh = st.columns([7, 3])
with c_check:
    show_only_uninspected = st.checkbox("미검침 계량기만 보기", value=False)
with c_refresh:
    if st.button("새로고침", use_container_width=True):
        st.rerun()

st.divider()

# --- 대상 계량기 필터링 ---
if show_only_uninspected:
    selectable_items = [item for item in meter_status if not item["is_done"]]
    if not selectable_items:
        st.success("🎉 이번 달 모든 수도계량기 검침이 완료되었습니다!")
        st.stop()
else:
    selectable_items = meter_status

meter_name_list = [item["meter"]["name"] for item in selectable_items]

# 세션 상태로 현재 선택된 계량기 인덱스 관리
if "selected_meter_idx" not in st.session_state:
    st.session_state.selected_meter_idx = 0

# 인덱스 유효성 검사
if st.session_state.selected_meter_idx >= len(meter_name_list):
    st.session_state.selected_meter_idx = 0

selected_meter_name = st.selectbox(
    "📍 검침 대상 계량기 선택",
    options=meter_name_list,
    index=st.session_state.selected_meter_idx
)

# 현재 선택된 아이템 찾기
current_item = next(item for item in selectable_items if item["meter"]["name"] == selected_meter_name)
current_meter = current_item["meter"]

# 메트릭 표시
col1, col2 = st.columns(2)
with col1:
    st.metric("계량기 종류", current_meter["type"])
with col2:
    prev_label = f"전월({selected_month-1}월) 지침" if selected_month > 1 else "전월 지침"
    st.metric(prev_label, current_item["prev_val"] if current_item["prev_val"] else "기록 없음")

# --- 입력 폼 ---
with st.form("meter_reading_form", clear_on_submit=False):
    input_val = st.text_input(
        f"당월 ({selected_month}월) 지침 입력",
        value=current_item["val"],
        placeholder="지침값을 입력하세요 (예: 1254.3)"
    )
    
    submitted = st.form_submit_button("💾 저장 후 다음 계량기로 이동", use_container_width=True)
    
    if submitted:
        if not input_val.strip():
            st.warning("지침 값을 입력해주세요.")
        else:
            try:
                # 구글 시트에 업데이트
                ws.update_cell(current_meter["row"], col_idx, input_val.strip())
                st.success(f"✅ [{current_meter['name']}] 저장 완료!")
                
                # 다음 계량기로 인덱스 이동 (자동 넘김)
                current_idx = meter_name_list.index(selected_meter_name)
                if current_idx + 1 < len(meter_name_list):
                    st.session_state.selected_meter_idx = current_idx + 1
                else:
                    st.session_state.selected_meter_idx = 0
                
                st.rerun()
            except Exception as e:
                st.error(f"시트 저장 실패: {e}")

# 전체 현황표 접기/펼치기
with st.expander(f"📋 {selected_month}월 전체 입력 목록 보기"):
    summary_data = []
    for item in meter_status:
        summary_data.append({
            "계량기명": item["meter"]["name"],
            "구분": item["meter"]["type"],
            "지침": item["val"],
            "상태": "✅ 완료" if item["is_done"] else "⬜ 미검침"
        })
    df_summary = pd.DataFrame(summary_data)
    st.dataframe(df_summary, use_container_width=True, hide_index=True)
