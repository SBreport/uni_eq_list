import streamlit as st
import plotly.express as px
from st_aggrid import AgGrid, GridOptionsBuilder, GridUpdateMode, DataReturnMode

from config import ROLES
from data import load_data
from sheets import save_photo_batch_to_sheet, update_braw_photo
from auth import hash_password
from users import (
    load_users, add_user, remove_user,
    update_user_role, update_user_password, invalidate_users_cache,
)


# ============================================================
# KPI 카드 헬퍼
# ============================================================
def _kpi_card(icon, label, value, color="var(--accent)"):
    """아이콘 + 라벨 + 대형 숫자 + 좌측 컬러 보더 카드"""
    return f"""
    <div style="background:var(--bg-card); border:1px solid var(--border);
                border-left:4px solid {color}; border-radius:var(--radius, 10px);
                padding:1rem 1.25rem; box-shadow:var(--shadow-sm, 0 1px 2px rgba(0,0,0,0.05));
                transition:all 0.2s ease; height:100%;">
        <div style="display:flex;align-items:center;gap:0.4rem;margin-bottom:0.3rem;">
            <span style="font-size:1.15rem;">{icon}</span>
            <span style="font-size:0.72rem;font-weight:600;text-transform:uppercase;
                         letter-spacing:0.04em;color:var(--text-muted, #94A3B8);">{label}</span>
        </div>
        <div style="font-size:1.65rem;font-weight:700;color:var(--text-primary, #1E293B);line-height:1.2;">
            {value}
        </div>
    </div>"""


