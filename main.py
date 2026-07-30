import streamlit as st
import pandas as pd
import requests
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

st.set_page_config(page_title="박스오피스 대시보드", layout="wide")
st.title("🎬 일별 박스오피스 대시보드")

# 비밀 금고에서 인증키 꺼내기
KOBIS_KEY = st.secrets["KOBIS_KEY"]

# 한국 시간 기준 어제 날짜 구하기 (최대 선택 가능 날짜)
today_seoul = datetime.now(ZoneInfo("Asia/Seoul")).date()
yesterday_seoul = today_seoul - timedelta(days=1)

# 1. 달력에서 날짜 선택 (최대 어제까지 선택 가능)
selected_date = st.date_input(
    "조회할 날짜를 선택하세요",
    value=yesterday_seoul,
    max_value=yesterday_seoul
)

target_dt = selected_date.strftime("%Y%m%d")
st.caption(f"조회 기준일: {selected_date.strftime('%Y-%m-%d')}")

url = "https://www.kobis.or.kr/kobisopenapi/webservice/rest/boxoffice/searchDailyBoxOfficeList.json"
res = requests.get(url, params={"key": KOBIS_KEY, "targetDt": target_dt}, timeout=10)

if res.status_code != 200:
    st.error(f"요청이 실패했습니다 (상태코드: {res.status_code})")
    st.stop()

data = res.json()

# KOBIS 인증키 에러 처리
if "faultInfo" in data:
    st.error("인증키가 올바르지 않습니다. 금고(Secrets)의 KOBIS_KEY를 확인해 주세요.")
    st.stop()

box_list = data.get("boxOfficeResult", {}).get("dailyBoxOfficeList", [])

# 2. 고른 날짜에 영화 목록이 비어있는 경우
if not box_list:
    st.warning("그날은 아직 집계 전입니다.")
    st.stop()

df = pd.DataFrame(box_list)

# 글자로 온 숫자들을 숫자 타입으로 변환 (rankInten 추가)
for col in ["rank", "rankInten", "audiCnt", "audiAcc", "scrnCnt", "showCnt"]:
    df[col] = pd.to_numeric(df[col])

# 3. 누적 관객 100만 명 이상 영화명 옆에 트로피(🏆) 추가
df["movieNm"] = df.apply(
    lambda row: f"🏆 {row['movieNm']}" if row["audiAcc"] >= 1000000 else row["movieNm"],
    axis=1
)

# 4. 순위 증감(rankInten) 화살표 포맷팅 함수
def format_rank_change(val):
    if val > 0:
        return f"🔺 {val}"
    elif val < 0:
        return f"🔻 {abs(val)}"
    else:
        return "-"

df["rankInten_str"] = df["rankInten"].apply(format_rank_change)

# 상단 주요 지표 카드 세 장
top = df.sort_values("rank").iloc[0]
c1, c2, c3 = st.columns(3)
c1.metric("선택일 1위", top["movieNm"])
c2.metric("일일 관객수", f"{top['audiCnt']:,}명")
c3.metric("누적 관객수", f"{top['audiAcc']:,}명")

# 표 열 정리
table = df[["rank", "rankInten_str", "movieNm", "openDt", "audiCnt", "audiAcc", "scrnCnt"]].copy()
table.columns = ["순위", "순위변동", "영화명", "개봉일", "관객수", "누적관객", "스크린수"]
table = table.sort_values("순위").reset_index(drop=True)

st.subheader("📋 박스오피스 TOP 10")
st.dataframe(table, use_container_width=True)

st.subheader("📈 관객수 상위 5편")
top5 = table.sort_values("관객수", ascending=False).head(5)
st.bar_chart(top5.set_index("영화명")["관객수"])
