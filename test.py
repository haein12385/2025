from typing import List, Dict
from rapidfuzz import fuzz

# 증상 데이터
conditions: List[Dict] = [
    {
        "name": "출혈",
        "keywords": ["피", "출혈", "상처", "찢어짐"],
        "first_aid": "출혈 부위를 압박하여 지혈하고, 출혈이 심하면 즉시 응급실로 이동하세요.",
        "department": "응급의학과",
    },
    {
        "name": "골절/염좌",
        "keywords": ["골절", "뼈", "부러짐", "삐끗", "접질림", "부러졌어요", "삐었어요"],
        "first_aid": "환부를 움직이지 않게 고정하고, 얼음찜질을 하며 병원으로 이동하세요.",
        "department": "정형외과",
    },
    {
        "name": "화상",
        "keywords": ["화상", "데임", "뜨거움", "불에탐", "데였어요"],
        "first_aid": "즉시 흐르는 차가운 물에 환부를 10분 이상 식히고, 물집은 터뜨리지 마세요.",
        "department": "외과",
    },
    {
        "name": "두통",
        "keywords": ["두통", "머리 아픔", "머리 아파요", "머리 띵해요"],
        "first_aid": "편안한 곳에서 휴식을 취하고, 증상이 지속되면 진료를 받아야 합니다.",
        "department": "신경과",
    },
    {
        "name": "코피",
        "keywords": ["코피", "코에서 피", "코피나요"],
        "first_aid": "고개를 약간 숙이고 코를 5~10분 정도 눌러주세요.",
        "department": "이비인후과",
    },
]

def score_condition(user_text: str, cond: dict) -> int:
    """
    사용자 입력과 condition 키워드 간의 유사도를 점수화
    """
    score = 0
    for k in cond["keywords"]:
        ratio = fuzz.partial_ratio(k, user_text)
        if ratio >= 70:  # 70% 이상 비슷하면 매칭 인정
            score += 1
    return score

def get_condition(user_text: str) -> Dict:
    """
    입력된 텍스트와 가장 잘 맞는 condition 반환
    """
    best_match = None
    best_score = 0

    for cond in conditions:
        score = score_condition(user_text, cond)
        if score > best_score:
            best_score = score
            best_match = cond

    if best_match and best_score > 0:
        return {
            "증상": best_match["name"],
            "응급처치": best_match["first_aid"],
            "진료과": best_match["department"],
        }
    else:
        return {
            "증상": "알 수 없음",
            "응급처치": "증상이 명확하지 않습니다. 가까운 병원에서 진료를 받으세요.",
            "진료과": "일반의/내과",
        }

# 테스트 예시
if __name__ == "__main__":
    examples = [
        "팔 삐었어요",
        "코에서 피나요",
        "머리가 띵해요",
        "뜨거운 거에 데였어요",
        "피가 납니다",
    ]

    for ex in examples:
        print(f"입력: {ex}")
        print(get_condition(ex))
        print("-" * 40)
