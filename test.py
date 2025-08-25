# -*- coding: utf-8 -*-
"""
응급처치 & 진료과 안내 스트림릿 앱

기능 요약
- 사용자가 자유롭게 증상/사고 상황을 입력하면 의미 유사도 기반으로 가장 유사한 항목을 찾아
  1) 즉시 해야 할 응급처치 단계
  2) 권장 내원 진료과/기관
  3) 119 연락 권고 기준(레드 플래그)
  를 보여줍니다.

- 의미 유사도: SentenceTransformer(권장) -> 실패 시 TF-IDF 코사인 유사도 대체
- 한국 로컬 용어(119, 진료과명) 적용
- 절대적 의학적 조언이 아니며, 긴급/중증 의심 시 즉시 119 연락 및 응급실 방문 안내

실행
  $ pip install streamlit scikit-learn sentence-transformers torch
  $ streamlit run app.py

메모
- 배포 환경에서 sentence-transformers 설치가 어렵다면 사이드바에서 "간단 매칭(TF-IDF)"로 바꿔 사용하세요.
- 필요 시 knowledge_base 항목을 자유롭게 추가/수정하세요.
"""

import os
import re
import json
from typing import List, Dict, Any

import streamlit as st
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

# ===== 시맨틱 임베딩 로딩 (선택) =====
_ST_MODEL = None
_ST_AVAILABLE = False

@st.cache_resource(show_spinner=False)
def load_st_model(model_name: str = "sentence-transformers/paraphrase-MiniLM-L6-v2"):
    global _ST_MODEL, _ST_AVAILABLE
    try:
        from sentence_transformers import SentenceTransformer
        _ST_MODEL = SentenceTransformer(model_name)
        _ST_AVAILABLE = True
    except Exception as e:
        _ST_MODEL = None
        _ST_AVAILABLE = False
    return _ST_MODEL, _ST_AVAILABLE

