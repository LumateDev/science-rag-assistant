import streamlit as st
import openai
import os
from dotenv import load_dotenv

# Загрузка переменных из .env файла (если есть)
load_dotenv()

st.set_page_config(page_title="Научный RAG Ассистент", page_icon="🔬")
st.title("🔬 Ассистент учёного (RAG)")
st.caption("Задайте вопрос по загруженным документам, статьям или данным.")

# --- Инициализация клиента OpenAI (совместимого с Yandex Cloud) ---
# Кэшируем клиент, чтобы не пересоздавать его при каждом чихе стримлита
@st.cache_resource
def get_client():
    api_key = os.getenv("YANDEX_API_KEY")
    project_id = os.getenv("YANDEX_PROJECT_ID")
    
    # Если переменных нет в .env, запрашиваем их в сайдбаре
    if not api_key or not project_id:
        st.sidebar.error("Не найден .env файл. Введите данные вручную.")
    
    return openai.OpenAI(
        api_key=api_key,
        base_url="https://ai.api.cloud.yandex.net/v1",
        # Важно: передаем project как заголовок или параметр
        # В новой версии SDK можно передать default_headers
        default_headers={"OpenAI-Project": project_id}
    )

# --- Блок конфигурации в сайдбаре ---
with st.sidebar:
    st.header("⚙️ Конфигурация")
    
    # Поля для ввода (если не через .env)
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
        value=os.getenv("PROMPT_ID", "fvtu64r76l6l21dk0v8u")
    )
    
    # Переопределяем переменные окружения в сессии, если пользователь ввел в сайдбаре
    if api_key_input:
        os.environ["YANDEX_API_KEY"] = api_key_input
    if project_input:
        os.environ["YANDEX_PROJECT_ID"] = project_input
    if prompt_input:
        os.environ["PROMPT_ID"] = prompt_input
        
    st.divider()
    st.markdown("**Инструкция:**")
    st.markdown("1. Вставьте API-ключ.")
    st.markdown("2. Убедитесь, что Prompt ID указан верно.")
    st.markdown("3. Задайте вопрос.")

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

# --- Хранение истории сообщений ---
if "messages" not in st.session_state:
    st.session_state.messages = []

# Отображение истории
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# --- Обработка ввода пользователя ---
if prompt := st.chat_input("Спросите о чём-нибудь из документов..."):
    # Добавляем сообщение пользователя
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # Генерация ответа
    with st.chat_message("assistant"):
        message_placeholder = st.empty()
        full_response = ""
        
        # Используем указанный метод responses.create с prompt_id
        try:
            response = client.responses.create(
                prompt={
                    "id": os.getenv("PROMPT_ID"),
                },
                input=prompt,
            )
            
            # Извлекаем текст ответа
            # Согласно документации Yandex, ответ лежит в response.output_text
            if hasattr(response, 'output_text') and response.output_text:
                full_response = response.output_text
            else:
                # Fallback на случай другой структуры ответа
                full_response = str(response)
                
            message_placeholder.markdown(full_response)
            
        except Exception as e:
            full_response = f"⚠️ Ошибка API: {str(e)}"
            message_placeholder.error(full_response)
            
    # Сохраняем ответ ассистента в историю
    st.session_state.messages.append({"role": "assistant", "content": full_response})