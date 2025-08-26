import streamlit as st  # Streamlit 웹 앱 라이브러리
import re  # 문자열 정규표현식 처리
from urllib.parse import quote_plus  # URL 인코딩
from datetime import datetime  # 날짜/시간 처리
# -----------------------------
# Page config
# -----------------------------
st.set_page_config(
    page_title="응급처치 · 진료안내 도우미",
    page_icon="🩹",
    layout="wide"
)

# -----------------------------
# Helper data
# -----------------------------
TRIAGE_INFO = {
    1: {"label": "🚨 즉시 119 (혹은 응급실로 이동)", "color": "#ef4444"},
    2: {"label": "⚠️ 오늘 중 응급실/야간진료 권장", "color": "#f59e0b"},
    3: {"label": "⏱ 24–48시간 내 외래 방문 권장", "color": "#0ea5e9"},
    4: {"label": "✅ 자가 처치 우선 + 경과 관찰", "color": "#22c55e"},
}

# 증상/상태 사전: 키워드 매칭 → 우선순위, 응급처치, 진료과, 간단한 응급처치 팁
CONDITIONS = [
    {
        "name": "심근허혈/심근경색 의심 (가슴통증)",
        "keywords": ["가슴통증", "흉통", "가슴 아픔", "압박감", "식은땀", "숨참", "호흡곤란", "왼팔", "어깨", "턱 통증"],
        "triage": 1,
        "dept": "응급의학과 (응급실)",
        "first_aid": [
            "즉시 119에 전화하거나 가까운 응급실로 이동합니다.",
            "편안한 자세로 안정, 꽉 끼는 옷 풀기.",
            "아스피린 복용 이력이 있고 의사가 금기하지 않았다면 300mg 한 번 씹어 삼키는 것을 고려 (알레르기/위장관 출혈 병력 있으면 금지).",
        ],
        "simple_tip": "편안히 눕히고 옷을 느슨하게 하여 숨쉬기 편하게 해주세요.",
        "red_flags": ["휴식해도 지속되는 흉통", "식은땀/구역", "목·턱·왼팔로 퍼지는 통증"]
    },
    {
        "name": "골절/염좌 의심",
        "keywords": ["부러짐", "골절", "딱 소리", "붓기", "멍", "발목 접질림", "손목", "통증 심함", "체중 부하 불가"],
        "triage": 3,
        "dept": "정형외과",
        "first_aid": [
            "RICE: 휴식(Rest)·냉찜질(Ice 20분 이내)·압박(Compression)·거상(Elevation).",
            "심한 변형/저림·창백 있으면 부목 고정 후 응급실.",
        ],
        "simple_tip": "수건에 싸서 냉찜질하고, 아픈 부위는 움직이지 않게 고정하세요.",
        "red_flags": ["심한 변형", "저림/감각저하", "창백/혈류저하"]
    },
    {
        "name": "코피",
        "keywords": ["코피", "비출혈"],
        "triage": 4,
        "dept": "이비인후과",
        "first_aid": [
            "앞으로 약간 숙이고 콧망울을 10분간 지속 압박.",
            "목 뒤 얼음찜질, 피는 삼키지 않기.",
        ],
        "simple_tip": "고개를 앞으로 숙이고 콧망울을 손가락으로 10분간 꾹 누르세요.",
        "red_flags": ["20분 이상 지속", "머리 외상 후 발생", "항응고제 복용"]
    },
  {
    "name": "벌 쏘임",
    "keywords": ["벌에 쏘임", "벌침", "벌에 물림", "벌한테 쏘임"],
    "triage": 3,
    "dept": "피부과 / 응급의학과",
    "first_aid": [
        "벌침이 남아있으면 카드 같은 납작한 물체로 피부를 긁어내듯 제거.",
        "상처 부위를 비누와 물로 깨끗이 씻기.",
        "얼음찜질로 통증과 부기를 줄이기.",
        "호흡곤란, 전신 발진, 어지럼증 같은 알레르기 반응(아나필락시스) 증상이 나타나면 즉시 119 신고 및 응급실 내원."
    ]
},
    {
        "name": "화상 (열/화학/전기)",
        "keywords": ["화상", "데임", "뜨거운 물", "불에", "전기쇼크", "화학물질"],
        "triage": 2,
        "dept": "응급의학과/성형외과/피부과",
        "first_aid": [
            "즉시 흐르는 미지근한 물에 20분 이상 냉각 (얼음 금지).",
            "물집은 터뜨리지 말고 깨끗하게 덮기. 화학물은 최소 20분 이상 물로 씻어내기.",
            "전기화상은 겉이 약해 보여도 반드시 병원 평가.",
        ],
        "simple_tip": "얼음 대신 흐르는 시원한 물에 20분 이상 식히세요.",
        "red_flags": ["얼굴·손·발·사타구니·관절부위", "넓은 면적", "흡입손상 의심"]
    }
]

EMERGENCY_BONUS_WORDS = ["의식 저하", "경련", "호흡곤란", "피가 멈추지", "대량", "청색", "마비", "심한 흉통"]

# -----------------------------
# Matching logic
# -----------------------------
def normalize(txt: str) -> str:
    return re.sub(r"\s+", " ", txt.strip())


