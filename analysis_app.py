import streamlit as st
import pandas as pd
import re

# =========================
# 페이지 설정
# =========================
st.set_page_config(
    page_title="분반 가능 여부 분석",
    layout="wide"
)

st.title("분반 가능 여부 분석 시스템")

# =========================
# 파일 업로드
# =========================
uploaded_files = st.file_uploader(
    "엑셀 파일 업로드 (여러 개 가능)",
    type=["xlsx", "xls", "csv"],
    accept_multiple_files=True
)

# =========================
# 연도 추출 함수
# =========================
def extract_year(filename):
    match = re.search(r"(20\d{2})", filename)
    return int(match.group(1)) if match else None


if uploaded_files:

    dfs = []

    # =========================
    # 파일 읽기
    # =========================
    for file in uploaded_files:

        if file.name.endswith(".csv"):
            temp_df = pd.read_csv(file)

        elif file.name.lower().endswith(".xls"):
            temp_df = pd.read_excel(file, engine="xlrd")

        else:
            temp_df = pd.read_excel(file, engine="openpyxl")

        # 컬럼 정리
        temp_df.columns = [c.strip() for c in temp_df.columns]

        # 연도 추가
        temp_df["연도"] = extract_year(file.name)

        dfs.append(temp_df)

    df = pd.concat(dfs, ignore_index=True)

    # =========================
    # 컬럼 표준화
    # =========================
    df = df.rename(columns={
        "교과목명": "course",
        "학수코드": "code",
        "수강인원": "enroll",
        "개설전공": "major",
        "이수구분": "category"
    })

    df["enroll"] = pd.to_numeric(df["enroll"], errors="coerce")
    df["연도"] = pd.to_numeric(df["연도"], errors="coerce")

    # =========================
    # 최근 2년 필터
    # =========================
    latest_year = df["연도"].max()
    df_2y = df[df["연도"] >= latest_year - 1]

    # =========================================================
    # 🔥 핵심 1: 같은 과목 + 연도 기준 먼저 합산 (분반 합치기)
    # =========================================================
    yearly_sum = (
        df_2y.groupby(
            ["code", "course", "major", "category", "연도"],
            as_index=False
        )["enroll"]
        .sum()
    )

    # =========================================================
    # 🔥 핵심 2: 연도별 값 기준 평균 계산
    # =========================================================
    result = (
        yearly_sum.groupby(
            ["code", "course", "major", "category"],
            as_index=False
        )["enroll"]
        .mean()
    )

    # =========================
    # 분반 가능 여부
    # =========================
    result["분반가능여부"] = result["enroll"].apply(
        lambda x: "✅ 가능" if x >= 60 else "❌ 불가"
    )

    # =========================
    # 컬럼 정리
    # =========================
    result = result.rename(columns={
        "code": "학수코드",
        "course": "교과목명",
        "major": "개설전공",
        "category": "이수구분",
        "enroll": "평균수강인원"
    })

    result = result[
        ["학수코드", "교과목명", "개설전공", "이수구분", "평균수강인원", "분반가능여부"]
    ]

    # =========================
    # 검색 기능
    # =========================
    search = st.text_input("🔍 학수코드 / 교과목명 검색")

    if search:

        mask = (
            result["학수코드"].astype(str).str.contains(search, case=False, na=False) |
            result["교과목명"].astype(str).str.contains(search, case=False, na=False)
        )

        filtered = result[mask]

    else:
        filtered = result

    # =========================
    # 색상 표시
    # =========================
    def highlight(row):

        return [
            "background-color: yellow" if row["평균수강인원"] >= 60 else ""
            for _ in row
        ]

    # =========================
    # 출력
    # =========================
    st.subheader(f"📌 결과 ({len(filtered)}개)")

    st.dataframe(
        filtered.style.apply(highlight, axis=1),
        use_container_width=True
    )

else:

    st.info("엑셀 파일을 업로드하세요")
