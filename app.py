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
# 글로벌 CSS  +  다크 모드 CSS (CSS 변수 시스템)
# ============================================================
st.markdown("""<style>
/* ================================================================
   CSS 변수 — 라이트 모드 (기본값)
   ================================================================ */
:root {
    --bg-primary: #FFFFFF;
    --bg-secondary: #F8FAFC;
    --bg-card: #FFFFFF;
    --border: #E2E8F0;
    --border-light: #F1F5F9;
    --text-primary: #1E293B;
    --text-secondary: #64748B;
    --text-muted: #94A3B8;
    --accent: #2563EB;
    --accent-light: #DBEAFE;
    --accent-hover: #1D4ED8;
    --success: #059669;
    --success-light: #D1FAE5;
    --warning: #D97706;
    --warning-light: #FEF3C7;
    --danger: #DC2626;
    --danger-light: #FEE2E2;
    --shadow-sm: 0 1px 2px rgba(0,0,0,0.05);
    --shadow-md: 0 4px 6px -1px rgba(0,0,0,0.07), 0 2px 4px -2px rgba(0,0,0,0.05);
    --radius-sm: 6px;
    --radius: 10px;
    --radius-lg: 14px;
}

/* ================================================================
   CSS 변수 — 다크 모드
   ================================================================ */
html.dark-theme {
    --bg-primary: #0F172A;
    --bg-secondary: #1E293B;
    --bg-card: #1E293B;
    --border: #334155;
    --border-light: #1E293B;
    --text-primary: #F1F5F9;
    --text-secondary: #94A3B8;
    --text-muted: #64748B;
    --accent: #3B82F6;
    --accent-light: #1E3A5F;
    --accent-hover: #60A5FA;
    --success: #34D399;
    --success-light: #064E3B;
    --warning: #FBBF24;
    --warning-light: #78350F;
    --danger: #F87171;
    --danger-light: #7F1D1D;
    --shadow-sm: 0 1px 2px rgba(0,0,0,0.2);
    --shadow-md: 0 4px 6px -1px rgba(0,0,0,0.25), 0 2px 4px -2px rgba(0,0,0,0.15);
}

/* ================================================================
   공통 레이아웃
   ================================================================ */
[data-testid="stToolbar"] > div > div:last-child { display: none !important; }
.block-container { padding-top: 0 !important; padding-bottom: 0 !important; }

/* sticky 탭을 위한 overflow 해제 (stMain은 스크롤 컨테이너이므로 제외) */
[data-testid="stMainBlockContainer"],
[data-testid="stVerticalBlockBorderWrapper"],
.main .block-container {
    overflow: visible !important;
}

/* ================================================================
   페이지 배경 + 텍스트
   ================================================================ */
.stApp,
[data-testid="stAppViewContainer"] {
    background-color: var(--bg-secondary) !important;
}
html.dark-theme .stApp,
html.dark-theme [data-testid="stAppViewContainer"] {
    background-color: var(--bg-primary) !important;
}
header[data-testid="stHeader"] {
    display: none !important;
}

/* 텍스트 컬러 */
html.dark-theme .stApp p, html.dark-theme .stApp span,
html.dark-theme .stApp label, html.dark-theme .stApp div,
html.dark-theme [data-testid="stMarkdownContainer"] *,
html.dark-theme [data-testid="stWidgetLabel"] *,
html.dark-theme .stRadio label span,
html.dark-theme .stSelectbox label,
html.dark-theme .stMultiSelect label,
html.dark-theme h1, html.dark-theme h2, html.dark-theme h3,
html.dark-theme h4, html.dark-theme h5, html.dark-theme h6 {
    color: var(--text-primary) !important;
}

/* ================================================================
   사이드바
   ================================================================ */
section[data-testid="stSidebar"] > div {
    background-color: var(--bg-card) !important;
    border-right: 1px solid var(--border) !important;
}

/* 사이드바 브랜드 */
.sidebar-brand {
    padding: 0.5rem 0 0.75rem 0;
    margin-bottom: 0.5rem;
    border-bottom: 2px solid var(--accent);
}
.sidebar-brand h3 {
    color: var(--text-primary) !important;
    font-size: 1.1rem !important;
    margin: 0 !important;
    font-weight: 700 !important;
    letter-spacing: -0.02em !important;
}
.sidebar-brand p {
    color: var(--text-muted) !important;
    font-size: 0.75rem !important;
    margin: 0.15rem 0 0 0 !important;
    font-weight: 400 !important;
}

/* 사이드바 필터 그룹 카드 */
.filter-card {
    background: var(--bg-secondary);
    border: 1px solid var(--border);
    border-radius: var(--radius-sm);
    padding: 0.85rem;
    margin-bottom: 0.75rem;
}
html.dark-theme .filter-card {
    background: var(--bg-primary);
}
.filter-label {
    font-size: 0.78rem !important;
    font-weight: 600 !important;
    color: var(--text-muted) !important;
    margin-bottom: 0.4rem !important;
    display: flex;
    align-items: center;
    gap: 0.35rem;
}

/* ================================================================
   탭 — 필(Pill) 스타일
   ================================================================ */
.stTabs [data-baseweb="tab-list"] {
    gap: 0.35rem !important;
    background: var(--bg-card) !important;
    border-radius: 0 !important;
    padding: 0.35rem 0.5rem !important;
    border: none !important;
    border-bottom: 1px solid var(--border) !important;
    box-shadow: 0 2px 4px rgba(0,0,0,0.06) !important;
    position: sticky !important;
    top: 0 !important;
    z-index: 999 !important;
}
html.dark-theme .stTabs [data-baseweb="tab-list"] {
    background: var(--bg-card) !important;
}
.stTabs [data-baseweb="tab"] {
    border-radius: var(--radius-sm) !important;
    padding: 0.55rem 1.1rem !important;
    font-size: 0.875rem !important;
    font-weight: 500 !important;
    color: var(--text-secondary) !important;
    background: transparent !important;
    border: none !important;
    transition: all 0.2s ease !important;
}
.stTabs [data-baseweb="tab"]:hover {
    background: var(--accent-light) !important;
    color: var(--accent) !important;
}
.stTabs [aria-selected="true"] {
    background: var(--accent) !important;
    color: white !important;
    font-weight: 600 !important;
    box-shadow: var(--shadow-sm) !important;
}
html.dark-theme .stTabs [aria-selected="true"] {
    color: white !important;
}
.stTabs [data-baseweb="tab-highlight"] { display: none !important; }
.stTabs [data-baseweb="tab-border"] { display: none !important; }
.stTabs [data-baseweb="tab-panel"] { padding-top: 0.75rem; }

/* ================================================================
   메트릭 카드
   ================================================================ */
[data-testid="stMetric"] {
    background: var(--bg-card) !important;
    border: 1px solid var(--border) !important;
    border-radius: var(--radius) !important;
    padding: 0.9rem 1.1rem !important;
    box-shadow: var(--shadow-sm) !important;
    transition: all 0.2s ease !important;
}
[data-testid="stMetric"]:hover {
    box-shadow: var(--shadow-md) !important;
    border-color: var(--accent) !important;
}
[data-testid="stMetric"] label {
    font-size: 0.75rem !important;
    font-weight: 600 !important;
    text-transform: uppercase !important;
    letter-spacing: 0.04em !important;
    color: var(--text-muted) !important;
}
[data-testid="stMetric"] [data-testid="stMetricValue"] {
    font-size: 1.6rem !important;
    font-weight: 700 !important;
    color: var(--text-primary) !important;
}

/* ================================================================
   버튼
   ================================================================ */
.stButton button {
    border-radius: var(--radius-sm) !important;
    font-weight: 500 !important;
    font-size: 0.875rem !important;
    padding: 0.5rem 1rem !important;
    border: 1px solid var(--border) !important;
    background: var(--bg-card) !important;
    color: var(--text-primary) !important;
    transition: all 0.2s ease !important;
    box-shadow: var(--shadow-sm) !important;
}
.stButton button:hover {
    border-color: var(--accent) !important;
    color: var(--accent) !important;
    box-shadow: var(--shadow-md) !important;
    transform: translateY(-1px);
}
.stButton button[kind="primary"] {
    background: var(--accent) !important;
    color: white !important;
    border-color: var(--accent) !important;
}
.stButton button[kind="primary"]:hover {
    background: var(--accent-hover) !important;
    color: white !important;
}

/* ================================================================
   입력 필드 / 셀렉트
   ================================================================ */
html.dark-theme .stTextInput input,
html.dark-theme .stTextArea textarea,
html.dark-theme [data-baseweb="select"] > div,
html.dark-theme [data-baseweb="input"] > div {
    background-color: var(--bg-primary) !important;
    color: var(--text-primary) !important;
    border-color: var(--border) !important;
}
html.dark-theme [data-baseweb="tag"] { background-color: var(--accent-light) !important; }
html.dark-theme [data-baseweb="popover"] > div,
html.dark-theme [data-baseweb="menu"] { background-color: var(--bg-card) !important; }
html.dark-theme [data-baseweb="menu"] li { color: var(--text-primary) !important; }
html.dark-theme [data-baseweb="menu"] li:hover { background-color: var(--accent-light) !important; }

[data-baseweb="select"] > div,
[data-baseweb="input"] > div,
.stTextInput input {
    border-radius: var(--radius-sm) !important;
}

/* ================================================================
   툴팁
   ================================================================ */
html.dark-theme [data-testid="stTooltipContent"],
html.dark-theme [data-baseweb="tooltip"] [role="tooltip"],
html.dark-theme [data-testid="stTooltipContent"] p,
html.dark-theme [data-testid="stTooltipContent"] div {
    background-color: var(--bg-card) !important;
    color: var(--text-primary) !important;
}

/* ================================================================
   데이터프레임 / 테이블
   ================================================================ */
[data-testid="stDataFrame"],
[data-testid="stDataEditor"] {
    border: 1px solid var(--border) !important;
    border-radius: var(--radius) !important;
    overflow: hidden !important;
    box-shadow: var(--shadow-sm) !important;
}

/* ================================================================
   구분선 / 기타
   ================================================================ */
hr, [data-testid="stDivider"] { border-color: var(--border) !important; opacity: 0.6 !important; }
html.dark-theme [data-testid="stCaptionContainer"] * { color: var(--text-muted) !important; }
html.dark-theme [data-testid="stExpander"] { border-color: var(--border) !important; }
.stProgress > div > div { background-color: var(--accent) !important; border-radius: 4px !important; }
.stProgress > div { background-color: var(--border) !important; border-radius: 4px !important; }
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
    section[data-testid="stSidebar"] .block-container { padding-top: 0.75rem; }
    section[data-testid="stSidebar"] [data-testid="stVerticalBlock"] > div { margin-bottom: -0.4rem; }
    </style>""", unsafe_allow_html=True)

    # 브랜드 섹션
    st.markdown("""
    <div class="sidebar-brand">
        <h3>유앤아이의원</h3>
        <p>장비 관리 시스템</p>
    </div>
    """, unsafe_allow_html=True)

    # 지점 선택
    st.markdown('<div class="filter-label">지점 선택</div>', unsafe_allow_html=True)
    selected_branches = st.multiselect(
        "지점 선택",
        options=all_branches,
        default=[],
        placeholder="지점명 입력하여 검색",
        help="지점명을 직접 입력하면 빠르게 찾을 수 있습니다",
        label_visibility="collapsed",
    )

    st.markdown("<div style='height:0.3rem'></div>", unsafe_allow_html=True)

    # 필터 설정 카드
    st.markdown('<div class="filter-card">', unsafe_allow_html=True)

    all_categories = sorted(df["카테고리"].unique()) if len(df) > 0 else []

    st.markdown('<div class="filter-label">카테고리</div>', unsafe_allow_html=True)
    selected_categories = st.multiselect(
        "카테고리 선택",
        options=all_categories,
        default=[],
        placeholder="전체 카테고리",
        label_visibility="collapsed",
    )

    st.markdown('<div class="filter-label">장비 검색</div>', unsafe_allow_html=True)
    search_query = st.text_input("장비 검색", placeholder="장비명 입력", label_visibility="collapsed")

    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown("<div style='height:0.3rem'></div>", unsafe_allow_html=True)

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

    # 푸터
    st.markdown(f"""
    <div style="margin-top:1rem; padding-top:0.75rem; border-top:1px solid var(--border);
                text-align:center; font-size:0.7rem; color:var(--text-muted);">
        마지막 로딩: {datetime.now().strftime('%Y-%m-%d %H:%M')}<br>
        {len(all_branches)}개 지점 · v1.0
    </div>
    """, unsafe_allow_html=True)
    # show_user_info_sidebar()  # 로그인 비활성화 중
    st.markdown(f"<div style='text-align:center;font-size:0.65rem;color:var(--text-muted);margin-top:0.25rem;'>{BRANDING}</div>", unsafe_allow_html=True)

# ============================================================
# 필터 적용
# ============================================================
filtered_df = apply_filters(df, selected_branches, selected_categories, search_query, "전체")

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