def score_condition(user_text: str, cond: dict) -> int:
    text = user_text
    return sum(1 for k in cond["keywords"] if k in text)


def analyze(user_text: str):
    user_text = normalize(user_text)
    results = []
    for cond in CONDITIONS:
        s = score_condition(user_text, cond)
        if s > 0:
            results.append((s, cond))
    # Emergency bonus
    emergency_hit = any(w in user_text for w in EMERGENCY_BONUS_WORDS)
    results.sort(key=lambda x: (-x[0], x[1]["triage"]))
    return results, emergency_hit


# -----------------------------
# UI
# -----------------------------
with st.sidebar:
    st.markdown("""
    # 🩹 응급처치 · 진료안내 도우미
    
    증상이나 다친 부위를 적으면 **우선 해야 할 응급처치**와 **권장 진료과/이동 여부**를 안내해요.
    
    **중요 고지**
    - 본 앱은 학습/참고용 정보입니다. 실제 진료를 대체하지 않아요.
    - **심한 통증, 호흡곤란, 의식 변화** 등 위험 신호가 보이면 즉시 **119**에 연락하세요.
    """)

# 메인 화면 제목/캡션
st.title("🆘 내 증상에 맞는 응급처치와 진료과 안내")
st.caption("입력 예: ‘가슴이 조여오고 왼팔로 통증이 퍼지면서 식은땀이 나요’ · ‘뜨거운 물에 데였고 물집이 생겼어요’ · ‘발목을 접질렀어요’")

#사용자 입력 영
col1, col2 = st.columns([2, 1])
with col1:
    text = st.text_area("어디가 아픈가요/어떻게 다쳤나요?", height=160, placeholder="증상, 발생 상황, 동반 증상 등을 적어주세요.")
with col2:
    loc = st.text_input("지역/동네 (선택)", placeholder="예: 서울 강남역, 부산 서면")
    st.write("")
    st.markdown("**오늘 날짜**: " + datetime.now().strftime("%Y-%m-%d %H:%M"))

# 분석 버튼
run = st.button("🔎 분석하기")

if run:
    if not text.strip():
        st.warning("증상을 먼저 입력해 주세요.")
    else:
        results, emergency_hit = analyze(text)
        if not results:
            st.info("명확한 매칭이 없어요. 그래도 위험 신호가 있으면 119에 연락하세요. 증상을 조금 더 구체적으로 적어주세요.")
        else:
            top_score = results[0][0]
            picks = [c for s, c in results if s == top_score][:3]

            final_triage = min(c["triage"] for c in picks)
            if emergency_hit and final_triage > 1:
                final_triage = 1

            tri = TRIAGE_INFO[final_triage]
            st.markdown(f"""
            <div style='padding:14px;border-radius:14px;border:2px solid {tri['color']};'>
                <div style='font-size:1.1rem'>우선순위</div>
                <div style='font-weight:700;color:{tri['color']};font-size:1.3rem'>{tri['label']}</div>
            </div>
            """, unsafe_allow_html=True)

            st.subheader("🔍 가능한 원인(추정)")
            for c in picks:
                with st.expander(f"{c['name']} · 권장: {c['dept']} · 우선순위: {TRIAGE_INFO[c['triage']]['label']}"):
                    st.markdown("**응급처치 가이드**")
                    for step in c["first_aid"]:
                        st.markdown(f"- {step}")
                    if "simple_tip" in c:
                        st.markdown("**👉 내가 할 수 있는 간단한 응급처치**")
                        st.info(c["simple_tip"])
                    st.markdown("**위험 신호 (보이면 즉시 병원)**")
                    st.markdown(", ".join(c["red_flags"]))

            # 진료과/장소 안내
            st.subheader("🏥 어디로 가야 하나요?")
            if final_triage == 1:
                base = "응급실"
            elif final_triage == 2:
                base = "응급실 야간진료"
            elif final_triage == 3:
                depts = {}
                for c in picks:
                    depts[c["dept"]] = depts.get(c["dept"], 0) + 1
                base = max(depts, key=depts.get)
            else:
                base = picks[0]["dept"]

            query = base if not loc.strip() else f"{loc} {base}"
            naver = f"https://map.naver.com/p/search/{quote_plus(query)}"
            kakao = f"https://map.kakao.com/?q={quote_plus(query)}"
            google = f"https://www.google.com/maps/search/{quote_plus(query)}"
            st.markdown(
                f"[🧭 네이버지도에서 검색하기]({naver}) · [🗺 카카오맵에서 검색하기]({kakao}) · [🌎 구글지도에서 검색하기]({google})"
            )

            st.divider()
            st.markdown("""
            ### ℹ️ 참고 안내
            - 이 도구는 **전문의 진단을 대체하지 않습니다**. 
            - 약 복용, 알레르기, 지병이 있다면 반드시 의료진에게 알리세요.
            - 아동/임신부/고령자는 동일 증상이라도 **더 낮은 역치로 병원 방문**이 필요합니다.
            """)
else:
    st.markdown(
        "> ⚡ 증상을 입력하고 ‘분석하기’를 누르면 결과가 표시됩니다. 자주 겪는 상황(골절, 화상, 코피 등)에 대한 응급처치 팁도 함께 제공돼요."
    )
