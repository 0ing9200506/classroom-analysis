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
    "엑셀/CSV 파일 업로드 (여러 개 가능)",
    type=["xlsx", "xls", "csv"],
    accept_multiple_files=True
)

# =========================
# 연도 추출
# =========================
def extract_year(filename):
    match = re.search(r"(20\d{2})", filename)
    return int(match.group(1)) if match else None

# =========================
# 컬럼 정리 함수
# =========================
def clean_columns(df):

    df.columns = (
        df.columns.astype(str)
        .str.replace("\r", "", regex=False)
        .str.replace("\n", "", regex=False)
        .str.replace(" ", "", regex=False)
        .str.strip()
    )

    # ! 같은 쓰레기 컬럼 제거
    df = df.loc[:, ~df.columns.str.contains("^!")]

    return df


if uploaded_files:

    dfs = []

    # =========================
    # 파일 읽기
    # =========================
    for file in uploaded_files:

        try:
            if file.name.endswith(".csv"):
                temp_df = pd.read_csv(file)

            elif file.name.lower().endswith(".xls"):
                temp_df = pd.read_excel(file, engine="xlrd")

            else:
                temp_df = pd.read_excel(file, engine="openpyxl")

        except Exception as e:
            st.error(f"{file.name} 읽기 실패: {e}")
            continue

        # 컬럼 정리
        temp_df = clean_columns(temp_df)

        # 연도 추가
        temp_df["연도"] = extract_year(file.name)

        dfs.append(temp_df)

    if not dfs:
        st.error("유효한 파일이 없습니다.")
        st.stop()

    df = pd.concat(dfs, ignore_index=True)

    # =========================
    # 컬럼 자동 매핑 (엑셀 깨짐 대응)
    # =========================
    def find_col(names):
        for n in names:
            if n in df.columns:
                return n
        return None

    col_course = find_col(["교과목명"])
    col_code = find_col(["학수코드"])
    col_enroll = find_col(["수강인원"])
    col_major = find_col(["개설전공"])
    col_category = find_col(["이수구분"])

    if col_enroll is None:
        st.error("'수강인원' 컬럼을 찾을 수 없습니다.")
        st.write("현재 컬럼:", df.columns.tolist())
        st.stop()

    # =========================
    # 표준 컬럼 변환
    # =========================
    rename_map = {}

    if col_course: rename_map[col_course] = "course"
    if col_code: rename_map[col_code] = "code"
    if col_enroll: rename_map[col_enroll] = "enroll"
    if col_major: rename_map[col_major] = "major"
    if col_category: rename_map[col_category] = "category"

    df = df.rename(columns=rename_map)

    # 없는 컬럼 대비
    for col in ["course", "code", "major", "category"]:
        if col not in df.columns:
            df[col] = ""

    # 숫자 변환
    df["enroll"] = pd.to_numeric(df["enroll"], errors="coerce")
    df["연도"] = pd.to_numeric(df["연도"], errors="coerce")

    df = df.dropna(subset=["enroll", "연도"])

    # =========================
    # 최근 2년 필터
    # =========================
    latest_year = df["연도"].max()
    df_2y = df[df["연도"] >= latest_year - 1]

    # =====================================================
    # 분반 합산 (과목 + 연도)
    # =====================================================
    yearly_sum = (
        df_2y.groupby(
            ["code", "course", "major", "category", "연도"],
            as_index=False
        )["enroll"]
        .sum()
    )

    # =====================================================
    # 연도 평균
    # =====================================================
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
    # 검색
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
    # 하이라이트
    # =========================
    def highlight(row):
        return [
            "background-color: yellow" if row["평균수강인원"] >= 60 else ""
            for _ in row
        ]

    # =========================
    # 출력
    # =========================
    st.subheader(f"결과 ({len(filtered)}개)")

    st.dataframe(
        filtered.style.apply(highlight, axis=1),
        use_container_width=True
    )

else:
    st.info("엑셀 파일을 업로드하세요")