# ============================================================
# 탭 1: 장비 목록 / 사진 관리
# ============================================================
def render_tab_equipment_list(filtered_df, df, selected_branches, permissions):
    if len(filtered_df) == 0:
        st.warning("선택한 조건에 해당하는 장비가 없습니다.")
        return

    # 저장 결과 메시지 표시
    if "save_result" in st.session_state:
        for msg in st.session_state.pop("save_result"):
            if msg.startswith("✅"):
                st.success(msg)
            elif msg.startswith("⚠️"):
                st.warning(msg)
            else:
                st.error(msg)

    st.markdown(f"**장비 목록** · {len(filtered_df):,}건")

    # AG-Grid 데이터 준비
    grid_df = filtered_df[["순번", "지점명", "기기명", "카테고리", "사진유무", "수량", "비고", "기기명_원본"]].copy()
    grid_df = grid_df.reset_index(drop=True)

    can_edit = permissions["can_edit_photo"] and permissions["can_save"]

    # 편집 모드: 사진유무를 True/False 체크박스로
    if can_edit:
        grid_df["사진"] = grid_df["사진유무"].apply(lambda x: x == "있음")
    else:
        grid_df["사진"] = grid_df["사진유무"]

    # AG-Grid 옵션 설정
    gb = GridOptionsBuilder.from_dataframe(
        grid_df[["순번", "지점명", "기기명", "카테고리", "사진", "수량", "비고"]]
    )

    # 공통: 열별 정렬/너비 설정
    gb.configure_column("순번", header_name="No", width=60,
                        cellStyle={"textAlign": "center"},
                        headerClass="ag-center-header")
    gb.configure_column("지점명", width=80,
                        cellStyle={"textAlign": "center"},
                        headerClass="ag-center-header")
    gb.configure_column("기기명", width=200, flex=2)
    gb.configure_column("카테고리", width=90,
                        cellStyle={"textAlign": "center"},
                        headerClass="ag-center-header")
    gb.configure_column("수량", width=60,
                        cellStyle={"textAlign": "center"},
                        headerClass="ag-center-header")
    gb.configure_column("비고", width=150, flex=1)

    if can_edit:
        gb.configure_column("사진", header_name="사진", width=70, editable=True,
                            cellRenderer="agCheckboxCellRenderer",
                            cellEditor="agCheckboxCellEditor",
                            cellStyle={"textAlign": "center"},
                            headerClass="ag-center-header")
    else:
        gb.configure_column("사진", width=70,
                            cellStyle={"textAlign": "center"},
                            headerClass="ag-center-header")

    gb.configure_default_column(sortable=True, filterable=False, resizable=True)
    gb.configure_grid_options(
        domLayout="normal",
        rowHeight=28,
        headerHeight=32,
    )

    grid_options = gb.build()

    # 헤더 가운데 정렬 + 셀 컴팩트 CSS + 다크모드 (html.dark-theme 스코프)
    custom_css = {
        # ── 공통 ──
        ".ag-center-header": {"text-align": "center !important"},
        ".ag-header-cell-label": {"justify-content": "center"},
        ".ag-cell": {"padding": "0 6px !important", "line-height": "28px !important"},
        ".ag-header-cell": {"padding": "0 6px !important"},
        ".ag-row": {"font-size": "13px"},
        ".ag-cell-wrapper": {"justify-content": "center"},
        ".ag-checkbox-input-wrapper": {"margin": "0 auto"},
        # ── 라이트 모드 개선 ──
        ".ag-header": {"background-color": "#F8FAFC !important", "border-bottom": "2px solid #2563EB !important"},
        ".ag-header-cell": {"background-color": "#F8FAFC !important", "color": "#1E293B !important",
                            "padding": "0 6px !important", "font-weight": "600 !important"},
        ".ag-row-odd": {"background-color": "#FAFBFC !important"},
        ".ag-row-hover": {"background-color": "#EFF6FF !important"},
        ".ag-root-wrapper": {"border": "1px solid #E2E8F0 !important", "border-radius": "8px !important"},
        # ── 다크 모드 (JS가 iframe :root에 .dark-theme 추가 시 활성) ──
        ":root.dark-theme .ag-cell": {
            "color": "#E0E0E0 !important", "border-color": "#2A2A4A !important",
        },
        ":root.dark-theme .ag-header": {"background-color": "#1E293B !important", "border-bottom": "2px solid #3B82F6 !important"},
        ":root.dark-theme .ag-header-cell": {
            "background-color": "#1E293B !important", "color": "#F1F5F9 !important",
        },
        ":root.dark-theme .ag-header-cell-label": {"color": "#F1F5F9 !important"},
        ":root.dark-theme .ag-row": {
            "background-color": "#0F172A !important", "color": "#E0E0E0 !important",
        },
        ":root.dark-theme .ag-root-wrapper": {
            "background-color": "#0F172A !important", "border-color": "#334155 !important",
        },
        ":root.dark-theme .ag-row-odd": {"background-color": "#1E293B !important"},
        ":root.dark-theme .ag-row-hover": {"background-color": "#1E3A5F !important"},
        ":root.dark-theme .ag-body-viewport": {"background-color": "#0F172A !important"},
    }

    # AG-Grid 렌더링
    grid_response = AgGrid(
        grid_df[["순번", "지점명", "기기명", "카테고리", "사진", "수량", "비고"]],
        gridOptions=grid_options,
        custom_css=custom_css,
        height=600,
        update_mode=GridUpdateMode.VALUE_CHANGED if can_edit else GridUpdateMode.NO_UPDATE,
        data_return_mode=DataReturnMode.FILTERED_AND_SORTED,
        fit_columns_on_grid_load=True,
        allow_unsafe_jscode=True,
        theme="streamlit",
    )

    # 버튼 영역
    if can_edit:
        col_save, col_download = st.columns([1, 1])

        with col_save:
            if st.button("변경 사항 저장", type="primary", use_container_width=True):
                edited_data = grid_response["data"]
                changes = []
                for i, row in enumerate(edited_data.itertuples(index=False)):
                    orig_photo = grid_df.iloc[i]["사진"]
                    new_photo = edited_data.iloc[i]["사진"]
                    if new_photo != orig_photo:
                        value = "0" if new_photo else ""
                        device_orig = str(grid_df.iloc[i]["기기명_원본"]).strip()
                        branch = str(grid_df.iloc[i]["지점명"]).strip()
                        changes.append((branch, device_orig, value))

                if changes:
                    with st.spinner(f"{len(changes)}건 저장 중..."):
                        ok_count, errors = save_photo_batch_to_sheet(changes)

                    if ok_count > 0:
                        save_msgs = [f"✅ {ok_count}건 저장 완료"]
                        if errors:
                            for e in errors:
                                save_msgs.append(f"❌ {e}")

                        with st.spinner("데이터 동기화 중..."):
                            braw_ok, braw_msg = update_braw_photo(changes)
                        if braw_ok:
                            save_msgs.append(f"✅ {braw_msg}")
                        else:
                            save_msgs.append(f"⚠️ {braw_msg}")

                        st.session_state["save_result"] = save_msgs
                        st.session_state["pending_photo_changes"] = changes
                        load_data.clear()
                        st.rerun()
                    elif errors:
                        for e in errors:
                            st.error(f"❌ {e}")
                    else:
                        st.warning("저장 실패 — 인증 정보를 확인하세요.")
                else:
                    st.info("변경된 항목이 없습니다.")

        with col_download:
            csv_data = grid_df[["순번", "지점명", "기기명", "카테고리", "사진유무", "수량", "비고"]].to_csv(index=False).encode("utf-8-sig")
            st.download_button("CSV 다운로드", csv_data, "equipment_list.csv", "text/csv", use_container_width=True)
    else:
        csv_data = grid_df[["순번", "지점명", "기기명", "카테고리", "사진유무", "수량", "비고"]].to_csv(index=False).encode("utf-8-sig")
        st.download_button("CSV 다운로드", csv_data, "equipment_list.csv", "text/csv", use_container_width=True)

    # 사진 현황 요약
    if selected_branches:
        st.markdown(f"**📷 사진 현황 요약** · {len(selected_branches)}개 지점")
        photo_summary = (
            filtered_df.groupby(["지점명", "사진유무"])
            .size()
            .unstack(fill_value=0)
            .reset_index()
        )
        if "있음" not in photo_summary.columns:
            photo_summary["있음"] = 0
        if "없음" not in photo_summary.columns:
            photo_summary["없음"] = 0
        photo_summary["보유율"] = (
            photo_summary["있음"] / (photo_summary["있음"] + photo_summary["없음"]) * 100
        ).round(1)

        cols = st.columns(min(len(selected_branches), 4))
        for i, branch in enumerate(selected_branches):
            row = photo_summary[photo_summary["지점명"] == branch]
            if len(row) > 0:
                row = row.iloc[0]
                pct = row["보유율"]
                bar_color = "var(--success, #059669)" if pct >= 80 else ("var(--warning, #D97706)" if pct >= 50 else "var(--danger, #DC2626)")
                with cols[i % len(cols)]:
                    st.markdown(f"""
                    <div style="background:var(--bg-card, #fff); border:1px solid var(--border, #E2E8F0);
                                border-radius:var(--radius-sm, 6px); padding:0.75rem; margin-bottom:0.5rem;
                                box-shadow:var(--shadow-sm, 0 1px 2px rgba(0,0,0,0.05));">
                        <div style="font-weight:600; font-size:0.875rem; color:var(--text-primary, #1E293B); margin-bottom:0.4rem;">
                            {branch}
                        </div>
                        <div style="background:var(--border, #E2E8F0); border-radius:4px; height:6px; overflow:hidden;">
                            <div style="background:{bar_color}; height:100%; width:{pct}%; border-radius:4px;
                                        transition:width 0.5s ease;"></div>
                        </div>
                        <div style="font-size:0.72rem; color:var(--text-muted, #94A3B8); margin-top:0.3rem;">
                            있음 {int(row['있음'])} / 없음 {int(row['없음'])} ({pct}%)
                        </div>
                    </div>
                    """, unsafe_allow_html=True)


