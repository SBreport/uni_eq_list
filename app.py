import streamlit as st
import streamlit.components.v1 as components
from datetime import datetime

from config import BRANDING
from auth import require_auth, get_permissions, show_user_info_sidebar
from data import load_data, apply_photo_status, apply_filters
from sheets import regenerate_braw
from ui_tabs import (
    render_tab_equipment_list,
    render_tab_search,
    render_tab_compare,
    render_tab_dashboard,
    render_admin_panel,
    render_tab_guide,
)

# ============================================================
# 페이지 설정
# ============================================================
st.set_page_config(
    page_title="유앤아이의원 장비 현황",
    page_icon="🏥",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ============================================================
# 글로벌 CSS  +  다크 모드 CSS (항상 포함, html.dark-theme 스코프)
# ============================================================
st.markdown("""<style>
/* ── 공통 레이아웃 ── */
[data-testid="stToolbar"] > div > div:last-child { display: none !important; }
.block-container { padding-top: 1rem !important; padding-bottom: 0 !important; }
.stTabs [data-baseweb="tab-list"] { gap: 2px; margin-bottom: 0; }
.stTabs [data-baseweb="tab-panel"] { padding-top: 0.5rem; }
.stTabs button[data-baseweb="tab"] { padding: 6px 16px; font-size: 14px; }

/* ── 다크 모드 (html.dark-theme 활성 시) ── */
html.dark-theme .stApp,
html.dark-theme [data-testid="stAppViewContainer"] {
    background-color: #0E1117 !important; color: #FAFAFA !important;
}
html.dark-theme section[data-testid="stSidebar"] > div {
    background-color: #262730 !important;
}
html.dark-theme header[data-testid="stHeader"] {
    background: #0E1117 !important;
}
/* 텍스트 */
html.dark-theme .stApp p, html.dark-theme .stApp span,
html.dark-theme .stApp label, html.dark-theme .stApp div,
html.dark-theme [data-testid="stMarkdownContainer"] *,
html.dark-theme [data-testid="stWidgetLabel"] *,
html.dark-theme .stRadio label span,
html.dark-theme .stSelectbox label,
html.dark-theme .stMultiSelect label,
html.dark-theme h1, html.dark-theme h2, html.dark-theme h3,
html.dark-theme h4, html.dark-theme h5, html.dark-theme h6 {
    color: #FAFAFA !important;
}
/* 입력 필드 */
html.dark-theme .stTextInput input,
html.dark-theme .stTextArea textarea,
html.dark-theme [data-baseweb="select"] > div,
html.dark-theme [data-baseweb="input"] > div {
    background-color: #1A1A2E !important;
    color: #FAFAFA !important;
    border-color: #3A3A5A !important;
}
html.dark-theme [data-baseweb="tag"] { background-color: #3A3A5A !important; }
html.dark-theme [data-baseweb="popover"] > div,
html.dark-theme [data-baseweb="menu"] { background-color: #1A1A2E !important; }
html.dark-theme [data-baseweb="menu"] li { color: #FAFAFA !important; }
html.dark-theme [data-baseweb="menu"] li:hover { background-color: #2A2A4E !important; }
/* 탭 */
html.dark-theme .stTabs [data-baseweb="tab"] { color: #A0A0A0 !important; }
html.dark-theme .stTabs [aria-selected="true"] { color: #FAFAFA !important; }
/* 메트릭 */
html.dark-theme [data-testid="stMetric"] {
    background-color: #1A1A2E; border-radius: 8px; padding: 8px 12px;
}
/* 버튼 — 하위 자식 선택자 (> 제거: Tooltip 래퍼 호환) */
html.dark-theme .stButton button:not([kind="primary"]) {
    background-color: #262730 !important;
    color: #FAFAFA !important;
    border-color: #3A3A5A !important;
}
/* 툴팁 */
html.dark-theme [data-testid="stTooltipContent"],
html.dark-theme [data-baseweb="tooltip"] [role="tooltip"],
html.dark-theme [data-testid="stTooltipContent"] p,
html.dark-theme [data-testid="stTooltipContent"] div {
    background-color: #1A1A2E !important;
    color: #E0E0E0 !important;
}
/* 구분선/캡션/기타 */
html.dark-theme hr { border-color: #3A3A5A !important; }
html.dark-theme [data-testid="stCaptionContainer"] * { color: #A0A0A0 !important; }
html.dark-theme [data-testid="stExpander"] { border-color: #3A3A5A !important; }
html.dark-theme [data-testid="stProgress"] > div > div { background-color: #3A3A5A !important; }
</style>""", unsafe_allow_html=True)

# ============================================================
# 다크 모드 JS 토글 (페이지 리로드 없이 CSS 클래스만 전환)
# ============================================================
components.html("""
<script>
(function() {
  var pd = window.parent.document;
  var html = pd.documentElement;
  var KEY = 'uandi_dark_mode';

  /* 1. localStorage → 즉시 클래스 적용 */
  var isDark = localStorage.getItem(KEY) === 'true';
  if (isDark) html.classList.add('dark-theme');
  else html.classList.remove('dark-theme');

  /* 2. AG-Grid iframe 동기화 헬퍼 */
  function syncIframes(dark) {
    pd.querySelectorAll('iframe').forEach(function(f) {
      try {
        var d = f.contentDocument || f.contentWindow.document;
        if (dark) d.documentElement.classList.add('dark-theme');
        else d.documentElement.classList.remove('dark-theme');
      } catch(e) {}
    });
  }
  syncIframes(isDark);

  /* 3. 플로팅 토글 버튼 */
  var old = pd.getElementById('dark-toggle');
  if (old) old.remove();

  var btn = pd.createElement('button');
  btn.id = 'dark-toggle';
  function applyBtnStyle() {
    var d = html.classList.contains('dark-theme');
    btn.textContent = d ? '\\u2600\\uFE0F' : '\\uD83C\\uDF19';
    btn.style.background = d ? '#262730' : '#F0F2F6';
    btn.style.borderColor = d ? '#3A3A5A' : '#D0D0D0';
    btn.style.color = d ? '#FFF' : '#000';
  }
  btn.style.cssText = 'position:fixed;right:0;top:50%;transform:translateY(-50%);z-index:999999;'
    + 'font-size:18px;border:1px solid;border-radius:8px 0 0 8px;width:32px;height:48px;'
    + 'display:flex;align-items:center;justify-content:center;cursor:pointer;'
    + 'box-shadow:-2px 0 6px rgba(0,0,0,.2);transition:background .2s,color .2s;';
  applyBtnStyle();

  btn.addEventListener('click', function() {
    html.classList.toggle('dark-theme');
    var nowDark = html.classList.contains('dark-theme');
    localStorage.setItem(KEY, nowDark);
    applyBtnStyle();
    syncIframes(nowDark);
  });
  pd.body.appendChild(btn);

  /* 4. 새로 추가되는 iframe 자동 동기화 (AG-Grid 지연 렌더링 대응) */
  new MutationObserver(function() {
    syncIframes(html.classList.contains('dark-theme'));
  }).observe(pd.body, { childList: true, subtree: true });
})();
</script>
""", height=0)

# ============================================================
# 인증 게이트 (현재 비활성화 — 추후 활성화 시 아래 주석 해제)
# ============================================================
# if not require_auth():
#     st.stop()
# permissions = get_permissions()

from config import ROLES
permissions = ROLES["admin"]  # 로그인 없이 관리자 권한으로 동작

# ============================================================
# 데이터 로딩
# ============================================================
df = load_data()

# 저장 직후: Google CSV 캐시 갱신 전까지 변경 내역을 직접 반영
if "pending_photo_changes" in st.session_state:
    df = df.copy()
    for branch_name, device_name, value in st.session_state["pending_photo_changes"]:
        mask = (df["지점명"] == branch_name) & (df["기기명_원본"] == device_name)
        df.loc[mask, "사진"] = value

df = apply_photo_status(df)

# 지점 목록
all_branches = sorted(df["지점명"].unique()) if len(df) > 0 else []

# ============================================================
# 사이드바
# ============================================================
with st.sidebar:
    st.markdown("""<style>
    section[data-testid="stSidebar"] .block-container { padding-top: 1rem; }
    section[data-testid="stSidebar"] [data-testid="stVerticalBlock"] > div { margin-bottom: -0.5rem; }
    </style>""", unsafe_allow_html=True)

    st.markdown("### 유앤아이의원")
    st.caption("보유장비 현황")
    st.divider()

    # 지점 선택
    selected_branches = st.multiselect(
        "지점 선택",
        options=all_branches,
        default=[],
        placeholder="지점명 입력하여 검색",
        help="지점명을 직접 입력하면 빠르게 찾을 수 있습니다",
    )

    st.divider()

    st.header("필터 설정")

    all_categories = sorted(df["카테고리"].unique()) if len(df) > 0 else []
    selected_categories = st.multiselect(
        "카테고리 선택",
        options=all_categories,
        default=[],
        placeholder="전체 카테고리",
    )

    search_query = st.text_input("장비 검색", placeholder="장비명 입력")

    photo_filter = st.radio(
        "사진 필터",
        options=["전체", "사진 없음만", "사진 있음만"],
        horizontal=True,
    )

    st.divider()

    if st.button("새로고침", use_container_width=True,
                  help="화면 데이터를 최신 상태로 갱신합니다"):
        load_data.clear()
        st.session_state.pop("pending_photo_changes", None)
        st.rerun()

    if permissions["can_sync"]:
        if st.button("전체 동기화", use_container_width=True,
                      help="모든 지점의 원본 데이터를 다시 불러와 통합합니다"):
            with st.spinner("전체 데이터 동기화 중..."):
                regen_ok, regen_msg = regenerate_braw()
            if regen_ok:
                st.success(f"✅ {regen_msg}")
                load_data.clear()
                st.session_state.pop("pending_photo_changes", None)
                st.rerun()
            else:
                st.error(f"❌ {regen_msg}")

    st.caption(f"마지막 로딩\n{datetime.now().strftime('%Y-%m-%d %H:%M')}")

    # 브랜딩
    st.divider()
    # show_user_info_sidebar()  # 로그인 비활성화 중
    st.caption(BRANDING)

# ============================================================
# 필터 적용
# ============================================================
filtered_df = apply_filters(df, selected_branches, selected_categories, search_query, photo_filter)

# ============================================================
# 탭
# ============================================================
tab_names = ["장비 목록", "장비 검색", "지점 비교", "대시보드", "가이드"]
if permissions["can_manage_users"]:
    tab_names.append("사용자 관리")

tabs = st.tabs(tab_names)

with tabs[0]:
    render_tab_equipment_list(filtered_df, df, selected_branches, permissions)

with tabs[1]:
    render_tab_search(filtered_df, df)

with tabs[2]:
    render_tab_compare(df, selected_branches)

with tabs[3]:
    render_tab_dashboard(filtered_df)

with tabs[4]:
    render_tab_guide()

if permissions["can_manage_users"]:
    with tabs[5]:
        render_admin_panel()
