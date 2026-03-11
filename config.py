# ============================================================
# 유앤아이의원 장비 현황 대시보드 — 설정
# Developed by smartbranding
# ============================================================

BRANDING = "Developed by smartbranding"

# 역할 정의
ROLES = {
    "viewer": {
        "label": "뷰어",
        "can_edit_photo": False,
        "can_save": False,
        "can_sync": False,
        "can_manage_users": False,
    },
    "editor": {
        "label": "편집자",
        "can_edit_photo": True,
        "can_save": True,
        "can_sync": False,
        "can_manage_users": False,
    },
    "admin": {
        "label": "관리자",
        "can_edit_photo": True,
        "can_save": True,
        "can_sync": True,
        "can_manage_users": True,
    },
}

# 종합시트 (b-sheet) ID
SUMMARY_SHEET_ID = "16d4L0pg91wYle5QSC6SCaCIrXmn0iTFpY2bDOYU8n0I"

# 지점명 → 종합시트 탭명 매핑
BRANCH_NAME_TO_TAB = {
    "경기광주점": "경기광주",
}

# braw CSV URL
CSV_URL = (
    "https://docs.google.com/spreadsheets/d/e/"
    "2PACX-1vT7kB-eQbBWxfLRB4mCoCfw-2nz7J2QhA5xmiwSxer2U8IPuNdqnm_"
    "-TR2i-BGqwpuoUeW6y8RzRdXV/pub"
    "?gid=1543424723&single=true&output=csv"
)

# 사진 있음 판정 값
PHOTO_YES = {"0", "0.0", "1", "1.0", "o", "O", "ㅇ", "있음", "v", "완료", "y", "yes"}

# 기기명 정규화 (유사 장비 그룹핑)
DEVICE_ALIASES = {
    "슈링크 유니버스": ["슈링크 유니버스", "슈링크유니버스", "유니버스슈링크", "유니버스 슈링크"],
    "울쎄라피 프라임": ["울쎄라피 프라임", "울쎄라피프라임", "울쎄라피 프라임/", "울쎄라"],
    "써마지FLX": ["써마지FLX", "써마지 FLX", "써마지flx", "써마지 flx", "미니 써마지"],
    "써마지": ["써마지"],
    "인모드": ["인모드"],
    "바디인모드": ["바디인모드", "바디 인모드", "인모드 (바디", "인모드(바디"],
    "클라리티2": ["클라리티2", "클라리티 2"],
    "클라리티 롱펄": ["클라리티 롱펄", "클라리티롱펄"],
    "보톡스": ["보톡스"],
    "리쥬란": ["리쥬란"],
    "쥬베룩": ["쥬베룩"],
    "올리지오X": ["올리지오X", "올리지오x", "올리지오 X"],
    "볼뉴머": ["볼뉴머"],
    "온다리프팅": ["온다리프팅", "온다 리프팅"],
    "필러": ["필러"],
}
