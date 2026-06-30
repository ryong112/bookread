import streamlit as st
from google import genai # 구글 최신 정식 표준 SDK 도입
from gtts import gTTS
from PIL import Image
import io

# ==========================================
# 1. 고성능 구글 AI 엔진 정의
# ==========================================

def extract_and_summarize_with_gemini(image: Image.Image, api_key: str, use_summary: bool) -> tuple[str, str]:
    """
    [최신 구글 AI 표준 엔진]
    구글의 최신 규격인 google-genai API를 사용하여 
    레이아웃 분석 오류(404)를 완벽하게 해결하고 텍스트를 추출합니다.
    """
    if not api_key:
        st.warning("🔑 왼쪽 사이드바에 구글 API 키를 입력해 주세요.")
        return "", ""
        
    try:
        # 최신 SDK 표준 방식으로 클라이언트 객체 생성
        client = genai.Client(api_key=api_key)
        
        prompt = (
            "너는 저시력자와 대학생을 위한 최고의 독서 보조 전문가야. "
            "주어진 이미지에서 모든 한글과 영어 텍스트를 복잡한 레이아웃(단 분할, 번호, 제목 등)에 상관없이 "
            "사람이 실제 책을 읽는 올바른 순서대로 정확하게 추출해줘. "
            "스마트폰 촬영으로 인해 발생한 오타나 깨진 글자가 있다면 앞뒤 문맥을 고려하여 완벽한 한국어 문장으로 자동 교정해줘."
        )
        
        with st.spinner("구글 AI가 책의 문맥과 레이아웃을 정밀 분석하는 중..."):
            # 최신 표준 모델인 'gemini-2.5-flash'와 contents 매개변수 적용
            response = client.models.generate_content(
                model='gemini-2.5-flash',
                contents=[image, prompt]
            )
            extracted_text = response.text
            
        summarized_text = ""
        if use_summary and extracted_text.strip():
            with st.spinner("핵심 요점 요약본을 생성하는 중..."):
                summary_prompt = "다음 본문 내용을 대학생들이 빠르게 복습할 수 있도록 핵심 요점만 일목요연하게 요약해줘."
                summary_response = client.models.generate_content(
                    model='gemini-2.5-flash',
                    contents=[extracted_text, summary_prompt]
                )
                summarized_text = summary_response.text
                
        return extracted_text, summarized_text
        
    except Exception as e:
        st.error(f"구글 AI 연동 중 오류가 발생했습니다: {e}")
        return "", ""

def generate_tts(text: str, lang: str) -> io.BytesIO:
    """[TTS 엔진] 텍스트를 음성 파일로 변환하여 메모리 스트림으로 반환합니다."""
    tts = gTTS(text=text, lang=lang, slow=False)
    fp = io.BytesIO()
    tts.write_to_fp(fp)
    fp.seek(0)
    return fp

# ==========================================
# 2. UI/UX 레이아웃 구성
# ==========================================

st.set_page_config(page_title="보이스북 (VoiceBook)", layout="centered")

st.title("📚 글 읽어주는 보이스북")
st.markdown("### 늦은 나이에 학업을 시작하신 분들을 위한 스마트 독서 보조 도구")

if "scanned_texts" not in st.session_state:
    st.session_state.scanned_texts = []
if "summary_texts" not in st.session_state:
    st.session_state.summary_texts = []

st.sidebar.header("🔑 보안 및 리딩 설정")
google_api_key = st.sidebar.text_input("Google Gemini API Key 입력", type="password", help="가계부 만드실 때 사용했던 AI 키를 넣어주세요.")
lang_option = st.sidebar.selectbox("주요 음성 언어 선택", ["한국어 (ko)", "영어 (en)"])
lang_code = lang_option.split("(")[1].split(")")[0].strip()
use_summary = st.sidebar.checkbox("요약본으로 듣기 (요점만 재생)", value=False)

input_method = st.radio("이미지 가져오기 방식 선택", ["📷 실시간 카메라 촬영", "🖼️ 앨범에서 이미지 불러오기"])

image = None
if input_method == "📷 실시간 카메라 촬영":
    camera_img = st.camera_input("책 페이지를 찍어주세요")
    if camera_img:
        image = Image.open(camera_img)
else:
    uploaded_file = st.file_uploader("앨범에서 책 이미지를 선택하세요", type=["jpg", "jpeg", "png"])
    if uploaded_file:
        image = Image.open(uploaded_file)

# ==========================================
# 3. 핵심 비즈니스 로직 제어
# ==========================================

if image:
    st.image(image, caption="선택된 이미지", width=400)
    
    if st.button("🚀 구글 AI 분석 시작", type="primary"):
        if not google_api_key:
            st.error("❌ 왼쪽 사이드바에 구글 API 키를 먼저 입력해 주셔야 분석이 가능합니다!")
        else:
            raw_txt, sum_txt = extract_and_summarize_with_gemini(image, google_api_key, use_summary)
            
            if raw_txt.strip():
                st.session_state.scanned_texts.append(raw_txt)
                if use_summary:
                    st.session_state.summary_texts.append(sum_txt)
                st.success(f"성공적으로 분석을 완료했습니다! (현재 누적 페이지: {len(st.session_state.scanned_texts)}장)")

if st.session_state.scanned_texts:
    st.divider()
    
    full_text = "\n\n".join(st.session_state.scanned_texts)
    full_summary = "\n\n".join(st.session_state.summary_texts)
    
    final_text_to_read = full_text
    
    if use_summary and full_summary.strip():
        final_text_to_read = full_summary
        st.subheader("💡 구글 AI 요약본 (요점 요약)")
        st.info(final_text_to_read)
    else:
        st.subheader("📋 전체 누적 텍스트")
        with st.expander("원본 전체 텍스트 보기", expanded=True):
            st.write(full_text)
            
# ==========================================
# 기존 app.py 맨 아래의 이 버튼 구역을 아래 코드로 교체하세요
# ==========================================

    if st.button("🔊 음성 파일 생성 및 듣기"):
        with st.spinner("음성을 대본에 맞춰 생성하고 있습니다..."):
            
            # [수정 포인트 1] gTTS가 '별표'라고 읽지 않도록 강조 기호(**)를 먼저 싹 제거합니다.
            clean_text_to_read = final_text_to_read.replace("*", "")
            
            # 깨끗해진 텍스트로 음성 파일 생성
            audio_data = generate_tts(clean_text_to_read, lang=lang_code)
            
            # 화면에 오디오 플레이어 송출
            st.audio(audio_data, format="audio/mp3")
            st.success("재생 버튼을 누르면 오디오가 시작됩니다. 플레이어 내 우측 설정(⋮)에서 속도 조절이 가능합니다.")
            
            # [수정 포인트 2] 아이폰/안드로이드에서 터치 한 번으로 다운로드할 수 있는 전용 버튼을 배치합니다.
            st.download_button(
                label="📥 스마트폰에 음성 파일(.mp3) 저장하기",
                data=audio_data,
                file_name="voicebook_audio.mp3",
                mime="audio/mp3",
                use_container_width=True # 버튼을 화면 너비에 맞게 큼직하게 키웁니다.
            )

    if st.button("🗑️ 전체 비우기 및 새로 시작"):
        st.session_state.scanned_texts = []
        st.session_state.summary_texts = []
        st.rerun()