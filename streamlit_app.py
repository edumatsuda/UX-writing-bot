import streamlit as st
from openai import OpenAI
import time

# Configuração da página
st.set_page_config(page_title="Assistente GPT", page_icon="🤖")

# Inicialização da sessão state
if 'client' not in st.session_state:
    st.session_state.client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

if 'thread_id' not in st.session_state:
    st.session_state.thread_id = None

if 'messages' not in st.session_state:
    st.session_state.messages = []

# Configuração do Assistente
ASSISTANT_ID = "seu-assistant-id-aqui"  # Coloque seu Assistant ID aqui

def criar_thread():
    if st.session_state.thread_id is None:
        thread = st.session_state.client.beta.threads.create()
        st.session_state.thread_id = thread.id
    return st.session_state.thread_id

def gerar_resposta(prompt):
    thread_id = criar_thread()
    
    # Adicionar a mensagem do usuário à thread
    st.session_state.client.beta.threads.messages.create(
        thread_id=thread_id,
        role="user",
        content=prompt
    )
    
    # Executar o assistente
    run = st.session_state.client.beta.threads.runs.create(
        thread_id=thread_id,
        assistant_id=ASSISTANT_ID
    )
    
    # Esperar pela resposta
    while run.status in ["queued", "in_progress"]:
        time.sleep(0.5)
        run = st.session_state.client.beta.threads.runs.retrieve(
            thread_id=thread_id,
            run_id=run.id
        )
    
    if run.status == "completed":
        # Buscar as mensagens mais recentes
        messages = st.session_state.client.beta.threads.messages.list(
            thread_id=thread_id
        )
        
        # A primeira mensagem é a mais recente
        assistant_message = messages.data[0].content[0].text.value
        return assistant_message
    else:
        return f"Erro: o run terminou com status {run.status}"

# Interface do usuário
st.title("💬 Assistente GPT")
st.subheader("Seu assistente personalizado")

# Campo de entrada
prompt_usuario = st.chat_input("Digite sua mensagem aqui...")

# Quando o usuário envia uma mensagem
if prompt_usuario:
    # Adicionar mensagem do usuário ao histórico local
    st.session_state.messages.append({"role": "user", "content": prompt_usuario})
    
    # Gerar e adicionar resposta do assistente
    with st.spinner('Gerando resposta...'):
        resposta = gerar_resposta(prompt_usuario)
    st.session_state.messages.append({"role": "assistant", "content": resposta})

# Exibir histórico de mensagens
for msg in st.session_state.messages:
    if msg["role"] == "user":
        st.chat_message("user").write(msg["content"])
    else:
        st.chat_message("assistant").write(msg["content"])

# Botão para limpar conversa
if st.button("Limpar Conversa"):
    st.session_state.messages = []
    st.session_state.thread_id = None
    st.rerun()