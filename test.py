import streamlit as st
import json
import os
from stt_engine import STTEngine
from llm_engine import LLMEngine
from tts_engine import TTSEngine

# --- 1. 배리어프리 고대비 CSS 설정 ---
def apply_accessible_style():
    st.markdown("""
        <style>
        /* 검정 배경, 형광 노랑 글씨로 시인성 극대화 */
        .stApp { background-color: #000000; color: #FFFF00; }
        
        /* 중앙 안내 문구 */
        .guide-text { 
            font-size: 4rem !important; font-weight: bold; text-align: center; 
            margin-top: 50px; color: #FFFF00;
        }
        
        /* 마이크 섹션 커스텀 */
        div[data-testid="stAudioInput"] {
            border: 5px solid #FFFF00 !important;
            border-radius: 50px !important;
            padding: 20px !important;
            background-color: #222 !important;
        }

        /* 하단 실시간 정보 카드 */
        .info-container {
            display: flex; justify-content: space-around;
            background-color: #1a1a1a; border: 3px solid #FFFF00;
            border-radius: 30px; padding: 30px; margin-top: 50px;
        }
        .info-box { text-align: center; }
        .info-label { font-size: 1.5rem; color: #FFFFFF; margin-bottom: 10px; }
        .info-value { font-size: 2.5rem; font-weight: bold; color: #FFFF00; }
        </style>
    """, unsafe_allow_html=True)

# --- 2. 엔진 로드 및 초기화 ---
@st.cache_resource
def load_engines():
    return STTEngine(), LLMEngine(), TTSEngine()

stt, llm, tts = load_engines()

def main():
    apply_accessible_style()

    # 세션 상태 초기화 (정보 저장용)
    if 'ticket' not in st.session_state:
        st.session_state.ticket = {"출발지": "-", "도착지": "-", "시간": "-", "인원": "-"}
    if 'initialized' not in st.session_state:
        st.session_state.initialized = False

    # --- 3. 첫 접속 시 안내 음성 송출 ---
    if not st.session_state.initialized:
        intro_text = "반갑습니다. 말로 하는 대화형 키오스크 말표입니다. 화면 가운데 마이크를 누르고 목적지를 말씀해 주세요."
        intro_audio = tts.speak(intro_text, "intro.mp3")
        st.audio(intro_audio, autoplay=True)
        st.session_state.initialized = True

    # --- 4. 중앙 UI (가이드 & 마이크) ---
    st.markdown("<div class='guide-text'>무엇을 도와드릴까요?</div>", unsafe_allow_html=True)
    st.write("") # 간격 조절
    
    # Streamlit 기본 마이크 입력을 중앙 배치
    audio_value = st.audio_input("마이크 버튼을 눌러 말씀하세요")

    # --- 5. 음성 인식 및 정보 업데이트 로직 ---
    if audio_value:
        with open("temp_input.wav", "wb") as f:
            f.write(audio_value.read())
        
        with st.spinner("어르신 말씀을 이해하는 중입니다..."):
            # STT 수행
            user_text = stt.transcribe("temp_input.wav")
            
            # LLM 수행 (JSON 추출)
            intent_json = llm.extract_info(user_text)
            try:
                new_data = json.loads(intent_json)
                # 기존 정보 유지하며 새 정보 업데이트
                for key in st.session_state.ticket.keys():
                    if new_data.get(key) and new_data.get(key) != "-":
                        st.session_state.ticket[key] = new_data.get(key)
                
                # 분석 결과 피드백 TTS
                reply = f"{st.session_state.ticket['도착지']} 가는 표를 찾으시는군요."
                reply_audio = tts.speak(reply, "reply.mp3")
                st.audio(reply_audio, autoplay=True)
            except:
                st.error("잘 이해하지 못했어요. 다시 한 번 말씀해 주시겠어요?")

    # --- 6. 하단 실시간 정보 대시보드 ---
    t = st.session_state.ticket
    st.markdown(f"""
        <div class='info-container'>
            <div class='info-box'>
                <div class='info-label'>출발지</div>
                <div class='info-value'>{t['출발지']}</div>
            </div>
            <div class='info-box'>
                <div class='info-label'>도착지</div>
                <div class='info-value'>{t['도착지']}</div>
            </div>
            <div class='info-box'>
                <div class='info-label'>시간</div>
                <div class='info-value'>{t['시간']}</div>
            </div>
            <div class='info-box'>
                <div class='info-label'>인원</div>
                <div class='info-value'>{t['인원']}</div>
            </div>
        </div>
    """, unsafe_allow_html=True)

    # 하단 예매 확정 버튼 (정보가 다 찼을 때만 강조)
    if "-" not in t.values():
        if st.button("이대로 예매하기", type="primary", use_container_width=True):
            st.balloons()
            st.success("예매가 완료되었습니다!")

if __name__ == "__main__":
    main()