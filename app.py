import streamlit as st
import openai
import os
import base64
import requests
from dotenv import load_dotenv

load_dotenv()

st.set_page_config(page_title="Научный RAG Ассистент", page_icon="🔬")
st.title("🔬 Ассистент учёного (RAG)")
st.caption("Голосовой ввод и озвучка ответов")

# --- Инициализация session state ---
if "messages" not in st.session_state:
    st.session_state.messages = []
if "voice_text" not in st.session_state:
    st.session_state.voice_text = ""
if "awaiting_voice_response" not in st.session_state:
    st.session_state.awaiting_voice_response = False

# --- Синтез речи через Yandex SpeechKit ---
def text_to_speech(text, api_key, voice="alena", speed="1.0"):
    """Конвертирует текст в аудио через Yandex SpeechKit"""
    url = "https://tts.api.cloud.yandex.net/speech/v1/tts:synthesize"
    headers = {"Authorization": f"Api-Key {api_key}"}
    
    data = {
        "text": text[:500],  # Ограничение длины для скорости
        "lang": "ru-RU",
        "voice": voice,
        "format": "mp3",
        "speed": speed
    }
    
    try:
        response = requests.post(url, headers=headers, data=data, timeout=10)
        if response.status_code == 200:
            return response.content
        else:
            st.error(f"Ошибка синтеза речи: {response.status_code}")
            return None
    except Exception as e:
        st.error(f"Ошибка подключения к SpeechKit: {e}")
        return None

def get_audio_player_html(audio_bytes):
    """Создает HTML для автовоспроизведения аудио"""
    if audio_bytes:
        audio_b64 = base64.b64encode(audio_bytes).decode()
        return f"""
        <audio autoplay style="display:none;">
            <source src="data:audio/mp3;base64,{audio_b64}" type="audio/mp3">
        </audio>
        """
    return ""

# --- Инициализация клиента YandexGPT ---
@st.cache_resource
def get_client():
    api_key = os.getenv("YANDEX_API_KEY")
    project_id = os.getenv("YANDEX_PROJECT_ID")
    
    return openai.OpenAI(
        api_key=api_key,
        base_url="https://ai.api.cloud.yandex.net/v1",
        default_headers={"OpenAI-Project": project_id}
    )

# --- Сайдбар с конфигурацией ---
with st.sidebar:
    st.header("⚙️ Конфигурация")
    
    api_key_input = st.text_input(
        "Yandex API Key", 
        value=os.getenv("YANDEX_API_KEY", ""), 
        type="password"
    )
    project_input = st.text_input(
        "Project ID", 
        value=os.getenv("YANDEX_PROJECT_ID", "b1gea2upudrrrnph3fj4")
    )
    prompt_input = st.text_input(
        "Prompt ID", 
        value=os.getenv("PROMPT_ID", "fvt7h1ud49bldnec9fjn")
    )
    
    # Настройки озвучки
    st.divider()
    st.subheader("🔊 Озвучка")
    tts_enabled = st.checkbox("Включить озвучку ответов", value=True)
    tts_voice = st.selectbox("Голос", ["alena", "filipp", "ermil", "jane"], index=0)
    tts_speed = st.slider("Скорость", 0.5, 2.0, 1.0, 0.1)
    
    if api_key_input:
        os.environ["YANDEX_API_KEY"] = api_key_input
    if project_input:
        os.environ["YANDEX_PROJECT_ID"] = project_input
    if prompt_input:
        os.environ["PROMPT_ID"] = prompt_input
        
    st.divider()
    st.markdown("**Голосовое управление:**")
    st.markdown("1. Нажмите 🎤 и разрешите микрофон")
    st.markdown("2. Говорите и нажмите 'Готово'")
    st.markdown("3. Ответ будет озвучен")

# --- Проверка готовности ---
if not os.getenv("YANDEX_API_KEY"):
    st.warning("👈 Пожалуйста, введите API ключ в боковом меню.")
    st.stop()

# Инициализация клиента
try:
    client = openai.OpenAI(
        api_key=os.getenv("YANDEX_API_KEY"),
        base_url="https://ai.api.cloud.yandex.net/v1",
        default_headers={"OpenAI-Project": os.getenv("YANDEX_PROJECT_ID")}
    )
