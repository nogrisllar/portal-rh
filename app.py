import streamlit as st
import os
import time
import bcrypt
import pandas as pd
import io
from auth import validar_usuario
from database import SessionLocal, Usuario, Documento

# --- CONFIGURAÇÕES VISUAIS ---
st.set_page_config(page_title="Portal do Servidor", page_icon="🇧🇷", layout="wide")
PASTA_UPLOAD = "contracheques_upload"
os.makedirs(PASTA_UPLOAD, exist_ok=True)

# --- CSS PARA LIMPAR O VISUAL ---
hide_streamlit_style = """
            <style>
            #MainMenu {visibility: hidden;}
            footer {visibility: hidden;}
            header {visibility: hidden;}
            </style>
            """
st.markdown(hide_streamlit_style, unsafe_allow_html=True)

# --- MAPA DE MESES ---
MAPA_MESES = {
    "01": "Janeiro", "02": "Fevereiro", "03": "Março", "04": "Abril",
    "05": "Maio", "06": "Junho", "07": "Julho", "08": "Agosto",
    "09": "Setembro", "10": "Outubro", "11": "Novembro", "12": "Dezembro",
    "13": "13º Salário", 
    "14": "Adiantamento 13º"
}

# --- FUNÇÕES DE SISTEMA ---
def formatar_referencia(mes_raw, ano_raw):
    nome_mes = MAPA_MESES.get(mes_raw, mes_raw)
    return f"{nome_mes}/{ano_raw}"

def extrair_dados_arquivo(nome_arquivo):
    try:
        nome_limpo = os.path.splitext(nome_arquivo)[0]
        partes = nome_limpo.split('_')
        if len(partes) < 4: return None, None, False
        
        cpf_extraido = partes[1]
        data_raw = partes[3] 

        if len(data_raw) == 6:
            mes = data_raw[:2]
            ano = data_raw[2:]
            referencia_bonita = formatar_referencia(mes, ano)
            return cpf_extraido, referencia_bonita, True
        else:
            return cpf_extraido, data_raw, True
    except Exception:
        return None, None, False

def salvar_doc_generico(arquivo, cpf_alvo, referencia_formatada):
    db = SessionLocal()
    try:
        user = db.query(Usuario).filter(Usuario.username == cpf_alvo).first()
        if not user:
            user = db.query(Usuario).filter(Usuario.username == str(int(cpf_alvo))).first()
            
        if not user:
            return False, f"CPF {cpf_alvo} não encontrado no sistema."
        
        nome_final = arquivo.name 
        caminho = os.path.join(PASTA_UPLOAD, nome_final)
        
        with open(caminho, "wb") as f:
            f.write(arquivo.getbuffer())
            
        doc = Documento(filename=nome_final, mes_ano=referencia_formatada, usuario_id=user.id)
        db.add(doc)
        db.commit()
        return True, "Arquivo salvo com sucesso"
    except Exception as e:
        return False, str(e)
    finally:
        db.close()

def criar_usuario(cpf, nome, senha):
    db = SessionLocal()
    try:
        # Verifica se CPF já existe
        if db.query(Usuario).filter(Usuario.username == str(cpf)).first():
            return False, "CPF já cadastrado."
        
        if not cpf or not nome or not senha:
             return False, "Dados incompletos."

        # Criptografa senha
        hashed = bcrypt.hashpw(str(senha).encode('utf-8'), bcrypt.gensalt())
        
        novo = Usuario(
            username=str(cpf), 
            nome_completo=str(nome), 
            senha_hash=hashed.decode('utf-8'), 
            is_admin=False
        )
        db.add(novo)
        db.commit()
        return True, "Sucesso"
    except Exception as e:
        return False, str(e)
    finally:
        db.close()

def listar_todos_usuarios():
    db = SessionLocal()
    usuarios = db.query(Usuario).all()
    db.close()
    dados = [{"ID": u.id, "Nome": u.nome_completo, "CPF": u.username, "Perfil Admin": "Sim" if u.is_admin else "Não"} for u in usuarios]
    return dados

def alterar_senha_admin(cpf_alvo, nova_senha):
    db = SessionLocal()
    try:
        user = db.query(Usuario).filter(Usuario.username == cpf_alvo).first()
        if not user:
            return False, "Usuário não encontrado."
        
        hashed = bcrypt.hashpw(nova_senha.encode('utf-8'), bcrypt.gensalt())
        user.senha_hash = hashed.decode('utf-8')
        db.commit()
        return True, f"Senha de {user.nome_completo} alterada com sucesso!"
    except Exception as e:
        return False, str(e)
    finally:
        db.close()

# --- INÍCIO DO PROGRAMA ---
if 'logado' not in st.session_state:
    st.session_state['logado'] = False
    st.session_state['usuario'] = None

