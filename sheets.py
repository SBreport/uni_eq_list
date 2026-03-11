import streamlit as st
import json
from pathlib import Path

from config import SUMMARY_SHEET_ID, BRANCH_NAME_TO_TAB

BRANCH_SOURCES_FILE = Path(__file__).parent / "branch_sources.json"


def get_gspread_client():
    """Google Sheets API 클라이언트를 반환한다 (캐싱)."""
    if "gspread_client" not in st.session_state:
        try:
            import gspread
            from google.oauth2.service_account import Credentials

            scopes = ["https://www.googleapis.com/auth/spreadsheets"]

            # Streamlit Cloud: st.secrets 사용
            # 로컬: .streamlit/secrets.toml 사용
            if "gcp_service_account" in st.secrets:
                creds = Credentials.from_service_account_info(
                    dict(st.secrets["gcp_service_account"]), scopes=scopes
                )
            else:
                # fallback: credentials.json 파일
                creds_file = Path(__file__).parent / "credentials.json"
                creds = Credentials.from_service_account_file(
                    str(creds_file), scopes=scopes
                )

            st.session_state.gspread_client = gspread.authorize(creds)
        except Exception as e:
            st.session_state.gspread_client = None
            st.session_state.gspread_error = str(e)
    return st.session_state.gspread_client


def load_branch_sources():
    if BRANCH_SOURCES_FILE.exists():
        with open(BRANCH_SOURCES_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data.get("branch_sources", {})
    return {}


def save_photo_batch_to_sheet(changes):
    gc = get_gspread_client()
    if gc is None:
        err_detail = st.session_state.get("gspread_error", "알 수 없는 오류")
        return 0, [f"Google Sheets 인증 실패: {err_detail}"]

    sources = load_branch_sources()
    if not sources:
        return 0, ["branch_sources.json 파일을 찾을 수 없습니다"]

    success = 0
    errors = []

    by_branch = {}
    for branch_name, device_name, value in changes:
        tab_name = BRANCH_NAME_TO_TAB.get(branch_name, branch_name)
        if tab_name not in by_branch:
            by_branch[tab_name] = []
        by_branch[tab_name].append((device_name, value, branch_name))

    for tab_name, items in by_branch.items():
        if tab_name not in sources:
            errors.append(f"'{tab_name}' 원본 시트 정보 없음")
            continue

        info = sources[tab_name]
        if "spreadsheet_id" not in info:
            errors.append(f"'{tab_name}' spreadsheet_id 없음")
            continue

        try:
            sh = gc.open_by_key(info["spreadsheet_id"])
            ws = sh.worksheet(info["source_tab"])
            d_column = ws.col_values(4)

            cells = []
            for device_name, value, orig_branch in items:
                found = False
                for row_idx, cell_val in enumerate(d_column):
                    if row_idx == 0:
                        continue
                    if str(cell_val).strip() == device_name:
                        sheet_row = row_idx + 1
                        cells.append({"range": f"G{sheet_row}", "values": [[value]]})
                        found = True
                        break
                if not found:
                    errors.append(f"{orig_branch}: '{device_name}' 원본 시트에서 찾을 수 없음")

            if cells:
                ws.batch_update(cells)
                success += len(cells)
        except Exception as e:
            errors.append(f"{tab_name}: {e}")

    return success, errors


def update_braw_photo(changes):
    gc = get_gspread_client()
    if gc is None:
        return False, "Google Sheets 인증 실패"

    try:
        sh = gc.open_by_key(SUMMARY_SHEET_ID)
        raw_ws = sh.worksheet("raw")
        all_data = raw_ws.get("B:D")

        cells = []
        not_found = []
        for branch_name, device_name, value in changes:
            found = False
            for row_idx, row in enumerate(all_data):
                if row_idx == 0:
                    continue
                b_val = str(row[0]).strip() if len(row) > 0 else ""
                d_val = str(row[2]).strip() if len(row) > 2 else ""
                if b_val == branch_name and d_val == device_name:
                    sheet_row = row_idx + 1
                    cells.append({"range": f"G{sheet_row}", "values": [[value]]})
                    found = True
                    break
            if not found:
                not_found.append(f"{branch_name}: {device_name}")

        if cells:
            raw_ws.batch_update(cells)

        msg = f"braw {len(cells)}건 동기화 완료"
        if not_found:
            msg += f" (미발견 {len(not_found)}건)"
        return True, msg
    except Exception as e:
        return False, f"braw 동기화 실패: {e}"


def regenerate_braw():
    gc = get_gspread_client()
    if gc is None:
        return False, "Google Sheets 인증 실패"

    try:
        if not BRANCH_SOURCES_FILE.exists():
            return False, "branch_sources.json 파일 없음"

        with open(BRANCH_SOURCES_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        tabs = data.get("tabs", [])
        skip = {"지점 목차", "파일생성목록", "raw"}
        branch_tabs = [t for t in tabs if t["title"] not in skip]

        if not branch_tabs:
            return False, "지점 탭이 없습니다"

        sh = gc.open_by_key(SUMMARY_SHEET_ID)
        ranges = [f"'{t['title']}'!A2:G" for t in branch_tabs]
        result = sh.values_batch_get(ranges)

        all_rows = []
        for vr in result.get("valueRanges", []):
            rows = vr.get("values", [])
            for row in rows:
                device = str(row[3]).strip() if len(row) > 3 else ""
                if not device:
                    continue
                branch = row[1] if len(row) > 1 else ""
                category = row[2] if len(row) > 2 else ""
                qty = row[4] if len(row) > 4 else ""
                note = row[5] if len(row) > 5 else ""
                photo = row[6] if len(row) > 6 else ""
                all_rows.append([branch, category, device, qty, note, photo])

        if not all_rows:
            return False, "데이터가 없습니다"

        raw_ws = sh.worksheet("raw")
        raw_ws.clear()

        headers = ["순번", "지점명", "카테고리", "기기명", "수량", "비고", "사진"]
        write_data = [headers]
        for i, row in enumerate(all_rows, 1):
            write_data.append([i] + row)

        raw_ws.update(range_name=f"A1:G{len(write_data)}", values=write_data)

        stats = [
            {"range": "I1:J1", "values": [["장비통계", "수량"]]},
            {"range": "L1:M1", "values": [["지점통계", "수량"]]},
            {"range": "I2", "values": [['=SORT(UNIQUE(FILTER(D2:D, D2:D<>"")))']]},
            {"range": "L2", "values": [['=SORT(UNIQUE(FILTER(B2:B, B2:B<>"")))']]},
            {"range": "J2", "values": [['=ARRAYFORMULA(IF(I2:I="", "", SUMIF(D:D, I2:I, E:E)))']]},
            {"range": "M2", "values": [['=ARRAYFORMULA(IF(L2:L="", "", SUMIF(B:B, L2:L, E:E)))']]},
        ]
        raw_ws.batch_update(stats, value_input_option="USER_ENTERED")

        return True, f"전체 동기화 완료 ({len(branch_tabs)}개 지점, {len(all_rows)}건)"
    except Exception as e:
        return False, f"동기화 실패: {e}"
