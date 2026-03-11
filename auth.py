import hashlib
import streamlit as st

from config import ROLES, BRANDING
from users import get_user


def hash_password(plain):
    """비밀번호를 SHA-256 + salt로 해싱한다."""
    salt = st.secrets["auth"]["salt"]
    return hashlib.sha256((salt + plain).encode()).hexdigest()


def verify_password(plain, stored_hash):
    return hash_password(plain) == stored_hash


def show_login_page():
    """로그인 페이지를 렌더링한다. 인증 성공 시 True를 반환한다."""
    st.markdown("""<style>
    #MainMenu {visibility: hidden;}
    header {visibility: hidden;}
    footer {visibility: hidden;}
    </style>""", unsafe_allow_html=True)

    _, center, _ = st.columns([1, 2, 1])
    with center:
        st.markdown("")
        st.markdown("")
        st.title("유앤아이의원")
        st.caption("장비 현황 관리 시스템")
        st.markdown("")

        with st.form("login_form"):
            username = st.text_input("사용자 ID")
            password = st.text_input("비밀번호", type="password")
            submitted = st.form_submit_button("로그인", type="primary", use_container_width=True)

            if submitted:
                if not username or not password:
                    st.error("ID와 비밀번호를 입력해주세요.")
                else:
                    user = get_user(username)
                    if user is None:
                        st.error("사용자를 찾을 수 없습니다.")
                    elif not verify_password(password, user["password_hash"]):
                        st.error("비밀번호가 올바르지 않습니다.")
                    else:
                        st.session_state["authenticated"] = True
                        st.session_state["username"] = user["username"]
                        st.session_state["role"] = user["role"]
                        st.rerun()

        st.markdown("")
        st.caption(BRANDING)

    return False


def require_auth():
    """인증 여부를 확인한다. 미인증이면 로그인 페이지를 표시한다."""
    if st.session_state.get("authenticated", False):
        return True
    show_login_page()
    return False


def get_current_role():
    return st.session_state.get("role", "viewer")


def get_permissions():
    return ROLES.get(get_current_role(), ROLES["viewer"])


def show_user_info_sidebar():
    """사이드바에 사용자 정보와 로그아웃 버튼을 표시한다."""
    username = st.session_state.get("username", "")
    role = get_current_role()
    role_label = ROLES.get(role, {}).get("label", role)

    st.markdown(f"**{username}** · `{role_label}`")

    if st.button("로그아웃", use_container_width=True):
        for key in ["authenticated", "username", "role", "gspread_client",
                     "_users_cache", "pending_photo_changes"]:
            st.session_state.pop(key, None)
        st.rerun()