# ============================================================
# 탭 2: 장비 통합 검색
# ============================================================
def render_tab_search(filtered_df, df):
    if len(df) == 0:
        st.warning("데이터가 없습니다.")
        return

    st.subheader("장비 통합 검색")
    st.caption("유사한 이름의 장비를 하나의 그룹으로 묶어서 조회합니다.")

    all_groups = sorted(filtered_df["장비그룹"].unique())
    selected_group = st.selectbox("장비 그룹 선택", options=["전체"] + all_groups)

    if selected_group == "전체":
        group_summary = (
            filtered_df.groupby("장비그룹")
            .agg(보유지점수=("지점명", "nunique"), 총수량=("수량", "sum"), 카테고리=("카테고리", "first"))
            .sort_values("보유지점수", ascending=False)
            .reset_index()
        )
        group_summary.columns = ["장비그룹", "보유 지점 수", "총 수량", "카테고리"]

        st.dataframe(
            group_summary,
            use_container_width=True,
            height=600,
            column_config={
                "장비그룹": st.column_config.TextColumn("장비명 (통합)", width="large"),
                "보유 지점 수": st.column_config.NumberColumn("보유 지점 수", width="medium"),
                "총 수량": st.column_config.NumberColumn("총 수량", width="small"),
                "카테고리": st.column_config.TextColumn("카테고리", width="medium"),
            },
        )
    else:
        group_df = filtered_df[filtered_df["장비그룹"] == selected_group]

        has = len(group_df[group_df["사진유무"] == "있음"])
        col_a, col_b, col_c = st.columns(3)
        with col_a:
            st.markdown(_kpi_card("🏢", "보유 지점 수", f"{group_df['지점명'].nunique()}", "var(--accent, #2563EB)"), unsafe_allow_html=True)
        with col_b:
            st.markdown(_kpi_card("📦", "총 수량", f"{int(group_df['수량'].sum())}", "var(--success, #059669)"), unsafe_allow_html=True)
        with col_c:
            st.markdown(_kpi_card("📷", "사진 보유율", f"{has}/{len(group_df)}", "var(--warning, #D97706)"), unsafe_allow_html=True)
        st.markdown("<div style='height:0.5rem'></div>", unsafe_allow_html=True)

        variants = group_df["기기명"].unique().tolist()
        if len(variants) > 1:
            st.info(f"이 그룹에 포함된 기기명 변형: {', '.join(variants)}")

        st.dataframe(
            group_df[["지점명", "기기명", "수량", "비고", "사진유무"]],
            use_container_width=True,
            column_config={
                "지점명": st.column_config.TextColumn("지점명", width="medium"),
                "기기명": st.column_config.TextColumn("기기명 (원본)", width="large"),
                "수량": st.column_config.NumberColumn("수량", width="small"),
                "비고": st.column_config.TextColumn("비고", width="large"),
                "사진유무": st.column_config.TextColumn("사진", width="small"),
            },
        )

        all_branch_set = set(df["지점명"].unique())
        has_branch_set = set(group_df["지점명"].unique())
        missing = sorted(all_branch_set - has_branch_set)
        if missing:
            with st.expander(f"미보유 지점 ({len(missing)}개)"):
                st.write(", ".join(missing))


