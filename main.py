

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

        # 빈 메뉴 제거 및 중복 제거
        menus = sorted(set(menu for menu in menus if menu))

        if menus:
            baskets.append(menus)

    total_days = len(baskets)

    # 메뉴별 등장 횟수
    menu_count = Counter()

    # 함께 등장한 메뉴 쌍의 횟수
    pair_count = Counter()

    for basket in baskets:

        menu_count.update(basket)

        for a, b in combinations(basket, 2):
            pair_count[(a, b)] += 1

    menu_types = len(menu_count)

    # 연관 규칙 생성
    rules = []

    for (a, b), count in pair_count.items():

        support = count / total_days

        support_a = menu_count[a] / total_days
        support_b = menu_count[b] / total_days

        confidence_ab = count / menu_count[a]
        confidence_ba = count / menu_count[b]

        lift_ab = confidence_ab / support_b
        lift_ba = confidence_ba / support_a

        # A → B
        rules.append({
            "조건": a,
            "결과": b,
            "동시": count,
            "지지도": support,
            "신뢰도": confidence_ab,
            "향상도": lift_ab
        })

        # B → A
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

    return (
        baskets,
        rules_df,
        menus,
        menu_count,
        pair_count,
        total_days,
        menu_types,
        len(pair_count)
    )


# -----------------------------
# 앱 실행
# -----------------------------
try:

    df = load_data()

    (
        baskets,
        rules_df,
        menus,
        menu_count,
        pair_count,
        total_days,
        menu_types,
        pair_types
    ) = analyze_rules(df)

except Exception as e:

    st.error(f"데이터 분석 중 오류가 발생했습니다: {e}")
    st.stop()


# -----------------------------
# 데이터 요약
# -----------------------------
st.subheader("📊 데이터 요약")

col1, col2, col3 = st.columns(3)

col1.metric("급식 일수", f"{total_days}일")
col2.metric("메뉴 종류 수", f"{menu_types}개")
col3.metric("함께 나온 메뉴 쌍", f"{pair_types}쌍")

st.divider()


# -----------------------------
# 연관 규칙 탐색
# -----------------------------
st.subheader("🔍 연관 규칙 탐색")

col1, col2 = st.columns(2)

with col1:

    selected_menu = st.selectbox(
        "메뉴로 좁혀 보기",
        ["전체 메뉴"] + menus,
        key="rule_menu_filter"
    )

with col2:

    sort_option = st.selectbox(
        "정렬 기준",
        ["향상도 순", "신뢰도 순", "동시 순"],
        key="rule_sort"
    )


# -----------------------------
# 최소 동시 일수 슬라이더
# -----------------------------
min_count = st.slider(
    "최소 동시 일수",
    min_value=1,
    max_value=10,
    value=1,
    step=1
)


# -----------------------------
# 규칙 필터링
# -----------------------------
filtered = rules_df.copy()

# 최소 동시 일수 적용
filtered = filtered[
    filtered["동시"] >= min_count
]

# 메뉴 선택 적용
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
# 남은 규칙 개수
# -----------------------------
st.write(
    f"현재 조건에 맞는 규칙은 **{len(filtered):,}개**입니다."
)


# -----------------------------
# 연관 규칙 표
# -----------------------------
st.subheader("📋 메뉴 연관 규칙")

st.caption(
    "조건 메뉴가 나온 날에 결과 메뉴도 함께 나오는 경향을 나타냅니다."
)

if filtered.empty:

    st.warning("조건에 맞는 연관 규칙이 없습니다.")

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


# -----------------------------
# 함께 나온 적 없는 짝
# -----------------------------
st.divider()

st.subheader("🚫 함께 나온 적 없는 짝")

st.write(
    "선택한 메뉴와 같은 날 한 번도 함께 나오지 않았지만, "
    "혼자서는 10일 이상 등장한 메뉴를 찾아봅니다."
)

# 위의 메뉴 필터와 별개인 메뉴 선택
selected_menu_absent = st.selectbox(
    "함께 나온 적 없는 짝을 찾을 메뉴",
    menus,
    key="absent_menu_selector"
)

# 선택한 메뉴가 등장한 일수
selected_menu_days = menu_count[selected_menu_absent]

# 선택한 메뉴와 함께 나온 적이 있는 메뉴들
co_occurring_menus = set()

for (a, b), count in pair_count.items():

    if a == selected_menu_absent:
        co_occurring_menus.add(b)

    elif b == selected_menu_absent:
        co_occurring_menus.add(a)


# 함께 나온 적이 없는 메뉴 찾기
absent_results = []

for menu in menus:

    # 자기 자신은 제외
    if menu == selected_menu_absent:
        continue

    # 함께 나온 적이 있는 메뉴는 제외
    if menu in co_occurring_menus:
        continue

    # 혼자서 10일 이상 나온 메뉴만 선택
    days = menu_count[menu]

    if days >= 10:

        absent_results.append({
            "메뉴": menu,
            "나온 날 수": days
        })


# 등장 횟수가 많은 순으로 정렬
absent_df = pd.DataFrame(absent_results)

if not absent_df.empty:

    absent_df = absent_df.sort_values(
        by=["나온 날 수", "메뉴"],
        ascending=[False, True]
    ).reset_index(drop=True)


# 선택한 메뉴의 등장 횟수 표시
st.metric(
    f"'{selected_menu_absent}'이(가) 나온 날 수",
    f"{selected_menu_days}일"
)

if absent_df.empty:

    st.info(
        "선택한 메뉴와 함께 나온 적이 없는 메뉴 중 "
        "10일 이상 등장한 메뉴가 없습니다."
    )

else:

    st.write(
        f"함께 나온 적 없는 메뉴: **{len(absent_df)}개**"
    )

    st.dataframe(
        absent_df,
        use_container_width=True,
        hide_index=True
    )


# -----------------------------
# 향상도 TOP 10 그래프
# -----------------------------
st.divider()

st.subheader("📈 향상도 TOP 10")

st.write(
    "향상도가 높을수록 두 메뉴가 독립적으로 나올 때보다 "
    "함께 나오는 경향이 강하다는 뜻입니다."
)

if filtered.empty:

    st.info("그래프로 표시할 규칙이 없습니다.")

else:

    top10 = filtered.nlargest(10, "향상도").copy()

    top10["규칙"] = (
        top10["조건"] + " → " + top10["결과"]
    )

    top10 = top10.sort_values(
        "향상도",
        ascending=True
    )

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

    st.plotly_chart(
        fig,
        use_container_width=True
    )


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

    두 메뉴가 독립적으로 등장할 때보다 얼마나 더 자주 함께 나오는지 나타냅니다.

    향상도 = 신뢰도 / 결과 메뉴의 출현 비율

    - 향상도 > 1 : 함께 나오는 경향이 강함
    - 향상도 = 1 : 독립적인 관계
    - 향상도 < 1 : 함께 나오지 않는 경향

    **4. 동시**

    두 메뉴가 같은 급식에 함께 등장한 횟수입니다.

    **5. 함께 나온 적 없는 짝**

    선택한 메뉴와 한 번도 같은 날 나오지 않았지만,
    각각 10일 이상 등장한 메뉴입니다.

    ※ 연관 규칙은 통계적 관계를 나타내며,
    한 메뉴가 다른 메뉴의 출현 원인이라는 뜻은 아닙니다.
    """)