# ===== 지식 베이스 =====
# label: 대표 명칭, keywords: 유사 표현들, dept: 권장 진료과/기관, aid: 응급처치 단계, red_flags: 즉시 119 기준
knowledge_base: List[Dict[str, Any]] = [
    {
        "label": "심정지/의식 없음",
        "keywords": ["의식이 없다", "반응이 없다", "심장 멈춤", "맥박 없음", "숨을 안 쉰다", "심정지"],
        "dept": "즉시 119 / 응급실(응급의학과)",
        "aid": [
            "119에 즉시 신고(스피커폰). AED가 있으면 가져오도록 요청.",
            "호흡/맥박 확인(10초 이내). 비정상 호흡 또는 무호흡이면 CPR 시작.",
            "가슴압박: 분당 100~120회, 깊이 5~6cm, 완전 이완 유지.",
            "AED 도착 시 음성 지시에 따라 패드 부착 및 제세동.",
        ],
        "red_flags": ["의식 없음", "무호흡", "심정지", "맥박 없음"],
    },
    {
        "label": "질식/기도막힘",
        "keywords": ["목에 걸림", "숨 막힘", "질식", "이물질", "기침 안됨", "하임리히"],
        "dept": "즉시 119 / 응급실",
        "aid": [
            "기침 가능하면 계속 기침하도록 격려.",
            "기침/소리 불가·청색증이면 성인/소아 하임리히법(복부 밀어올리기) 시행.",
            "영아(1세 미만): 등 두드리기 5회 + 가슴압박 5회 반복.",
            "의식 소실 시 CPR 및 119 신고.",
        ],
        "red_flags": ["숨 못쉼", "청색증", "기침 불가"],
    },
    {
        "label": "심근경색 의심(가슴 통증)",
        "keywords": ["가슴통증", "가슴이 조인다", "왼팔 저림", "식은땀", "압박감", "숨참"],
        "dept": "즉시 119 / 응급실(심장혈관센터 가능 시)",
        "aid": [
            "안정 자세, 꽉 끼는 옷 풀기.",
            "아스피린 알약(성인 300mg 내외)을 알레르기/금기 없을 때 씹어 삼키는 것을 고려(확실하지 않으면 복용 X).",
            "절대 혼자 운전 금지. 즉시 119 호출.",
        ],
        "red_flags": ["휴식해도 지속되는 가슴통증", "호흡곤란", "식은땀"],
    },
    {
        "label": "뇌졸중 의심(FAST)",
        "keywords": ["갑자기 마비", "말 어눌", "한쪽 저림", "안면마비", "시야장애", "어지럼 심함"],
        "dept": "즉시 119 / 뇌졸중 센터 있는 병원 응급실",
        "aid": [
            "FAST 확인(얼굴 처짐, 팔 들기 어려움, 말 어눌).",
            "증상 시작 시각 기록, 음식/음료 금지.",
            "즉시 119 호출, 혼자 이동 금지.",
        ],
        "red_flags": ["갑작스런 신경학적 결손", "의식 저하"],
    },
    {
        "label": "대량출혈/지혈",
        "keywords": ["피가 멈추지 않음", "대량 출혈", "칼에 베임", "동맥 출혈", "피철철"],
        "dept": "즉시 119 / 응급실",
        "aid": [
            "깨끗한 거즈/천으로 상처 부위를 강하게 직접 압박.",
            "지혈대는 마지막 수단(사용법 숙지 시).",
            "쇼크 예방: 눕히고 다리 약간 올리기(머리·척추 손상 의심 시 제외).",
        ],
        "red_flags": ["분출성 출혈", "지속적 대량 출혈", "쇼크 소견"],
    },
    {
        "label": "골절/염좌",
        "keywords": ["부러짐", "삐끗", "발목 접질림", "통증으로 체중 부하 불가", "붓기", "멍"],
        "dept": "정형외과(중증 외상·개방창은 응급실)",
        "aid": [
            "RICE: 휴식(Rest), 냉찜질(Ice, 20분 이내), 압박(Compression), 거상(Elevation).",
            "심한 변형/개방창/감각저하 시 고정 후 응급실.",
        ],
        "red_flags": ["심한 변형", "감각/혈류 저하", "개방성 골절"],
    },
    {
        "label": "화상",
        "keywords": ["데임", "뜨거운 물", "기름에 데임", "화상", "물집"],
        "dept": "경미: 피부과/외과 | 광범위/3도 의심: 응급실/화상센터",
        "aid": [
            "즉시 미지근한 흐르는 물로 20분 이상 냉각(얼음 직접 대지 않기).",
            "금속/의복이 붙었으면 억지로 떼지 말고 의료기관 이동.",
            "물집은 터뜨리지 않기, 멸균 거즈로 보호.",
        ],
        "red_flags": ["얼굴/회음부/손·발/관절부 심한 화상", "광범위 수포", "흡입 손상 의심"],
    },
    {
        "label": "코피",
        "keywords": ["코피", "비출혈", "코에서 피", "코피 멈추지 않음"],
        "dept": "이비인후과(지속 출혈은 응급실)",
        "aid": [
            "몸을 약간 숙이고 콧망울을 10분 이상 지속 압박.",
            "목 뒤 얼음찜질은 보조, 면봉·휴지 깊숙이 넣지 않기.",
        ],
        "red_flags": ["15분 이상 지속 출혈", "탈수/어지럼 동반"],
    },
    {
        "label": "눈 이물/화학손상",
        "keywords": ["눈에 이물", "눈 아픔", "화학물질 튐", "콘택트렌즈", "시력 흐림"],
        "dept": "안과(화학 손상은 응급실 우선)",
        "aid": [
            "깨끗한 수돗물/생리식염수로 15분 이상 지속 세척.",
            "비비지 말기, 콘택트렌즈 제거.",
        ],
        "red_flags": ["화학물질 노출", "시력 급격 저하", "심한 통증"],
    },
    {
        "label": "벌/곤충 쏘임",
        "keywords": ["벌에 쏘임", "모기", "벌침", "곤충", "알레르기"],
        "dept": "피부과/알레르기내과(전신 반응은 응급실)",
        "aid": [
            "냉찜질, 물로 세척, 가려움 완화 연고 사용 고려.",
            "벌침이 보이면 조심히 제거(핀셋보다 긁어내기).",
        ],
        "red_flags": ["호흡곤란", "입술/눈 주변 부종", "전신 두드러기"],
    },
    {
        "label": "개/동물 교상",
        "keywords": ["개에 물림", "고양이에게 물림", "동물에게 물림", "교상", "광견병"],
        "dept": "응급실/외과(필요 시 예방접종실/보건소 안내)",
        "aid": [
            "흐르는 물과 비누로 5분 이상 세척, 멸균 거즈로 덮기.",
            "상처 깊으면 지연 봉합 고려, 파상풍/광견병 예방접종 평가.",
        ],
        "red_flags": ["깊은 관통상", "발열·농 배출", "안면/손 부위"],
    },
    {
        "label": "복통(일반)",
        "keywords": ["배 아픔", "속이 뒤틀림", "명치통증", "설사 복통"],
        "dept": "내과/소화기내과(급성 심하면 응급실)",
        "aid": [
            "금식, 미지근한 물 소량씩, 증상/동반 증상 기록.",
            "지속·악화 시 의료기관 방문.",
        ],
        "red_flags": ["피 섞인 변/토혈", "고열/탈수", "임산부의 복통"],
    },
    {
        "label": "발작/간질 의심",
        "keywords": ["경련", "발작", "거품", "의식 잃음", "간질"],
        "dept": "응급실/신경과",
        "aid": [
            "주변 위험물 치우고 머리 보호, 억지로 붙잡거나 물건 물리지 말기.",
            "발작 후 기도 확보를 위해 옆으로 눕히기(회복자세).",
        ],
        "red_flags": ["5분 이상 지속", "연속 발작", "첫 발작"],
    },
    {
        "label": "과호흡/공황 의심",
        "keywords": ["과호흡", "숨 가쁨", "손발 저림", "불안", "공황"],
        "dept": "정신건강의학과/내과",
        "aid": [
            "천천히 코로 들이마시고 입으로 내쉬는 호흡 유도(4-7-8 호흡 등).",
            "안심시키고 자극 줄이기.",
        ],
        "red_flags": ["의식 저하", "가슴통증 동반", "호흡 곤란 악화"],
    },
]

