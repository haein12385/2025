import streamlit as st
import pandas as pd
from itertools import product

st.set_page_config(
    page_title="🌈💖✨ MBTI 궁합 추천기 ✨💖🌈",
    page_icon="💞",
    layout="centered",
)

st.title("🌟💘 MBTI 궁합 추천기 💘🌟")
st.caption("🌸 이 앱은 가볍게 즐기는 재미용! 다양한 이론 중 하나를 반영해 귀엽게 추천해드려요 💫✨")

ALL_TYPES = [
    "INTJ", "INTP", "ENTJ", "ENTP",
    "INFJ", "INFP", "ENFJ", "ENFP",
    "ISTJ", "ISFJ", "ESTJ", "ESFJ",
    "ISTP", "ISFP", "ESTP", "ESFP",
]

GOLDEN_PAIRS = {
    ("ENFP", "INTJ"), ("INTJ", "ENFP"),
    ("ENTP", "INFJ"), ("INFJ", "ENTP"),
    ("INFP", "ENFJ"), ("ENFJ", "INFP"),
    ("INTP", "ENTJ"), ("ENTJ", "INTP"),
    ("ISFP", "ESTJ"), ("ESTJ", "ISFP"),
    ("ISTP", "ESFJ"), ("ESFJ", "ISTP"),
    ("ISFJ", "ESTP"), ("ESTP", "ISFJ"),
    ("ESFP", "ISTJ"), ("ISTJ", "ESFP"),
}

LETTER_INDEX = {"I":0, "E":0, "N":1, "S":1, "T":2, "F":2, "J":3, "P":3}

@st.cache_data
def calc_score(a: str, b: str):
    score = 0
    reasons = []

    if a[1] == b[1]:
        score += 2
        reasons.append("🔮 N/S가 같아 사고의 틀이 유사해요 (+2)")

    if (a[2] == 'T' and b[2] == 'F') or (a[2] == 'F' and b[2] == 'T'):
        score += 1
        reasons.append("⚖️ T/F가 보완되어 결정이 균형적이에요 (+1)")

    if (a[3] == 'J' and b[3] == 'P') or (a[3] == 'P' and b[3] == 'J'):
        score += 1
        reasons.append("🌀 J/P가 보완되어 생활 리듬이 균형적이에요 (+1)")

    if (a[0] == 'E' and b[0] == 'I') or (a[0] == 'I' and b[0] == 'E'):
        score += 1
        reasons.append("🌞/🌙 E/I가 보완되어 에너지 균형이 좋아요 (+1)")

    if (a, b) in GOLDEN_PAIRS:
        score += 2
        reasons.append("💎✨ 자주 거론되는 궁합 조합이에요 (+2)")

    if a == b:
        score += 0.5
        reasons.append("🌸 같은 유형이라 공감대가 커요 (+0.5)")

    max_possible = 6.5
    norm = round(score / max_possible * 100, 1)
    return score, norm, reasons

with st.sidebar:
    st.header("⚙️🌟 설정 🌟⚙️")
    your = st.selectbox("💖 나의 MBTI를 선택하세요 💖", ALL_TYPES, index=ALL_TYPES.index("ENFP") if "ENFP" in ALL_TYPES else 0)
    top_k = st.slider("✨ 추천 개수 ✨", 1, 10, 5)
    show_all = st.toggle("📜 전체 순위표 보기", value=False)

st.subheader("🔮💫✨ 추천 결과 ✨💫🔮")

rows = []
for t in ALL_TYPES:
    s, norm, reasons = calc_score(your, t)
    rows.append({
        "상대 MBTI": t,
        "점수(원점수)": round(s,2),
        "적합도(%)": norm,
        "이유": " · ".join(reasons) if reasons else "—",
    })

df = pd.DataFrame(rows).sort_values(["점수(원점수)", "적합도(%)"], ascending=False).reset_index(drop=True)

best = df.head(top_k)
for i, r in best.iterrows():
    with st.container(border=True):
        st.markdown(f"## 🧩💖 {r['상대 MBTI']} · 🌈 적합도 {r['적합도(%)']}% 💖🧩")
        st.progress(min(int(r['적합도(%)']), 100))
        with st.expander("✨🔍 이 궁합을 이렇게 본 이유 🔍✨"):
            st.write(r["이유"]) 

if show_all:
    st.divider()
    st.subheader("📊🌟 전체 순위표 🌟📊")
    st.dataframe(df, use_container_width=True)

st.divider()
st.markdown(
    """
    ⚠️ **주의/면책** ⚠️  
    본 앱은 과학적 진단 도구가 아니라, 🌸 **재미로 보는 가벼운 추천** 🌸 을 제공합니다! ✨  
    관계는 MBTI뿐 아니라 💕 가치관, 🌍 소통 방식, 🎶 삶의 맥락 등 다양한 요소로 만들어져요 🌟.
    """
)

st.caption("👉 좌측 사이드바에서 ✨ MBTI와 옵션을 바꿔가며 💕 다양한 조합을 확인해보세요! 🌈")