# ============================================================
# 탭 3: 지점 비교
# ============================================================
def render_tab_compare(df, selected_branches):
    if len(df) == 0:
        st.warning("데이터가 없습니다.")
        return

    compare_default = selected_branches if selected_branches else []
    compare_branches = st.multiselect(
        "비교할 지점을 선택하세요 (2개 이상)",
        options=sorted(df["지점명"].unique()),
        default=compare_default,
        key="compare_branches",
    )

    if len(compare_branches) < 2:
        st.info("비교하려면 2개 이상의 지점을 선택해주세요.")
        return

    compare_df = df[df["지점명"].isin(compare_branches)]

    st.markdown("**지점별 카테고리 장비 수량 비교**")
    grouped = compare_df.groupby(["지점명", "카테고리"])["수량"].sum().reset_index()
    fig_compare = px.bar(
        grouped, x="카테고리", y="수량", color="지점명",
        barmode="group",
        color_discrete_sequence=["#2563EB", "#059669", "#D97706", "#DC2626", "#7C3AED", "#0891B2"],
    )
    fig_compare.update_layout(
        height=450, margin=dict(l=10, r=10, t=10, b=10),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(size=12, color="#64748B"),
        xaxis=dict(gridcolor="#E2E8F0"), yaxis=dict(gridcolor="#E2E8F0"),
        showlegend=True,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1,
                    font=dict(size=11), bgcolor="rgba(0,0,0,0)"),
    )
    fig_compare.update_traces(marker_cornerradius=4, marker_line_width=0)
    st.plotly_chart(fig_compare, use_container_width=True)

    st.markdown("**상세 비교 테이블**")
    pivot_compare = compare_df.pivot_table(
        index="지점명", columns="카테고리", values="수량", aggfunc="sum", fill_value=0,
    )
    pivot_compare["합계"] = pivot_compare.sum(axis=1)
    pivot_compare = pivot_compare.sort_values("합계", ascending=False)
    st.dataframe(pivot_compare, use_container_width=True)


