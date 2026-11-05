
import streamlit as st
import pandas as pd
import plotly.express as px
import re
from itertools import combinations
from collections import Counter

# -----------------------------
# 페이지 설정
# -----------------------------
st.set_page_config(
    page_title="급식 규칙 찾기",
    page_icon="🍱",
    layout="wide"
)

st.title("🍱 급식 규칙 찾기")
st.caption("송탄고 급식 데이터로 메뉴 사이의 연관 규칙을 찾아봅니다.")

DATA_URL = "https://raw.githubusercontent.com/it-teacher-go/data-share-/main/songtan_meals_184.csv"


# -----------------------------
# 데이터 불러오기
# -----------------------------
@st.cache_data
def load_data():
    df = pd.read_csv(DATA_URL, encoding="utf-8")

    required_columns = ["날짜", "식사", "메뉴"]
    for col in required_columns:
        if col not in df.columns:
            raise ValueError(f"CSV에 '{col}' 열이 없습니다.")

    return df


# -----------------------------
# 메뉴 이름 정리
# 괄호와 괄호 안의 내용 제거
# -----------------------------
def clean_menu(menu):
    menu = str(menu)

    # 일반 괄호와 전각 괄호 안의 내용 제거
    menu = re.sub(r"\([^)]*\)", "", menu)
    menu = re.sub(r"（[^）]*）", "", menu)

    return menu.strip()


# -----------------------------
# 연관 규칙 분석
# -----------------------------
def analyze_rules(df):

    baskets = []

    for menu_text in df["메뉴"].dropna():

        menus = [
            clean_menu(menu)
            for menu in str(menu_text).split("|")
        ]

        # 빈 메뉴 제거 및 같은 장바구니 안 중복 제거
        menus = sorted(set(menu for menu in menus if menu))

        if menus:
            baskets.append(menus)

    total_days = len(baskets)

    # 메뉴별 등장 횟수
    menu_count = Counter()

    # 같은 날 등장한 메뉴 쌍의 횟수
    pair_count = Counter()

    for basket in baskets:
        menu_count.update(basket)

        for a, b in combinations(basket, 2):
            pair_count[(a, b)] += 1

    # 메뉴 종류 수
    menu_types = len(menu_count)

    # 규칙 생성
    rules = []

    for (a, b), count in pair_count.items():

        support = count / total_days
        confidence_ab = count / menu_count[a]
        confidence_ba = count / menu_count[b]

        support_a = menu_count[a] / total_days
        support_b = menu_count[b] / total_days

        lift_ab = confidence_ab / support_b
        lift_ba = confidence_ba / support_a

        # A -> B
        rules.append({
            "조건": a,
            "결과": b,
            "동시": count,
            "지지도": support,
            "신뢰도": confidence_ab,
            "향상도": lift_ab
        })

        # B -> A
        rules.append({
            "조건": b,
            "결과": a,
            "동시": count,
            "지지도": support,
            "신뢰도": confidence_ba,
            "향상도": lift_ba
        })

    rules_df = pd.DataFrame(rules)

    menus = sorted(menu_count.keys())

    return baskets, rules_df, menus, total_days, menu_types, len(pair_count)


# -----------------------------
# 앱 실행
# -----------------------------
try:
    df = load_data()

    baskets, rules_df, menus, total_days, menu_types, pair_types = analyze_rules(df)

except Exception as e:
    st.error(f"데이터를 불러오거나 분석하는 중 오류가 발생했습니다: {e}")
    st.stop()


# -----------------------------
# 주요 통계
# -----------------------------
st.subheader("📊 데이터 요약")

col1, col2, col3 = st.columns(3)

col1.metric("급식 일수", f"{total_days}일")
col2.metric("메뉴 종류 수", f"{menu_types}개")
col3.metric("함께 나온 메뉴 쌍", f"{pair_types}쌍")

st.divider()


# -----------------------------
# 메뉴 및 정렬 선택
# -----------------------------
st.subheader("🔍 연관 규칙 탐색")

col1, col2 = st.columns(2)

with col1:
    selected_menu = st.selectbox(
        "메뉴 선택",
        ["전체 메뉴"] + menus
    )

with col2:
    sort_option = st.selectbox(
        "정렬 기준",
        ["향상도 순", "신뢰도 순", "동시 순"]
    )


# -----------------------------
# 메뉴 필터링
# -----------------------------
filtered = rules_df.copy()

