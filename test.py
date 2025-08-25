import streamlit as st

# 증상 데이터
first_aid_info = {
    "두통": {머리가 아파요, 열이 나요}
        "조치": "조용한 곳에서 휴식을 취하세요. 통증이 심하면 진통제를 복용하세요.",
        "진료과": "신경과"
    },
    "출혈": {피가 나요}
        "조치": "상처 부위를 깨끗이 씻고, 깨끗한 천으로 압박하세요.",
        "진료과": "외과"
    },
    "삠": {발을 삐었어요}
        "조치": "움직이지 말고 냉찜질을 하세요.",
        "진료과": "정형외과"
    },
    "화상": {뜨거운 물에 데었어요}
        "조치": "흐르는 찬물에 10분 이상 식히세요.",
        "진료과": "피부과"
    },
    "코피": {코에서 피가 나요}
        "조치": "고개를 숙이고 코를 5~10분간 압박하세요.",
        "진료과": "이비인후과"
    }
}

st.title("🩺 증상 기반 응급처치 & 진료과 안내")

user_input = st.text_input("어디가 아픈지 또는 어떻게 다쳤는지 입력하세요:")

if user_input:
    found = False
    for keyword, info in first_aid_info.items():
        if keyword in user_input:  # 부분 일치
            st.subheader(f"✅ '{keyword}' 관련 안내")
            st.write(f"👉 응급처치: {info['조치']}")
            st.write(f"🏥 진료과: {info['진료과']}")
            found = True
            break
    if not found:
        st.warning("해당 증상에 맞는 정보가 없습니다. 더 구체적으로 입력해 주세요!")
