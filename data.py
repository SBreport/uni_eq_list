import streamlit as st
import pandas as pd
import re

from config import CSV_URL, PHOTO_YES, DEVICE_ALIASES


def clean_device_name(name):
    if pd.isna(name):
        return ""
    name = str(name).strip()
    cleaned = re.sub(r"^\d+\.?\s+", "", name)
    return cleaned.strip()


def get_device_group(clean_name):
    lower = clean_name.lower()
    for group, patterns in DEVICE_ALIASES.items():
        for pattern in patterns:
            if pattern.lower() in lower:
                return group
    return clean_name


@st.cache_data(ttl=300)
def load_data():
    try:
        df = pd.read_csv(CSV_URL, header=1)

        expected_cols = ["순번", "지점명", "카테고리", "기기명", "수량", "비고"]
        available = [c for c in expected_cols if c in df.columns]
        if len(available) < 4:
            cols = df.columns.tolist()
            use_count = min(len(cols), 7)
            df = df.iloc[:, :use_count]
            if use_count == 7:
                df.columns = expected_cols + ["사진"]
            else:
                df.columns = expected_cols[:use_count]
        else:
            if "사진" in df.columns:
                df = df[available + ["사진"]]
            else:
                df = df[available]

        df = df.dropna(subset=["지점명"])

        for col in ["지점명", "카테고리", "기기명"]:
            if col in df.columns:
                df[col] = df[col].astype(str).str.strip()

        if "비고" in df.columns:
            df["비고"] = df["비고"].fillna("").astype(str).str.strip()
            df["비고"] = df["비고"].replace("nan", "")
        else:
            df["비고"] = ""

        if "사진" not in df.columns:
            df["사진"] = ""
        else:
            df["사진"] = df["사진"].fillna("").astype(str).str.strip()
            df["사진"] = df["사진"].replace("nan", "")

        if "수량" in df.columns:
            df["수량"] = pd.to_numeric(df["수량"], errors="coerce").fillna(0).astype(int)

        if "순번" in df.columns:
            df["순번"] = pd.to_numeric(df["순번"], errors="coerce").fillna(0).astype(int)

        df["기기명_원본"] = df["기기명"]
        df["기기명"] = df["기기명_원본"].apply(clean_device_name)
        df["장비그룹"] = df["기기명"].apply(get_device_group)

        return df

    except Exception as e:
        st.error(f"데이터를 불러오는 중 오류가 발생했습니다: {e}")
        st.info("인터넷 연결을 확인하고 '새로고침' 버튼을 눌러주세요.")
        return pd.DataFrame(
            columns=["순번", "지점명", "카테고리", "기기명", "기기명_원본", "장비그룹", "수량", "비고", "사진"]
        )


def apply_photo_status(df):
    df = df.copy()
    df["사진유무"] = df["사진"].apply(
        lambda x: "있음" if str(x).strip() in PHOTO_YES else "없음"
    )
    return df


def apply_filters(df, branches, categories, search, photo_filter):
    filtered = df.copy()

    if branches:
        filtered = filtered[filtered["지점명"].isin(branches)]

    if categories:
        filtered = filtered[filtered["카테고리"].isin(categories)]

    if search:
        mask = (
            filtered["기기명"].str.contains(search, case=False, na=False)
            | filtered["장비그룹"].str.contains(search, case=False, na=False)
            | filtered["비고"].str.contains(search, case=False, na=False)
        )
        filtered = filtered[mask]

    if photo_filter == "사진 없음만":
        filtered = filtered[filtered["사진유무"] == "없음"]
    elif photo_filter == "사진 있음만":
        filtered = filtered[filtered["사진유무"] == "있음"]

    return filtered