if selected_menu != "전체 메뉴":
    filtered = filtered[
        (filtered["조건"] == selected_menu) |
        (filtered["결과"] == selected_menu)
    ]

# -----------------------------
# 정렬
# -----------------------------
sort_columns = {
    "향상도 순": "향상도",
    "신뢰도 순": "신뢰도",
    "동시 순": "동시"
}

sort_column = sort_columns[sort_option]

filtered = filtered.sort_values(
    by=[sort_column, "신뢰도", "동시"],
    ascending=[False, False, False]
).reset_index(drop=True)


# -----------------------------
# 연관 규칙 표
# -----------------------------
st.subheader("📋 메뉴 연관 규칙")

st.caption(
    "조건 메뉴가 나온 날에 결과 메뉴도 함께 나오는 경향을 나타냅니다."
)

if filtered.empty:
    st.warning("선택한 메뉴에 해당하는 연관 규칙이 없습니다.")

else:
    display_df = filtered.copy()

    display_df["지지도"] = display_df["지지도"].map(
        lambda x: f"{x:.1%}"
    )

    display_df["신뢰도"] = display_df["신뢰도"].map(
        lambda x: f"{x:.1%}"
    )

    display_df["향상도"] = display_df["향상도"].map(
        lambda x: f"{x:.3f}"
    )

    st.dataframe(
        display_df,
        use_container_width=True,
        hide_index=True
    )

    st.caption(f"현재 표시 중인 규칙: {len(filtered)}개")


# -----------------------------
# 향상도 상위 10개 그래프
# -----------------------------
st.divider()
st.subheader("📈 향상도 TOP 10")

st.write(
    "향상도가 높을수록 두 메뉴가 서로 독립적으로 나올 때보다 "
    "함께 나오는 경향이 강하다는 뜻입니다."
)

if filtered.empty:
    st.info("그래프로 표시할 규칙이 없습니다.")

else:
    top10 = filtered.nlargest(10, "향상도").copy()

    # 그래프에 표시할 규칙 이름
    top10["규칙"] = (
        top10["조건"] + " → " + top10["결과"]
    )

    # 보기 편하게 오름차순으로 배치
    top10 = top10.sort_values("향상도", ascending=True)

    fig = px.bar(
        top10,
        x="향상도",
        y="규칙",
        orientation="h",
        text="향상도",
        hover_data={
            "조건": True,
            "결과": True,
            "동시": True,
            "지지도": ":.1%",
            "신뢰도": ":.1%",
            "향상도": ":.3f",
            "규칙": False
        },
        labels={
            "향상도": "향상도 (Lift)",
            "규칙": "메뉴 연관 규칙"
        },
        title="향상도가 높은 메뉴 연관 규칙 TOP 10"
    )

    fig.update_traces(
        texttemplate="%{text:.3f}",
        textposition="outside",
        cliponaxis=False
    )

    fig.update_layout(
        height=550,
        xaxis_title="향상도",
        yaxis_title="메뉴 규칙",
        margin=dict(l=20, r=60, t=70, b=30)
    )

    st.plotly_chart(fig, use_container_width=True)


# -----------------------------
# 지표 설명
# -----------------------------
st.divider()
st.subheader("📖 연관 규칙 분석 지표 알아보기")

with st.expander("각 지표의 의미 확인하기"):

    st.markdown("""
    **1. 지지도 (Support)**

    전체 급식 일수 중 두 메뉴가 같은 날 함께 나온 비율입니다.

    지지도 = 두 메뉴가 함께 나온 일수 / 전체 급식 일수

    **2. 신뢰도 (Confidence)**

    조건 메뉴가 나온 날 중 결과 메뉴도 함께 나온 비율입니다.

    신뢰도 = 두 메뉴가 함께 나온 일수 / 조건 메뉴가 나온 일수

    **3. 향상도 (Lift)**

    두 메뉴의 동시 출현이 우연히 독립적으로 나타나는 경우보다
    얼마나 더 자주 나타나는지를 보여 줍니다.

    향상도 = 신뢰도 / 결과 메뉴의 출현 비율

    - 향상도 > 1 : 함께 나오는 경향이 있음
    - 향상도 = 1 : 서로 독립적인 경향
    - 향상도 < 1 : 함께 나오지 않는 경향

    **4. 동시**

    두 메뉴가 같은 급식에 함께 등장한 횟수입니다.

    ※ 연관 규칙은 메뉴 사이의 통계적 관계를 나타내며,
    한 메뉴가 다른 메뉴의 출현 원인이라는 뜻은 아닙니다.
    """)