except Exception as e:
    st.error(f"Ошибка подключения клиента: {e}")
    st.stop()

# --- Голосовой ввод через streamlit-mic-recorder ---
st.markdown("### 🎤 Голосовой ввод")

# Используем встроенный audio_input (доступен в новых версиях Streamlit)
try:
    audio_value = st.audio_input("Запишите голосовое сообщение")
    
    if audio_value:
        # Конвертируем аудио в текст через Yandex SpeechKit
        with st.spinner("🎵 Распознаю речь..."):
            url = "https://stt.api.cloud.yandex.net/speech/v1/stt:recognize"
            headers = {"Authorization": f"Api-Key {os.getenv('YANDEX_API_KEY')}"}
            
            # Отправляем аудио на распознавание
            files = {"audio": audio_value.read()}
            
            try:
                response = requests.post(
                    url, 
                    headers=headers, 
                    files=files,
                    params={"lang": "ru-RU"}
                )
                
                if response.status_code == 200:
                    st.session_state.voice_text = response.json().get("result", "")
                    st.success(f"✓ Распознано: {st.session_state.voice_text}")
                else:
                    st.error(f"Ошибка распознавания: {response.status_code}")
            except Exception as e:
                st.error(f"Ошибка: {e}")
except AttributeError:
    # Если audio_input не доступен, показываем альтернативу
    st.info("Ваша версия Streamlit не поддерживает audio_input. Обновите: pip install streamlit --upgrade")
    
    # Простое текстовое поле для ручного ввода
    manual_text = st.text_input("Введите текст вручную:", key="manual_input")
    if st.button("Отправить"):
        st.session_state.voice_text = manual_text

# --- Отображение истории сообщений ---
for idx, message in enumerate(st.session_state.messages):
    with st.chat_message(message["role"]):
        st.markdown(message["content"])
        
        # Кнопка озвучки для сообщений ассистента
        if message["role"] == "assistant" and tts_enabled:
            col1, col2 = st.columns([1, 5])
            with col1:
                if st.button(f"🔊", key=f"tts_{idx}", help="Озвучить ответ"):
                    audio_bytes = text_to_speech(
                        message["content"], 
                        os.getenv("YANDEX_API_KEY"),
                        tts_voice,
                        str(tts_speed)
                    )
                    if audio_bytes:
                        st.markdown(get_audio_player_html(audio_bytes), unsafe_allow_html=True)

# --- Обработка ввода ---
# Приоритет: голосовой ввод, затем ручной
if st.session_state.voice_text:
    prompt = st.session_state.voice_text
    st.session_state.voice_text = ""  # Очищаем после использования
elif "manual_input" in st.session_state and st.session_state.manual_input:
    prompt = st.session_state.manual_input
else:
    prompt = st.chat_input("Или введите текст здесь...")

# --- Отправка запроса агенту ---
if prompt:
    # Добавляем сообщение пользователя
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # Генерация ответа
    with st.chat_message("assistant"):
        message_placeholder = st.empty()
        full_response = ""
        
        try:
            with st.spinner("🤔 Анализирую документы..."):
                response = client.responses.create(
                    prompt={"id": os.getenv("PROMPT_ID")},
                    input=prompt,
                )
                
                if hasattr(response, 'output_text') and response.output_text:
                    full_response = response.output_text
                else:
                    full_response = str(response)
                    
            message_placeholder.markdown(full_response)
            
            # Автоматическая озвучка если включена
            if tts_enabled:
                with st.spinner("🔊 Озвучиваю ответ..."):
                    audio_bytes = text_to_speech(
                        full_response, 
                        os.getenv("YANDEX_API_KEY"),
                        tts_voice,
                        str(tts_speed)
                    )
                    if audio_bytes:
                        st.markdown(get_audio_player_html(audio_bytes), unsafe_allow_html=True)
            
        except Exception as e:
            full_response = f"⚠️ Ошибка API: {str(e)}"
            message_placeholder.error(full_response)
            
    st.session_state.messages.append({"role": "assistant", "content": full_response})
    st.rerun()