# ============================================================
# 탭 4: 대시보드
# ============================================================
def render_tab_dashboard(filtered_df):
    if len(filtered_df) == 0:
        st.warning("선택한 조건에 해당하는 장비가 없습니다.")
        return

    total_qty = int(filtered_df["수량"].sum())
    branch_count = filtered_df["지점명"].nunique()
    cat_count = filtered_df["카테고리"].nunique()
    avg_per_branch = filtered_df.groupby("지점명")["수량"].sum().mean()

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.markdown(_kpi_card("📦", "총 장비 수량", f"{total_qty:,}", "var(--accent, #2563EB)"), unsafe_allow_html=True)
    with col2:
        st.markdown(_kpi_card("🏢", "지점 수", f"{branch_count}", "var(--success, #059669)"), unsafe_allow_html=True)
    with col3:
        st.markdown(_kpi_card("📂", "카테고리 수", f"{cat_count}", "var(--warning, #D97706)"), unsafe_allow_html=True)
    with col4:
        st.markdown(_kpi_card("📊", "평균 장비/지점", f"{avg_per_branch:.1f}", "#7C3AED"), unsafe_allow_html=True)

    st.markdown("<div style='height:0.5rem'></div>", unsafe_allow_html=True)

    has_photo = len(filtered_df[filtered_df["사진유무"] == "있음"])
    no_photo = len(filtered_df[filtered_df["사진유무"] == "없음"])
    photo_pct = (has_photo / len(filtered_df) * 100) if len(filtered_df) > 0 else 0

    col5, col6, col7, col8 = st.columns(4)
    with col5:
        st.markdown(_kpi_card("✅", "사진 보유", f"{has_photo}건", "var(--success, #059669)"), unsafe_allow_html=True)
    with col6:
        st.markdown(_kpi_card("❌", "사진 미보유", f"{no_photo}건", "var(--danger, #DC2626)"), unsafe_allow_html=True)
    with col7:
        st.markdown(_kpi_card("📈", "사진 보유율", f"{photo_pct:.1f}%", "var(--accent, #2563EB)"), unsafe_allow_html=True)
    with col8:
        st.markdown(_kpi_card("🔬", "고유 장비 종류", f"{filtered_df['장비그룹'].nunique()}", "#0891B2"), unsafe_allow_html=True)

    st.divider()

    chart_col1, chart_col2 = st.columns(2)

    _chart_layout = dict(
        showlegend=False, coloraxis_showscale=False,
        margin=dict(l=10, r=10, t=10, b=10),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(size=12, color="#64748B"),
        xaxis=dict(gridcolor="#E2E8F0", zerolinecolor="#E2E8F0"),
        yaxis=dict(gridcolor="#E2E8F0", zerolinecolor="#E2E8F0"),
    )

    with chart_col1:
        st.markdown("**카테고리별 장비 수량**")
        cat_data = filtered_df.groupby("카테고리")["수량"].sum().sort_values(ascending=True).reset_index()
        fig_cat = px.bar(cat_data, x="수량", y="카테고리", orientation="h", color="수량",
                         color_continuous_scale=["#DBEAFE", "#2563EB"])
        fig_cat.update_layout(height=400, **_chart_layout)
        fig_cat.update_traces(marker_cornerradius=4, marker_line_width=0)
        st.plotly_chart(fig_cat, use_container_width=True)

    with chart_col2:
        st.markdown("**지점별 총 장비 수량 (Top 15)**")
        branch_data = filtered_df.groupby("지점명")["수량"].sum().sort_values(ascending=False).head(15).sort_values(ascending=True).reset_index()
        fig_branch = px.bar(branch_data, x="수량", y="지점명", orientation="h", color="수량",
                            color_continuous_scale=["#D1FAE5", "#059669"])
        fig_branch.update_layout(height=400, **_chart_layout)
        fig_branch.update_traces(marker_cornerradius=4, marker_line_width=0)
        st.plotly_chart(fig_branch, use_container_width=True)

    chart_col3, chart_col4 = st.columns(2)

    _cat_colors = ["#2563EB", "#059669", "#D97706", "#DC2626", "#7C3AED", "#0891B2", "#DB2777", "#65A30D"]

    with chart_col3:
        st.markdown("**카테고리 분포**")
        pie_data = filtered_df.groupby("카테고리")["수량"].sum().reset_index()
        fig_pie = px.pie(pie_data, values="수량", names="카테고리", hole=0.4,
                         color_discrete_sequence=_cat_colors)
        fig_pie.update_layout(height=400, margin=dict(l=0, r=0, t=10, b=0),
                              paper_bgcolor="rgba(0,0,0,0)", font=dict(size=12, color="#64748B"))
        st.plotly_chart(fig_pie, use_container_width=True)

    with chart_col4:
        st.markdown("**지점 × 카테고리 히트맵**")
        pivot = filtered_df.pivot_table(index="지점명", columns="카테고리", values="수량", aggfunc="sum", fill_value=0)
        fig_heat = px.imshow(pivot, color_continuous_scale=["#EFF6FF", "#2563EB"], aspect="auto")
        fig_heat.update_layout(height=max(400, len(pivot) * 18), margin=dict(l=0, r=0, t=10, b=0),
                               paper_bgcolor="rgba(0,0,0,0)", font=dict(size=11, color="#64748B"))
        st.plotly_chart(fig_heat, use_container_width=True)


