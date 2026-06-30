import streamlit as st
import pytesseract
from gtts import gTTS
from PIL import Image
import io

# ==========================================
# 1. 초기 설정 및 모듈화된 엔진 정의
# ==========================================

def extract_text_from_image(image: Image.Image) -> str:
    """[OCR 엔진] Tesseract를 사용하여 이미지에서 한글과 영어를 추출합니다."""
    try:
        # 한글(kor)과 영어(eng)를 동시에 인식하도록 설정
        config = '--oem 3 --psm 6'
        text = pytesseract.image_to_string(image, lang='kor+eng', config=config)
        return text
    except Exception as e:
        st.error(f"OCR 엔진 오류: {e}")
        return ""

def summarize_text(text: str, ratio: float = 0.5) -> str:
    """[요약 엔진] 입력된 텍스트를 문장 단위로 분할하여 핵심 요점을 추출합니다."""
    if not text.strip():
        return ""
    
    sentences = [s.strip() for s in text.split('.') if s.strip()]
    if len(sentences) <= 2:
        return text
        
    summary_count = max(1, int(len(sentences) * ratio))
    summarized_sentences = sentences[:summary_count]
    return ". ".join(summarized_sentences) + "."

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
    
    if st.button("📝 글자 인식 시작", type="primary"):
        with st.spinner("글자를 분석하는 중입니다. 잠시만 기다려주세요..."):
            # 정교하게 수정된 경량 OCR 엔진 호출
            extracted_text = extract_text_from_image(image)
            
            if extracted_text.strip():
                st.session_state.scanned_texts.append(extracted_text)
                st.success(f"성공적으로 글자를 추출했습니다! (현재 누적 페이지: {len(st.session_state.scanned_texts)}장)")
            else:
                st.warning("인식된 글자가 없습니다. 다시 선명하게 찍어주세요.")

if st.session_state.scanned_texts:
    st.divider()
    st.subheader("📋 전체 누적 텍스트 정보")
    
    full_text = "\n\n".join(st.session_state.scanned_texts)
    
    with st.expander("원본 텍스트 보기", expanded=True):
        st.write(full_text)
        
    st.sidebar.header("🛠️ 음성 및 리딩 설정")
    lang_option = st.sidebar.selectbox("주요 언어 선택", ["한국어 (ko)", "영어 (en)"])
    lang_code = lang_option.split("(")[1].split(")")[0].strip()
    
    use_summary = st.sidebar.checkbox("요약본으로 듣기 (요점만 재생)", value=False)
    
    final_text_to_read = full_text
    if use_summary:
        final_text_to_read = summarize_text(full_text)
        st.info("💡 요점만 요약된 내용으로 음성을 생성합니다.")
        st.code(final_text_to_read)
        
    if st.button("🔊 음성 파일 생성 및 듣기"):
        with st.spinner("음성을 생성하고 있습니다..."):
            audio_data = generate_tts(final_text_to_read, lang=lang_code)
            st.audio(audio_data, format="audio/mp3")
            st.success("재생 버튼을 누르면 오디오가 시작됩니다. 플레이어 내 우측 설정(⋮)에서 속도 조절이 가능합니다.")

    if st.button("🗑️ 전체 비우기 및 새로 시작"):
        st.session_state.scanned_texts = []
        st.rerun()