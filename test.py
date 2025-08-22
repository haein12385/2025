import streamlit as st
import re
from urllib.parse import quote_plus
from datetime import datetime

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

# 증상/상태 사전: 키워드 매칭 → 우선순위, 응급처치, 진료과
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
        "red_flags": ["휴식해도 지속되는 흉통", "식은땀/구역", "목·턱·왼팔로 퍼지는 통증"]
    },
    {
        "name": "뇌졸중 의심",
        "keywords": ["얼굴 마비", "한쪽 마비", "팔 다리 힘빠짐", "말 어눌", "언어장애", "시야장애", "갑작스런 어지럼", "FAST"],
        "triage": 1,
        "dept": "응급의학과 (뇌신경센터)",
        "first_aid": [
            "즉시 119 (골든타임 4.5시간).",
            "먹거나 마시지 않기, 눕혀서 머리를 약간 올림.",
        ],
        "red_flags": ["갑작스런 한쪽 마비/구음장애/시야장애"]
    },
    {
        "name": "기도폐쇄(교착) / 질식",
        "keywords": ["숨막힘", "질식", "목막힘", "기침 불가", "숨을 못", "목 잡고"],
        "triage": 1,
        "dept": "응급의학과",
        "first_aid": [
            "기침 가능하면 기침 유도. 기침 불가·청색증이면 성인 하임리히법 시행.",
            "영아는 등 두드리기와 흉부 압박 교대로.",
            "이물질 보이면 손가락으로 맹목적 탐색 금지.",
        ],
        "red_flags": ["기침 불가", "청색증", "의식 저하"]
    },
    {
        "name": "중증 알레르기(아나필락시스)",
        "keywords": ["알레르기", "두드러기", "입술 붓기", "혀 붓기", "목 붓기", "호흡곤란", "어지럼", "벌에 쏘임 후", "땅콩", "갑각류"],
        "triage": 1,
        "dept": "응급의학과",
        "first_aid": [
            "즉시 119. 에피네프린 자가주사(있다면) 대퇴 외측에 즉시 투여.",
            "눕히고 다리 올림, 꽉 끼는 옷 풀기.",
        ],
        "red_flags": ["호흡곤란", "삼킴 곤란", "빠른 진행의 붓기"]
    },
    {
        "name": "심한 출혈/깊은 상처",
        "keywords": ["피가 멈추지", "대량 출혈", "지혈 안됨", "깊은 상처", "베였", "절단"],
        "triage": 1,
        "dept": "응급의학과/외상센터",
        "first_aid": [
            "상처 위를 깨끗한 거즈로 강하게 압박 지혈 (10분 이상).",
            "절단이면 깨끗한 거즈로 싸서 비닐봉지→얼음물에 담가 함께 가져가기 (직접 얼음에 닿게 X).",
        ],
        "red_flags": ["분출성 출혈", "지속적 대량 출혈"]
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
        "red_flags": ["심한 변형", "저림/감각저하", "창백/혈류저하"]
    },
    {
        "name": "머리 외상(뇌진탕 포함)",
        "keywords": ["머리 부딪힘", "넘어짐", "의식 잃", "구토", "심한 두통", "기억 안남", "어지럼"],
        "triage": 2,
        "dept": "응급의학과/신경외과",
        "first_aid": [
            "의식·호흡 확인. 의식 저하/반복 구토/경련/한쪽 약화 시 119.",
            "24시간 동반자 관찰 권장. 진통제는 아세트아미노펜 우선 (의사 지시 없이 NSAID는 피함).",
        ],
        "red_flags": ["반복 구토", "의식 저하", "발작", "편측 약화"]
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
        "red_flags": ["얼굴·손·발·사타구니·관절부위", "넓은 면적", "흡입손상 의심"]
    },
    {
        "name": "눈 손상/이물·화학물 노출",
        "keywords": ["눈 아픔", "눈에 이물", "렌즈", "화학물 눈", "눈 빨갛", "시력 흐림"],
        "triage": 2,
        "dept": "안과",
        "first_aid": [
            "렌즈 제거 후 깨끗한 물/식염수로 15–20분 이상 계속 세척.",
            "눈비비기 금지, 보호 안대 후 내원.",
        ],
        "red_flags": ["시력저하", "화학물 접촉", "관통상 의심"]
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
        "red_flags": ["20분 이상 지속", "머리 외상 후 발생", "항응고제 복용"]
    },
    {
        "name": "벌레·동물에 물림/개물림",
        "keywords": ["개물림", "강아지", "고양이", "벌에", "곤충", "두드러기", "통증", "상처"],
        "triage": 3,
        "dept": "응급의학과/외과/피부과",
        "first_aid": [
            "흐르는 물과 비누로 5분 이상 세척, 거즈로 덮기.",
            "동물 교상은 파상풍·광견병 노출 평가 필요.",
        ],
        "red_flags": ["깊은 상처", "얼굴 손상", "알레르기 증상 동반"]
    },
    {
        "name": "열사병/열탈진",
        "keywords": ["더위", "열사병", "탈수", "의식 흐림", "고열", "어지럼", "근육경련"],
        "triage": 2,
        "dept": "응급의학과",
        "first_aid": [
            "그늘/시원한 곳으로 이동, 옷 느슨하게.",
            "시원한 물수건·부채질·수분보충 (의식 저하 시 금식).",
        ],
        "red_flags": ["의식 변화", "체온 40℃ 이상", "경련"]
    },
    {
        "name": "복통/구토·설사 (탈수 위험)",
        "keywords": ["복통", "배 아픔", "구토", "설사", "열", "탈수", "혈변", "검은변"],
        "triage": 3,
        "dept": "내과/소아청소년과",
        "first_aid": [
            "소량씩 자주 수분·전해질 보충, 기름지거나 자극적인 음식 피하기.",
            "혈변/검은변·지속 고열·복막자극 증상 시 응급실.",
        ],
        "red_flags": ["피 섞인 변/구토", "지속 고열", "심한 탈수(어지럼, 소변 감소)"]
    },
    {
        "name": "치아 외상/통증",
        "keywords": ["치아 깨짐", "이 빠짐", "치통", "잇몸 출혈"],
        "triage": 3,
        "dept": "치과",
        "first_aid": [
            "빠진 치아는 우유/생리식염수에 담가 치과로 즉시 이동(치근부 잡지 않기).",
            "출혈은 거즈로 압박.",
        ],
        "red_flags": ["영구치 완전 탈구", "안면골 의심"]
    },
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
    
    개발 메모 ✍️  
    - 키워드 기반 규칙 엔진(오탑재 가능) → 지속 개선 권장  
    - 위치 입력 시 주변 병원 검색 링크 생성
    """)

st.title("🆘 내 증상에 맞는 응급처치와 진료과 안내")
st.caption("입력 예: ‘가슴이 조여오고 왼팔로 통증이 퍼지면서 식은땀이 나요’ · ‘뜨거운 물에 데였고 물집이 생겼어요’ · ‘발목을 접질렀어요’")

col1, col2 = st.columns([2, 1])
with col1:
    text = st.text_area("어디가 아픈가요/어떻게 다쳤나요?", height=160, placeholder="증상, 발생 상황, 동반 증상 등을 적어주세요.")
with col2:
    loc = st.text_input("지역/동네 (선택)", placeholder="예: 서울 강남역, 부산 서면")
    st.write("")
    st.markdown("**오늘 날짜**: " + datetime.now().strftime("%Y-%m-%d %H:%M"))

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
            # 동점 상위 3개까지만 노출
            picks = [c for s, c in results if s == top_score][:3]

            # 최종 권장 triage: 상위 중 가장 높은 긴급도
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
                    st.markdown("**위험 신호 (보이면 즉시 병원)**")
                    st.markdown(", ".join(c["red_flags"]))

            # 병원 검색 링크
            st.subheader("🏥 어디로 가야 하나요?")
            if final_triage == 1:
                base = "응급실"
            elif final_triage == 2:
                base = "응급실 야간진료"
            elif final_triage == 3:
                # 가장 많이 나온 과를 선택
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
        "> ⚡ 증상을 입력하고 ‘분석하기’를 누르면 결과가 표시됩니다. 자주 겪는 상황(골절, 화상, 코피, 알레르기 등)에 대한 응급처치 팁도 함께 제공돼요."
    )