# ============================================================
# 탭 5: 사용자 관리 (관리자 전용)
# ============================================================
def render_admin_panel():
    st.subheader("사용자 관리")

    users = load_users()

    # 현재 사용자 목록
    if users:
        user_table = [{"사용자 ID": u["username"], "역할": ROLES.get(u["role"], {}).get("label", u["role"])} for u in users]
        st.dataframe(user_table, use_container_width=True, hide_index=True)
    else:
        st.info("등록된 사용자가 없습니다.")

    st.divider()

    col_add, col_manage = st.columns(2)

    # 사용자 추가
    with col_add:
        st.markdown("**사용자 추가**")
        with st.form("add_user_form"):
            new_username = st.text_input("사용자 ID")
            new_password = st.text_input("비밀번호", type="password")
            new_password_confirm = st.text_input("비밀번호 확인", type="password")
            new_role = st.selectbox(
                "역할", options=["viewer", "editor", "admin"],
                format_func=lambda r: ROLES[r]["label"],
            )
            submitted = st.form_submit_button("추가", type="primary", use_container_width=True)
            if submitted:
                if not new_username or not new_password:
                    st.error("ID와 비밀번호를 입력해주세요.")
                elif len(new_username) < 2:
                    st.error("ID는 2자 이상이어야 합니다.")
                elif new_password != new_password_confirm:
                    st.error("비밀번호가 일치하지 않습니다.")
                else:
                    hashed = hash_password(new_password)
                    ok, msg = add_user(new_username, hashed, new_role)
                    if ok:
                        st.success(msg)
                        st.rerun()
                    else:
                        st.error(msg)

    # 역할 변경 / 삭제 / 비밀번호 초기화
    with col_manage:
        current_user = st.session_state.get("username", "")
        other_users = [u["username"] for u in users if u["username"] != current_user]

        if not other_users:
            st.info("관리할 다른 사용자가 없습니다.")
        else:
            st.markdown("**역할 변경**")
            role_target = st.selectbox("대상 사용자", other_users, key="role_target")
            role_new = st.selectbox(
                "새 역할", options=["viewer", "editor", "admin"],
                format_func=lambda r: ROLES[r]["label"], key="role_new",
            )
            if st.button("역할 변경", use_container_width=True):
                ok, msg = update_user_role(role_target, role_new)
                if ok:
                    st.success(msg)
                    st.rerun()
                else:
                    st.error(msg)

            st.divider()

            st.markdown("**비밀번호 초기화**")
            pw_target = st.selectbox("대상 사용자", other_users, key="pw_target")
            pw_new = st.text_input("새 비밀번호", type="password", key="pw_new")
            if st.button("비밀번호 변경", use_container_width=True):
                if not pw_new:
                    st.error("새 비밀번호를 입력해주세요.")
                else:
                    hashed = hash_password(pw_new)
                    ok, msg = update_user_password(pw_target, hashed)
                    if ok:
                        st.success(msg)
                    else:
                        st.error(msg)

            st.divider()

            st.markdown("**사용자 삭제**")
            del_target = st.selectbox("대상 사용자", other_users, key="del_target")
            del_confirm = st.checkbox(f"'{del_target}' 삭제를 확인합니다", key="del_confirm")
            if st.button("삭제", type="primary", use_container_width=True):
                if not del_confirm:
                    st.error("삭제 확인란을 체크해주세요.")
                else:
                    ok, msg = remove_user(del_target)
                    if ok:
                        st.success(msg)
                        st.rerun()
                    else:
                        st.error(msg)


