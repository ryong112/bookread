import streamlit as st
from google import genai
from gtts import gTTS
from PIL import Image
import io

# ==========================================
# 1. 고성능 구글 AI 및 TTS 엔진 (기존 기능 유지)
# ==========================================

def extract_and_summarize_with_gemini(image: Image.Image, api_key: str, use_summary: bool) -> tuple[str, str]:
    if not api_key:
        st.warning("🔑 왼쪽 사이드바에 구글 API 키를 입력해 주세요.")
        return "", ""
    try:
        client = genai.Client(api_key=api_key)
        prompt = (
            "너는 저시력자와 대학생을 위한 최고의 독서 보조 전문가야. "
            "주어진 이미지에서 모든 한글과 영어 텍스트를 복잡한 레이아웃에 상관없이 "
            "사람이 실제 책을 읽는 올바른 순서대로 정확하게 추출해줘. "
            "스마트폰 촬영으로 인해 발생한 오타나 깨진 글자가 있다면 앞뒤 문맥을 고려하여 완벽한 한국어 문장으로 자동 교정해줘."
        )
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=[image, prompt]
        )
        extracted_text = response.text
        
        summarized_text = ""
        if use_summary and extracted_text.strip():
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
    tts = gTTS(text=text, lang=lang, slow=False)
    fp = io.BytesIO()
    tts.write_to_fp(fp)
    fp.seek(0)
    return fp

# ==========================================
# 2. UI/UX 레이아웃 구성 (깔끔한 앱 스타일 개편)
# ==========================================

st.set_page_config(page_title="보이스북 (VoiceBook)", layout="centered")

st.title("📚 글 읽어주는 보이스북")
st.markdown("### 대학교 전공서적 스마트 오디오북 시스템")

# [핵심 추가] 책 제목별 영구 보관을 위한 라이브러리 세션 초기화
if "audiobook_library" not in st.session_state:
    st.session_state.audiobook_library = {} # 구조: {"책제목": {"text": "...", "summary": "..."}}

# 사이드바 설정 구역
st.sidebar.header("🔑 환경 설정")
google_api_key = st.sidebar.text_input("Google Gemini API Key 입력", type="password")
lang_option = st.sidebar.selectbox("주요 음성 언어 선택", ["한국어 (ko)", "영어 (en)"])
lang_code = lang_option.split("(")[1].split(")")[0].strip()
use_summary = st.sidebar.checkbox("요약본으로 듣기 (요점만 재생)", value=False)

# ⭐ [디자인 개편] 깔끔한 스마트폰 화면 구성을 위해 탭 메뉴 사용
tab_scan, tab_library = st.tabs(["📷 새 책 스캔하기", "🎧 내 오디오북 보관함"])

# ==========================================
# 3. 첫 번째 탭: 새 책 스캔하기
# ==========================================
with tab_scan:
    st.subheader("새로운 책 페이지 등록")
    
    # [기능 추가] 책 제목을 입력받아 독립된 저장소 생성
    book_title = st.text_input("📖 읽으실 책 제목을 입력해주세요", value="나의 전공서적").strip()
    
    input_method = st.radio("이미지 가져오기 방식", ["실시간 카메라 촬영", "앨범에서 불러오기"], horizontal=True)

    image = None
    if input_method == "실시간 카메라 촬영":
        camera_img = st.camera_input("책 페이지 촬영")
        if camera_img:
            image = Image.open(camera_img)
    else:
        uploaded_file = st.file_uploader("이미지 선택", type=["jpg", "jpeg", "png"])
        if uploaded_file:
            image = Image.open(uploaded_file)

    if image:
        st.image(image, caption="선택된 이미지", width=350)
        
        if st.button("🚀 구글 AI 분석 및 보관함 저장", type="primary", use_container_width=True):
            if not google_api_key:
                st.error("❌ 왼쪽 설정에서 구글 API 키를 먼저 입력해 주세요.")
            else:
                raw_txt, sum_txt = extract_and_summarize_with_gemini(image, google_api_key, use_summary)
                
                if raw_txt.strip():
                    # 해당 책 제목이 없으면 새로 만들고, 있으면 기존 내용 뒤에 이어서 누적 처리
                    if book_title not in st.session_state.audiobook_library:
                        st.session_state.audiobook_library[book_title] = {"text": "", "summary": ""}
                    
                    st.session_state.audiobook_library[book_title]["text"] += "\n\n" + raw_txt
                    if sum_txt:
                        st.session_state.audiobook_library[book_title]["summary"] += "\n\n" + sum_txt
                        
                    st.success(f"🎉 [{book_title}] 보관함에 페이지가 성공적으로 누적 저장되었습니다!")
                    st.info("상단의 '🎧 내 오디오북 보관함' 탭으로 이동하시면 확인 및 청취가 가능합니다.")

# ==========================================
# 4. 두 번째 탭: 내 오디오북 보관함 (리스트 구현)
# ==========================================
with tab_library:
    st.subheader("🗂️ 등록된 오디오북 리스트")
    
    if not st.session_state.audiobook_library:
        st.warning("아직 등록된 책이 없습니다. '새 책 스캔하기' 탭에서 첫 페이지를 등록해 주세요!")
    else:
        # 저장된 책 제목들을 리스트 선택 상자로 깔끔하게 송출
        saved_books = list(st.session_state.audiobook_library.keys())
        selected_book = st.selectbox("듣고 싶으신 책을 선택하세요", saved_books)
        
        # 선택된 책의 데이터 가져오기
        book_data = st.session_state.audiobook_library[selected_book]
        
        st.divider()
        st.markdown(f"### 🎧 재생 중: **{selected_book}**")
        
        # 요약 모드 여부에 따라 대본 텍스트 확정
        final_text_to_read = book_data["text"]
        if use_summary and book_data["summary"].strip():
            final_text_to_read = book_data["summary"]
            st.info("💡 구글 AI가 요약한 핵심 요점 대본을 읽습니다.")
            st.write(final_text_to_read)
        else:
            with st.expander("원본 전체 텍스트 확인", expanded=True):
                st.write(final_text_to_read)
                
        # 음성 재생 및 다운로드 제어
        if st.button("🔊 음성 파일 재생하기", use_container_width=True):
            with st.spinner("오디오를 구성하는 중입니다..."):
                # 별표 기호 제거 후 깨끗한 음성 생성
                clean_text = final_text_to_read.replace("*", "")
                audio_data = generate_tts(clean_text, lang=lang_code)
                
                st.audio(audio_data, format="audio/mp3")
                
                st.download_button(
                    label="📥 이 오디오북 스마트폰에 파일로 저장하기",
                    data=audio_data,
                    file_name=f"{selected_book}_audio.mp3",
                    mime="audio/mp3",
                    use_container_width=True
                )
                
        if st.button("🗑️ 이 책 보관함에서 삭제", type="secondary"):
            del st.session_state.audiobook_library[selected_book]
            st.rerun()