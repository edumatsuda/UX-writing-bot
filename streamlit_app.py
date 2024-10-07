import streamlit as st
from openai import OpenAI
import time
import re
from datetime import datetime
import json
import os

# Configuração da página
st.set_page_config(page_title="Azul UX - Assistente", page_icon="🤖", layout="wide")

# Constantes
FAVORITOS_FILE = "favoritos.json"
DEFAULT_TAGS = ["gramática", "clareza", "tom", "estrutura", "outro"]

# Funções de gerenciamento de arquivos
def carregar_favoritos_do_arquivo():
    if os.path.exists(FAVORITOS_FILE):
        try:
            with open(FAVORITOS_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except json.JSONDecodeError:
            st.error(f"Erro ao carregar favoritos do arquivo {FAVORITOS_FILE}")
            return []
    return []

def salvar_favoritos_no_arquivo(favoritos):
    try:
        with open(FAVORITOS_FILE, 'w', encoding='utf-8') as f:
            json.dump(favoritos, f, ensure_ascii=False, indent=2)
    except Exception as e:
        st.error(f"Erro ao salvar favoritos: {str(e)}")

# Inicialização da sessão state
if 'client' not in st.session_state:
    st.session_state.client = OpenAI(api_key=st.secrets["OPENAI_KEY"])

if 'thread_id' not in st.session_state:
    st.session_state.thread_id = None

if 'messages' not in st.session_state:
    st.session_state.messages = []

if 'favoritos' not in st.session_state:
    st.session_state.favoritos = carregar_favoritos_do_arquivo()

if 'debug_mode' not in st.session_state:
    st.session_state.debug_mode = False

# Configuração do Assistente
ASSISTANT_ID = "asst_2gdW0pdYhNLEl0Kp9BIQankx"

def extrair_secoes(texto):
    """Extrai as seções 'Original' e 'Sugestão' do texto em formato Markdown"""
    secoes = {}
    
    # Múltiplos padrões para maior flexibilidade
    padroes_original = [
        r'\*\*Original\*\*:\s*"([^"]+)"',
        r'\*\*Original\*\*:\s*(.+?)(?=\n|$)',
    ]
    padroes_sugestao = [
        r'\*\*Sugestão\*\*:\s*"([^"]+)"',
        r'\*\*Sugestão\*\*:\s*(.+?)(?=\n|$)',
    ]
    
    # Tentar cada padrão para Original
    for padrao in padroes_original:
        match = re.search(padrao, texto, re.DOTALL)
        if match:
            secoes['Original'] = match.group(1).strip()
            break
    
    # Tentar cada padrão para Sugestão
    for padrao in padroes_sugestao:
        match = re.search(padrao, texto, re.DOTALL)
        if match:
            secoes['Sugestão'] = match.group(1).strip()
            break
    
    # Log para debug
    if st.session_state.debug_mode:
        st.write("Texto recebido para extração:", texto)
        st.write("Seções encontradas:", secoes)
    
    return secoes

def salvar_resposta_favorita(prompt, resposta_completa, citations):
    secoes = extrair_secoes(resposta_completa)
    
    if not secoes:
        st.warning("Não foi possível encontrar as seções Original e Sugestão na resposta.")
        if st.session_state.debug_mode:
            st.write("Resposta completa que não pôde ser processada:", resposta_completa)
        return False
    
    favorito_id = str(int(time.time()))
    
    favorito = {
        "id": favorito_id,
        "data": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "prompt": prompt,
        "original": secoes.get('Original', ''),
        "sugestao": secoes.get('Sugestão', ''),
        "citations": citations,
        "tags": []
    }
    
    st.session_state.favoritos.append(favorito)
    salvar_favoritos_no_arquivo(st.session_state.favoritos)
    return favorito_id

def atualizar_tags(favorito_id, novas_tags):
    for fav in st.session_state.favoritos:
        if fav["id"] == favorito_id:
            fav["tags"] = novas_tags
            salvar_favoritos_no_arquivo(st.session_state.favoritos)
            break

# Funções do Assistente
def criar_thread():
    if st.session_state.thread_id is None:
        thread = st.session_state.client.beta.threads.create()
        st.session_state.thread_id = thread.id
    return st.session_state.thread_id

def processar_mensagem_assistente(message):
    texto_principal = message.content[0].text.value
    annotations = message.content[0].text.annotations
    citations = []
    
    if annotations:
        for index, annotation in enumerate(annotations):
            if hasattr(annotation, 'file_citation'):
                citation_text = annotation.text
                file_citation = annotation.file_citation
                cited_file = st.session_state.client.files.retrieve(file_citation.file_id)
                citations.append(f"{index + 1}. {citation_text} [Arquivo: {cited_file.filename}]")
            elif hasattr(annotation, 'file_path'):
                file_path = annotation.file_path
                cited_file = st.session_state.client.files.retrieve(file_path.file_id)
                citations.append(f"{index + 1}. Referência ao arquivo: {cited_file.filename}")
    
    return texto_principal, citations

def gerar_resposta(prompt):
    thread_id = criar_thread()
    
    st.session_state.client.beta.threads.messages.create(
        thread_id=thread_id,
        role="user",
        content=prompt
    )
    
    run = st.session_state.client.beta.threads.runs.create(
        thread_id=thread_id,
        assistant_id=ASSISTANT_ID
    )
    
    while run.status in ["queued", "in_progress"]:
        time.sleep(0.5)
        run = st.session_state.client.beta.threads.runs.retrieve(
            thread_id=thread_id,
            run_id=run.id
        )
    
    if run.status == "completed":
        messages = st.session_state.client.beta.threads.messages.list(
            thread_id=thread_id
        )
        return processar_mensagem_assistente(messages.data[0])
    else:
        return f"Erro: o run terminou com status {run.status}", []

# Interface do usuário
import streamlit as st
from openai import OpenAI
import time
import re
from datetime import datetime
import json
import os

# [O restante das importações e configurações permanecem iguais]

# ... [O código anterior permanece o mesmo até a parte da interface do usuário]

# Interface do usuário
st.title("💬 Assistente GPT")

# Botão de debug no sidebar
with st.sidebar:
    st.session_state.debug_mode = st.checkbox("Modo Debug", value=st.session_state.debug_mode)

# Criação de abas
tab1, tab2 = st.tabs(["Chat", "Respostas Favoritas"])

with tab1:
    st.subheader("Seu assistente personalizado")
    
    # Criar um container para as mensagens
    chat_container = st.container()
    
    # Criar um container separado para o campo de entrada
    input_container = st.container()
    
    # Usar o container de entrada para o campo de prompt
    with input_container:
        prompt_usuario = st.chat_input("Digite sua mensagem aqui...")
    
    # Processar a entrada do usuário
    if prompt_usuario:
        st.session_state.messages.append({"role": "user", "content": prompt_usuario, "citations": []})
        
        with st.spinner('Gerando resposta...'):
            resposta, citations = gerar_resposta(prompt_usuario)
        st.session_state.messages.append({"role": "assistant", "content": resposta, "citations": citations})
        
        # Recarregar a página para mostrar a nova mensagem
        st.rerun()
    
    # Exibir mensagens no container de chat
    with chat_container:
        for msg in st.session_state.messages:
            with st.chat_message(msg["role"]):
                st.write(msg["content"])
                if msg["citations"]:
                    st.divider()
                    st.caption("Referências:")
                    for citation in msg["citations"]:
                        st.caption(citation)
                
                # Botão de salvar favorito para respostas do assistente
                if msg["role"] == "assistant":
                    if st.button(f"⭐ Salvar como favorito", key=f"fav_{msg['content'][:10]}"):
                        # Encontrar o prompt correspondente (a mensagem do usuário anterior)
                        index = st.session_state.messages.index(msg)
                        if index > 0 and st.session_state.messages[index-1]["role"] == "user":
                            prompt_anterior = st.session_state.messages[index-1]["content"]
                            if salvar_resposta_favorita(prompt_anterior, msg["content"], msg["citations"]):
                                st.toast("Resposta salva nos favoritos!", icon="⭐")
    
    # Botão para limpar conversa (mantido fora dos containers para fácil acesso)
    if st.button("Limpar Conversa"):
        st.session_state.messages = []
        st.session_state.thread_id = None
        st.rerun()

with tab2:
    st.subheader("Respostas Favoritas")
    
    # Filtro por tags
    todas_tags = set()
    for fav in st.session_state.favoritos:
        todas_tags.update(fav.get("tags", []))
    todas_tags = sorted(list(todas_tags))
    
    col1, col2 = st.columns([2, 1])
    with col1:
        tags_selecionadas = st.multiselect("Filtrar por tags:", todas_tags)
    
    with col2:
        opcao_ordenacao = st.selectbox("Ordenar por:", ["Mais recente", "Mais antigo"])
    
    favoritos_filtrados = [
        fav for fav in st.session_state.favoritos
        if not tags_selecionadas or any(tag in fav.get("tags", []) for tag in tags_selecionadas)
    ]
    
    if opcao_ordenacao == "Mais antigo":
        favoritos_filtrados.reverse()
    
    if not favoritos_filtrados:
        st.info("Ainda não há respostas favoritas salvas. Use o botão ⭐ no chat para salvar respostas!")
    else:
        for fav in favoritos_filtrados:
            with st.expander(f"Favorito - {fav['data']}"):
                col1, col2 = st.columns([3, 1])
                
                with col1:
                    st.subheader("Pergunta:")
                    st.write(fav["prompt"])
                    if fav["original"]:
                        st.subheader("Original:")
                        st.write(fav["original"])
                    if fav["sugestao"]:
                        st.subheader("Sugestão:")
                        st.write(fav["sugestao"])
                
                with col2:
                    # Gerenciamento de tags
                    st.subheader("Tags")
                    tags_atuais = set(fav.get("tags", []))
                    
                    for tag in DEFAULT_TAGS:
                        if st.checkbox(tag, value=tag in tags_atuais, key=f"{fav['id']}_{tag}"):
                            tags_atuais.add(tag)
                        else:
                            tags_atuais.discard(tag)
                    
                    # Campo para adicionar nova tag
                    nova_tag = st.text_input("Nova tag:", key=f"new_tag_{fav['id']}")
                    if st.button("Adicionar Tag", key=f"add_tag_{fav['id']}"):
                        if nova_tag and nova_tag not in tags_atuais:
                            tags_atuais.add(nova_tag)
                    
                    # Atualizar tags no favorito
                    if st.button("Salvar Tags", key=f"save_tags_{fav['id']}"):
                        atualizar_tags(fav['id'], list(tags_atuais))
                        st.toast("Tags atualizadas!", icon="✅")
                
                if fav["citations"]:
                    st.divider()
                    st.caption("Referências:")
                    for citation in fav["citations"]:
                        st.caption(citation)
        
        if st.button("Limpar Favoritos"):
            if st.checkbox("Confirmar exclusão de todos os favoritos"):
                st.session_state.favoritos = []
                salvar_favoritos_no_arquivo([])
                st.rerun()