# ============================================================
# 탭: 가이드
# ============================================================
def render_tab_guide():
    st.subheader("운영 가이드")
    st.caption("시스템 관리를 위한 절차 안내입니다.")

    with st.expander("신규 지점 생성 시 해야 할 일", expanded=False):
        st.markdown("""
**새로운 지점을 시스템에 추가하는 절차입니다.**

**① 지점 전용 Google 스프레드시트 생성**
- Google Drive에서 새 스프레드시트를 만듭니다.
- 시트 이름을 `Copy of [지점명]`으로 설정합니다.

**② 시트 구조 설정 (1행에 아래 헤더 입력)**

| 열 | 항목 |
|---|---|
| A | 순번 |
| B | 지점명 |
| C | 카테고리 |
| D | 기기명 |
| E | 수량 |
| F | 비고 |
| G | 사진 |

**③ 종합시트에 연결**
- 종합시트에서 새 탭을 만들고 지점명으로 이름 설정
- A1 셀에 IMPORTRANGE 수식 입력:
  ```
  =IMPORTRANGE("스프레드시트_URL", "'Copy of 지점명'!A1:Z")
  ```

**④ 시스템 설정 파일 업데이트**
- `branch_sources.json` 파일에 새 지점 정보를 추가합니다.
- 관리자에게 요청하세요.

**⑤ 권한 부여**
- 새 스프레드시트 → 공유 → 서비스 계정 이메일에 편집 권한 부여

**⑥ 전체 동기화**
- 대시보드 좌측 '전체 동기화' 버튼 클릭
""")

    with st.expander("신규 장비 입고 시 해야 할 일", expanded=False):
        st.markdown("""
**기존 지점에 새 장비를 추가하는 절차입니다.**

**① 해당 지점의 Google 스프레드시트 열기**
- 해당 지점의 전용 스프레드시트를 엽니다.

**② 새 장비 행 추가**
- 마지막 행 아래에 새 행을 추가합니다.

| 열 | 입력 내용 | 예시 |
|---|---|---|
| A | 순번 (다음 번호) | 45 |
| B | 지점명 | 강남점 |
| C | 카테고리 | 리프팅 |
| D | 기기명 | 울쎄라피 프라임 |
| E | 수량 | 1 |
| F | 비고 (선택) | 2024년 도입 |
| G | 사진 | (비워두기) |

**③ 대시보드에서 확인**
- '새로고침' 버튼을 누르면 자동으로 반영됩니다.
- 반영이 안 될 경우 '전체 동기화' 버튼을 클릭합니다.
""")