# 레드 플래그 키워드(입력 문장에서 발견되면 최우선 경고)
CRITICAL_TRIGGERS = [
    "의식 없음", "반응 없음", "숨 못", "호흡 곤란", "숨 쉬기 힘듦", "피 철철", "피 멈추지", "심장", "가슴 통증",
    "마비", "말 어눌", "청색", "경련", "질식", "중독", "화학물질", "심한 통증"
]

# ===== 유틸 =====

def normalize(txt: str) -> str:
    txt = txt.lower().strip()
    txt = re.sub(r"\s+", " ", txt)
    return txt

@st.cache_data(show_spinner=False)
def build_tfidf_corpus(items: List[Dict[str, Any]]):
    docs = []
    for it in items:
        docs.append(it["label"] + " " + " ".join(it.get("keywords", [])))
    vec = TfidfVectorizer(ngram_range=(1,2), min_df=1)
    X = vec.fit_transform(docs)
    return vec, X

@st.cache_resource(show_spinner=False)
def build_semantic_corpus(items: List[Dict[str, Any]]):
    model, ok = load_st_model()
    if not ok:
        return None, None, False
    docs = []
    for it in items:
        docs.append(it["label"] + " " + " ".join(it.get("keywords", [])))
    emb = model.encode(docs, normalize_embeddings=True)
    return model, emb, True


def rank_with_semantic(query: str, items: List[Dict[str, Any]], topk: int = 3):
    model, emb, ok = build_semantic_corpus(items)
    if not ok:
        return []
    qv = model.encode([query], normalize_embeddings=True)
    sims = (qv @ emb.T).ravel()
    idx = sims.argsort()[::-1][:topk]
    results = [(int(i), float(sims[i])) for i in idx]
    return results


def rank_with_tfidf(query: str, items: List[Dict[str, Any]], topk: int = 3):
    vec, X = build_tfidf_corpus(items)
    q = vec.transform([query])
    sims = cosine_similarity(q, X).ravel()
    idx = sims.argsort()[::-1][:topk]
    results = [(int(i), float(sims[i])) for i in idx]
    return results


def detect_critical(query: str) -> List[str]:
    hits = []
    q = normalize(query)
    for kw in CRITICAL_TRIGGERS:
        if kw in q:
            hits.append(kw)
    return hits

# ===== UI =====
st.set_page_config(page_title="응급처치 & 진료과 안내", page_icon="🆘", layout="wide")

st.title("🆘 증상 입력만 하면 알려주는 응급처치 & 진료과 안내")

with st.expander("❗️중요 고지", expanded=True):
    st.markdown(
        """
        - 이 도구는 **응급처치 참고용**입니다. 정확한 진단을 대신하지 않습니다.
        - **심각한 증상**(의식 소실, 호흡 곤란, 대량 출혈, 심한 가슴 통증 등)은 **즉시 119**에 연락하세요.
        - 입력한 내용은 로컬에서만 처리되며, 서버로 전송되지 않습니다(배포 방식에 따라 달라질 수 있음).
        """
    )

col1, col2 = st.columns([2, 1])

with col2:
    st.subheader("⚙️ 매칭 설정")
    match_mode = st.radio(
        "매칭 방식 선택",
        ["고급 의미 유사도(권장)", "간단 매칭(TF-IDF)"],
        index=0
    )
    topk = st.slider("결과 개수", 1, 5, 3)
    st.caption("*설치 환경에 따라 의미 유사도 모델이 자동으로 TF-IDF로 대체될 수 있습니다.")

with col1:
    st.subheader("📝 증상/상황을 자유롭게 적어주세요")
    examples = st.pills("예시"
