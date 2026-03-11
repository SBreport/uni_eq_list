import streamlit as st
from sheets import get_gspread_client
from config import SUMMARY_SHEET_ID

USERS_TAB = "_users"


def _get_users_worksheet():
    """종합시트의 _users 탭을 가져온다. 없으면 생성한다."""
    gc = get_gspread_client()
    if gc is None:
        return None

    sh = gc.open_by_key(SUMMARY_SHEET_ID)
    try:
        return sh.worksheet(USERS_TAB)
    except Exception:
        # 탭이 없으면 생성
        ws = sh.add_worksheet(title=USERS_TAB, rows=100, cols=3)
        ws.update("A1:C1", [["username", "password_hash", "role"]])
        return ws


def load_users():
    """사용자 목록을 로드한다. 캐시는 session_state에 저장."""
    if "_users_cache" in st.session_state:
        return st.session_state["_users_cache"]

    users = []

    ws = _get_users_worksheet()
    if ws is not None:
        try:
            rows = ws.get_all_values()
            for row in rows[1:]:  # 헤더 스킵
                if len(row) >= 3 and row[0].strip():
                    users.append({
                        "username": row[0].strip(),
                        "password_hash": row[1].strip(),
                        "role": row[2].strip(),
                    })
        except Exception:
            pass

    # 시트에 사용자가 없으면 bootstrap admin 사용
    if not users:
        try:
            auth_secrets = st.secrets["auth"]
            users.append({
                "username": auth_secrets["bootstrap_admin_id"],
                "password_hash": auth_secrets["bootstrap_admin_pw_hash"],
                "role": auth_secrets.get("bootstrap_admin_role", "admin"),
            })
        except Exception:
            pass

    st.session_state["_users_cache"] = users
    return users


def get_user(username):
    """사용자명으로 사용자 정보를 반환한다."""
    for user in load_users():
        if user["username"] == username:
            return user
    return None


def add_user(username, password_hash, role):
    """사용자를 추가한다."""
    if get_user(username):
        return False, f"'{username}' 은(는) 이미 존재합니다."

    ws = _get_users_worksheet()
    if ws is None:
        return False, "시트 연결 실패"

    try:
        ws.append_row([username, password_hash, role])
        invalidate_users_cache()
        return True, f"'{username}' 사용자가 추가되었습니다."
    except Exception as e:
        return False, f"추가 실패: {e}"


def remove_user(username):
    """사용자를 삭제한다."""
    ws = _get_users_worksheet()
    if ws is None:
        return False, "시트 연결 실패"

    # 마지막 관리자 삭제 방지
    users = load_users()
    admins = [u for u in users if u["role"] == "admin"]
    target = get_user(username)
    if target and target["role"] == "admin" and len(admins) <= 1:
        return False, "마지막 관리자는 삭제할 수 없습니다."

    try:
        rows = ws.get_all_values()
        for i, row in enumerate(rows):
            if i == 0:
                continue
            if len(row) > 0 and row[0].strip() == username:
                ws.delete_rows(i + 1)
                invalidate_users_cache()
                return True, f"'{username}' 사용자가 삭제되었습니다."
        return False, f"'{username}' 을(를) 찾을 수 없습니다."
    except Exception as e:
        return False, f"삭제 실패: {e}"


def update_user_role(username, new_role):
    """사용자 역할을 변경한다."""
    ws = _get_users_worksheet()
    if ws is None:
        return False, "시트 연결 실패"

    try:
        rows = ws.get_all_values()
        for i, row in enumerate(rows):
            if i == 0:
                continue
            if len(row) > 0 and row[0].strip() == username:
                ws.update_cell(i + 1, 3, new_role)
                invalidate_users_cache()
                return True, f"'{username}' 역할이 변경되었습니다."
        return False, f"'{username}' 을(를) 찾을 수 없습니다."
    except Exception as e:
        return False, f"역할 변경 실패: {e}"


def update_user_password(username, new_password_hash):
    """사용자 비밀번호를 변경한다."""
    ws = _get_users_worksheet()
    if ws is None:
        return False, "시트 연결 실패"

    try:
        rows = ws.get_all_values()
        for i, row in enumerate(rows):
            if i == 0:
                continue
            if len(row) > 0 and row[0].strip() == username:
                ws.update_cell(i + 1, 2, new_password_hash)
                invalidate_users_cache()
                return True, f"'{username}' 비밀번호가 변경되었습니다."
        return False, f"'{username}' 을(를) 찾을 수 없습니다."
    except Exception as e:
        return False, f"비밀번호 변경 실패: {e}"


def invalidate_users_cache():
    st.session_state.pop("_users_cache", None)
