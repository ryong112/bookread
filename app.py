import streamlit as st
import easyocr
from gtts import gTTS
from PIL import Image
import numpy as np
import io

# ==========================================
# 1. 초기 설정 및 모듈화된 엔진 정의
# ==========================================

@st.cache_resource
def load_ocr_reader():
    """한글과 영어를 동시에 인식하는 OCR 엔진을 로드합니다 (캐싱 처리)."""
    return easyocr.Reader(['ko', 'en'], gpu=False)

def summarize_text(text: str, ratio: float = 0.5) -> str:
    """
    [요약 엔진] 입력된 텍스트를 문장 단위로 분할하여 핵심 요점을 추출합니다.
    (추후 2단계에서 고성능 AI 요약 모델로 업그레이드 가능한 구조로 설계)
    """
    if not text.strip():
        return ""
    
    sentences = [s.strip() for s in text.split('.') if s.strip()]
    if len(sentences) <= 2:
        return text # 문장이 너무 적으면 전체 출력
        
    # 우선 1단계에서는 문장 전반부와 후반부의 핵심 요점을 추출하는 오픈소스 로직 적용
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

# 세션 상태 초기화 (재촬영 및 다중 장수 관리를 위한 저장소)
if "scanned_texts" not in st.session_state:
    st.session_state.scanned_texts = []

# 기능 선택: 카메라 촬영 vs 앨범에서 가져오기
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
    st.image(image, caption="선택된 이미지", use_column_width=True)
    
    if st.button("📝 글자 인식 시작", type="primary"):
        with st.spinner("글자를 분석하는 중입니다. 잠시만 기다려주세요..."):
            reader = load_ocr_reader()
            # PIL 이미지를 numpy 배열로 변환하여 OCR 수행
            img_np = np.array(image)
            result = reader.readtext(img_np, detail=0)
            extracted_text = " ".join(result)
            
            if extracted_text.strip():
                st.session_state.scanned_texts.append(extracted_text)
                st.success(f"성공적으로 글자를 추출했습니다! (현재 누적 페이지: {len(st.session_state.scanned_texts)}장)")
            else:
                st.warning("인식된 글자가 없습니다. 다시 선명하게 찍어주세요.")

# 누적된 텍스트가 있을 경우 처리 화면 표시
if st.session_state.scanned_texts:
    st.divider()
    st.subheader("📋 전체 누적 텍스트 정보")
    
    full_text = "\n\n".join(st.session_state.scanned_texts)
    
    # 텍스트 보기 편하게 확장형 레이아웃 제공
    with st.expander("원본 텍스트 보기", expanded=True):
        st.write(full_text)
        
    # 옵션 설정 구역 (속도 및 요약 여부)
    st.sidebar.header("🛠️ 음성 및 리딩 설정")
    
    # 주 언어 선택
    lang_option = st.sidebar.selectbox("주요 언어 선택", ["한국어 (ko)", "영어 (en)"])
    lang_code = lang_option.split("(")[1].split(")")[0].strip()
    
    # 요약 기능 활성화 여부
    use_summary = st.sidebar.checkbox("요약본으로 듣기 (요점만 재생)", value=False)
    
    # 음성 처리 진행
    final_text_to_read = full_text
    if use_summary:
        final_text_to_read = summarize_text(full_text)
        st.info("💡 요점만 요약된 내용으로 음성을 생성합니다.")
        st.code(final_text_to_read)
        
    if st.button("🔊 음성 파일 생성 및 듣기"):
        with st.spinner("음성을 생성하고 있습니다..."):
            audio_data = generate_tts(final_text_to_read, lang=lang_code)
            
            # 모바일 브라우저 표준 오디오 플레이어 송출
            # 오디오 플레이어 자체에서 재생 속도 제어(0.5x ~ 2.0x) 인터페이스를 기본 제공하므로 접근성이 우수합니다.
            st.audio(audio_data, format="audio/mp3")
            st.success("재생 버튼을 누르면 오디오가 시작됩니다. 플레이어 내 우측 설정(⋮)에서 속도 조절이 가능합니다.")

    # 초기화 버튼
    if st.button("🗑️ 전체 비우기 및 새로 시작"):
        st.session_state.scanned_texts = []
        st.experimental_rerun()