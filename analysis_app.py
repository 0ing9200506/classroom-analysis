import streamlit as st
import pandas as pd
import re

st.title("분반 가능 여부 분석")

uploaded_files = st.file_uploader(
    "엑셀 파일 업로드",
    type=["xlsx", "xls", "csv"],
    accept_multiple_files=True
)

def extract_year_from_filename(filename):
    match = re.search(r"(20\d{2})", filename)
    return int(match.group(1)) if match else None

if uploaded_files:

    dfs = []

    for file in uploaded_files:

        if file.name.endswith(".csv"):
            temp_df = pd.read_csv(file)
        elif file.name.lower().endswith(".xls"):
            temp_df = pd.read_excel(file, engine="xlrd")
        else:
            temp_df = pd.read_excel(file, engine="openpyxl")

        temp_df.columns = [c.replace("\r", "").strip() for c in temp_df.columns]
        temp_df["연도"] = extract_year_from_filename(file.name)
        dfs.append(temp_df)

    df = pd.concat(dfs, ignore_index=True)

    df = df.rename(columns={
        "교과목명": "course",
        "학수코드": "code",
        "수강인원": "enroll",
        "연도": "year",
        "개설전공": "major",
        "이수구분": "category"
    })

    df["enroll"] = pd.to_numeric(df["enroll"], errors="coerce")
    df["year"] = pd.to_numeric(df["year"], errors="coerce")

    latest_year = df["year"].max()
    df_2y = df[df["year"] >= latest_year - 1]

    result = (
        df_2y.groupby(["code", "course", "major", "category"], sort=False)["enroll"]
        .mean()
        .reset_index()
    )

    result["분반가능여부"] = result["enroll"].apply(
        lambda x: "✅ 가능" if x >= 60 else "❌ 불가"
    )

    result = result.rename(columns={
        "code": "학수코드",
        "course": "교과목명",
        "major": "개설전공",
        "category": "이수구분",
        "enroll": "평균수강인원"
    })

    result = result[["학수코드", "교과목명", "개설전공", "이수구분", "평균수강인원", "분반가능여부"]]

    # ✅ 검색창
    search = st.text_input("🔍 학수코드 또는 교과목명 검색")

    if search:
        mask = (
            result["학수코드"].str.contains(search, case=False, na=False) |
            result["교과목명"].str.contains(search, case=False, na=False)
        )
        filtered = result[mask]
    else:
        filtered = result

    def highlight(row):
        return [
            "background-color: yellow" if row["평균수강인원"] >= 60 else ""
            for _ in row
        ]

    st.subheader(f"분반 분석 결과 (최근 2년 평균) — {len(filtered)}개 표시")

    st.dataframe(
        filtered.style.apply(highlight, axis=1),
        use_container_width=True
    )

else:
    st.info("엑셀 파일을 업로드하세요")
