# /mnt/data/streamlit_app.py
import streamlit as st
import pandas as pd
import plotly.express as px

st.set_page_config(page_title="대중교통 접근수단 (2018-2024) 시각화", layout="wide")
st.title("대중교통 접근수단 (2018 - 2024) — 시도별/유형별 시각화")

CSV_PATH = "/mnt/data/대중교통현황조사(2011~ )_시도별 대중교통 접근수단 (2018 ~ 2024).csv"

@st.cache_data
def load_data(path=CSV_PATH):
    encodings = ["utf-8", "utf-8-sig", "cp949", "euc-kr", "latin1"]
    for enc in encodings:
        try:
            df = pd.read_csv(path, encoding=enc)
            df.attrs["encoding_used"] = enc
            return df
        except Exception:
            pass
    # fallback: use python engine with loose quoting
    try:
        df = pd.read_csv(path, engine="python", encoding="utf-8", quoting=3)
        df.attrs["encoding_used"] = "utf-8 (python engine, quoting=3)"
        return df
    except Exception as e:
        raise e

# load
try:
    df = load_data()
except Exception as e:
    st.error(f"CSV 파일을 불러오지 못했습니다: {e}")
    st.stop()

st.sidebar.header("데이터 정보 / 필터")
st.sidebar.write(f"읽은 인코딩: **{df.attrs.get('encoding_used', 'unknown')}**")
st.write("원본 데이터 미리보기 (상위 10행)")
st.dataframe(df.head(10))

# 기본 컬럼명 (파일에서 발견된 컬럼에 맞춘 기본값)
year_col_guess = "년(Annual)" if "년(Annual)" in df.columns else df.columns[0]
region_col_guess = "구분" if "구분" in df.columns else df.columns[1]

# UI: 컬럼 선택(자동으로 추정)
year_col = st.sidebar.selectbox("연도(Year) 컬럼 선택", options=list(df.columns), index=list(df.columns).index(year_col_guess))
region_col = st.sidebar.selectbox("지역(시도) 컬럼 선택", options=list(df.columns), index=list(df.columns).index(region_col_guess))

# 교통수단 컬럼(연도/지역 외 모두를 수단으로 간주)
transport_cols = [c for c in df.columns if c not in {year_col, region_col}]
if not transport_cols:
    st.error("교통수단으로 사용할 컬럼을 자동으로 찾지 못했습니다. CSV 구조를 확인해 주세요.")
    st.stop()

st.sidebar.write("교통수단(컬럼)")
selected_transports = st.sidebar.multiselect("표시할 교통수단 선택", options=transport_cols, default=transport_cols[:3])

# 연도 필터 (값이 문자열이면 그대로)
unique_years = df[year_col].astype(str).unique().tolist()
selected_years = st.sidebar.multiselect("표시할 연도 선택", options=unique_years, default=unique_years)

# 시도 필터
unique_regions = df[region_col].astype(str).unique().tolist()
selected_regions = st.sidebar.multiselect("표시할 시도 선택", options=unique_regions, default=unique_regions[:6])

# 데이터 정리: 연도는 문자열로 처리 후 pivot/melt
df_work = df.copy()
df_work[year_col] = df_work[year_col].astype(str)

# 필터 적용
df_work = df_work[df_work[year_col].isin(selected_years)]
df_work = df_work[df_work[region_col].isin(selected_regions)]

# melt: long 형식으로 변환 (Region, Year, Transport, Value)
df_long = df_work.melt(id_vars=[region_col, year_col], value_vars=transport_cols,
                       var_name="Transport", value_name="Value")

# 숫자 변환 시도 (콤마 제거 등)
def to_num(x):
    if pd.isna(x): return None
    if isinstance(x, (int, float)): return x
    s = str(x).replace(",", "").strip()
    try:
        return float(s)
    except:
        return None

df_long["Value"] = df_long["Value"].apply(to_num)

st.header("시도별 추이 (라인 차트)")
chart_mode = st.radio("차트 종류", options=["라인 차트 (연도별)","막대 차트 (연도별 합계)", "스택형 막대(연도별)"], index=0)

if chart_mode == "라인 차트 (연도별)":
    if df_long["Value"].notna().sum() == 0:
        st.warning("수치 데이터로 변환 가능한 값이 없습니다. 원시값을 확인해 주세요.")
    else:
        fig = px.line(
            df_long[df_long["Transport"].isin(selected_transports)],
            x=year_col, y="Value", color=region_col, line_dash="Transport",
            markers=True, labels={"Value":"값", year_col:"연도"}
        )
        st.plotly_chart(fig, use_container_width=True)

elif chart_mode == "막대 차트 (연도별 합계)":
    agg = df_long[df_long["Transport"].isin(selected_transports)].groupby([year_col]).sum(numeric_only=True).reset_index()
    # if multiple transport columns were melted, groupby already sums Value
    fig = px.bar(agg, x=year_col, y="Value", labels={"Value":"합계", year_col:"연도"})
    st.plotly_chart(fig, use_container_width=True)

else:  # 스택형 막대
    stacked = df_long[df_long["Transport"].isin(selected_transports)].groupby([year_col, "Transport"])["Value"].sum().reset_index()
    fig = px.bar(stacked, x=year_col, y="Value", color="Transport", labels={year_col:"연도", "Value":"값"})
    st.plotly_chart(fig, use_container_width=True)

st.header("원본 / 가공 데이터 확인")
st.write("긴 형식 (region / year / transport / value)")
st.dataframe(df_long.reset_index(drop=True))

st.caption("참고: 이 템플릿은 CSV 구조(컬럼명)에 맞춰 자동 추정합니다. 필요하면 연도 추출 규칙·숫자 변환 규칙·레이블을 조정하세요.")