# --- TELA DE LOGIN ---
if not st.session_state['logado']:
    col1, col2, col3 = st.columns([1,2,1])
    with col2:
        st.title("Portal do Servidor")
        st.markdown("### Acesso ao Sistema")
        with st.form("login"):
            cpf_login = st.text_input("CPF (Apenas números)")
            senha_login = st.text_input("Senha", type="password")
            if st.form_submit_button("ENTRAR NO SISTEMA"):
                u = validar_usuario(cpf_login, senha_login)
                if u:
                    st.session_state['logado'] = True
                    st.session_state['usuario'] = {'id': u.id, 'nome': u.nome_completo, 'admin': u.is_admin}
                    st.rerun()
                else:
                    st.error("CPF ou Senha incorretos. Tente novamente.")
else:
    dados = st.session_state['usuario']
    
    # --- BARRA LATERAL ---
    with st.sidebar:
        st.write(f"Bem-vindo(a), **{dados['nome']}**")
        if st.button("SAIR DO SISTEMA"):
            st.session_state['logado'] = False
            st.rerun()

    # --- PERFIL: ADMINISTRADOR (RH) ---
    if dados['admin']:
        st.title("Painel de Gestão e RH")
        
        # Novas Abas
        tab_lote, tab_manual, tab_cadastro, tab_import, tab_users = st.tabs([
            "🚀 Envio Docs", 
            "📝 Envio Manual", 
            "➕ Novo Servidor",
            "📥 Importar Usuários",
            "👥 Gerenciar Usuários"
        ])
        
        # ABA 1: ENVIO DOCS (LOTE)
        with tab_lote:
            st.info("Selecione os contracheques (PDF) e arraste para a área abaixo.")
            arquivos = st.file_uploader("Contracheques (PDF)", accept_multiple_files=True, type="pdf")
            
            if arquivos:
                qtd = len(arquivos)
                st.markdown(f"**{qtd} arquivos selecionados**")
                lista_nomes = [f.name for f in arquivos]
                df_preview = pd.DataFrame(lista_nomes, columns=["Nome do Arquivo"])
                st.dataframe(df_preview, use_container_width=True, height=200)
                
                if st.button(f"ENVIAR TODOS ({qtd})"):
                    progresso = st.progress(0)
                    relatorio = []
                    for i, arq in enumerate(arquivos):
                        cpf, ref, ok = extrair_dados_arquivo(arq.name)
                        if ok:
                            salvou, msg = salvar_doc_generico(arq, cpf, ref)
                            status = "✅ Enviado" if salvou else "❌ Falha"
                            obs = f"{cpf} - {ref}" if salvou else msg
                        else:
                            status = "⚠️ Nome Inválido"
                            obs = "Arquivo fora do padrão"
                        relatorio.append({"Arquivo": arq.name, "Status": status, "Detalhes": obs})
                        progresso.progress((i+1)/qtd)
                    
                    st.success("Processamento finalizado!")
                    df_res = pd.DataFrame(relatorio)
                    st.dataframe(df_res.style.applymap(
                        lambda v: 'color: red;' if 'Falha' in str(v) or 'Inválido' in str(v) else 'color: green;', subset=['Status']
                    ), use_container_width=True, height=400)

        # ABA 2: ENVIO MANUAL
        with tab_manual:
            c1, c2, c3 = st.columns(3)
            with c1: cpf_manual = st.text_input("CPF do Servidor")
            with c2: 
                mes_sel = st.selectbox("Mês de Referência", [f"{k} - {v}" for k, v in MAPA_MESES.items()])
                cod_mes = mes_sel.split(" - ")[0]
            with c3: ano_manual = st.text_input("Ano", value="2025")
            
            pdf_manual = st.file_uploader("Selecione o PDF do contracheque", type="pdf")
            if st.button("ENVIAR ARQUIVO"):
                if cpf_manual and pdf_manual:
                    ref = formatar_referencia(cod_mes, ano_manual)
                    ok, msg = salvar_doc_generico(pdf_manual, cpf_manual, ref)
                    if ok: st.success("Arquivo enviado com sucesso!")
                    else: st.error(msg)
                else:
                    st.warning("Preencha todos os campos.")

        # ABA 3: CADASTRO UNITÁRIO
        with tab_cadastro:
            st.subheader("Registrar Um Servidor")
            c1, c2 = st.columns(2)
            novo_cpf = c1.text_input("CPF (Apenas números)", key="new_cpf")
            novo_nome = c2.text_input("Nome Completo", key="new_name")
            nova_senha = st.text_input("Senha Inicial", type="password", key="new_pass")
            
            if st.button("CADASTRAR SERVIDOR"):
                ok, msg = criar_usuario(novo_cpf, novo_nome, nova_senha)
                if ok: st.success(msg)
                else: st.error(msg)

        # ABA 4: IMPORTAÇÃO DE USUÁRIOS (NOVA!)
        with tab_import:
            st.subheader("Importação em Massa (CSV)")
            st.markdown("""
            **Instruções:**
            1. Crie uma planilha no Excel.
            2. Coloque 3 colunas na ordem: **CPF**, **Nome**, **Senha**.
            3. Salve como **CSV (Separado por vírgulas)**.
            """)
            
            # Botão para baixar modelo
            csv_modelo = "CPF,Nome,Senha\n11111111111,Joao Silva,123456\n22222222222,Maria Souza,senha123"
            st.download_button(
                label="📥 Baixar Planilha Modelo",
                data=csv_modelo,
                file_name="modelo_importacao_usuarios.csv",
                mime="text/csv"
            )
            
            st.divider()
            
            arquivo_users = st.file_uploader("Carregue seu arquivo CSV aqui", type=["csv"])
            
            if arquivo_users:
                try:
                    df_users = pd.read_csv(arquivo_users, dtype=str) # Lê tudo como texto para não perder zeros
                    
                    # Verifica se tem as 3 colunas necessárias (pelo índice 0, 1, 2)
                    if len(df_users.columns) < 3:
                        st.error("O arquivo precisa ter 3 colunas: CPF, Nome e Senha.")
                    else:
                        st.markdown("### Pré-visualização")
                        st.dataframe(df_users.head(), use_container_width=True)
                        
                        if st.button(f"CADASTRAR {len(df_users)} USUÁRIOS"):
                            progresso = st.progress(0)
                            sucessos = 0
                            erros = 0
                            log_import = []
                            
                            total = len(df_users)
                            for index, row in df_users.iterrows():
                                # Pega os dados independente do nome da coluna, pela posição
                                u_cpf = row.iloc[0]
                                u_nome = row.iloc[1]
                                u_senha = row.iloc[2]
                                
                                ok, msg = criar_usuario(u_cpf, u_nome, u_senha)
                                
                                status = "✅ Criado" if ok else "⚠️ Erro"
                                log_import.append({"CPF": u_cpf, "Nome": u_nome, "Resultado": status, "Detalhe": msg})
                                
                                if ok: sucessos += 1
                                else: erros += 1
                                
                                progresso.progress((index + 1) / total)
                                
                            st.success(f"Finalizado! Criados: {sucessos} | Não criados: {erros}")
                            df_log = pd.DataFrame(log_import)
                            st.dataframe(df_log.style.applymap(
                                lambda v: 'color: red;' if 'Erro' in str(v) else 'color: green;', subset=['Resultado']
                            ), use_container_width=True)
                            
                except Exception as e:
                    st.error(f"Erro ao ler o arquivo: {e}")

        # ABA 5: GERENCIAR USUÁRIOS
        with tab_users:
            st.subheader("Lista de Servidores")
            lista_users = listar_todos_usuarios()
            df_users = pd.DataFrame(lista_users)
            
            if not df_users.empty:
                st.dataframe(df_users, use_container_width=True)
                st.divider()
                st.subheader("🔑 Redefinir Senha")
                
                lista_cpfs = df_users["CPF"].tolist()
                usuario_selecionado = st.selectbox("Escolha o Servidor (CPF):", lista_cpfs)
                nova_senha_admin = st.text_input("Nova Senha:", type="password", key="reset_pass")
                
                if st.button("ATUALIZAR SENHA"):
                    if usuario_selecionado and nova_senha_admin:
                        ok, msg = alterar_senha_admin(usuario_selecionado, nova_senha_admin)
                        if ok: st.success(msg)
                        else: st.error(msg)
                    else:
                        st.warning("Digite a nova senha.")
            else:
                st.info("Ainda não há servidores cadastrados.")

    # --- PERFIL: SERVIDOR (USUÁRIO COMUM) ---
    else:
        st.header("Meus Contracheques")
        db = SessionLocal()
        docs = db.query(Documento).filter(Documento.usuario_id == dados['id']).order_by(Documento.mes_ano.desc()).all()
        db.close()
        
        if docs:
            for d in docs:
                caminho = os.path.join(PASTA_UPLOAD, d.filename)
                if os.path.exists(caminho):
                    with open(caminho, "rb") as f:
                        st.download_button(
                            label=f"⬇️ Baixar {d.mes_ano}", 
                            data=f, 
                            file_name=d.filename, 
                            mime="application/pdf"
                        )
                else:
                    st.warning(f"⚠️ O arquivo '{d.mes_ano}' não foi encontrado. Por favor, contate o RH.")
                st.divider()
        else:
            st.info("Você não possui contracheques disponíveis para download no momento.")