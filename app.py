import streamlit as st
import pandas as pd
import zipfile
import re
import urllib.request
import json

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(
    page_title="Painel de Inteligência Fiscal",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# --- ESTILIZAÇÃO CSS CUSTOMIZADA (LAYOUT PROFISSIONAL) ---
st.markdown("""
<style>
    /* Estilo Geral */
    .stApp {
        background-color: #0f172a;
        color: #f8fafc;
        font-family: 'Inter', system-ui, -apple-system, sans-serif;
    }
    
    /* Header Principal */
    .main-header {
        background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%);
        padding: 24px;
        border-radius: 12px;
        border: 1px solid #334155;
        margin-bottom: 24px;
        box-shadow: 0 4px 20px rgba(0, 0, 0, 0.3);
    }
    .main-title {
        font-size: 26px;
        font-weight: 700;
        color: #f8fafc;
        margin: 0;
        display: flex;
        align-items: center;
        gap: 12px;
    }
    .main-subtitle {
        color: #94a3b8;
        font-size: 14px;
        margin-top: 6px;
    }

    /* Cards de Informação */
    .info-card {
        background-color: #1e293b;
        border: 1px solid #334155;
        border-radius: 10px;
        padding: 18px;
        margin-bottom: 16px;
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.2);
    }
    .card-label {
        font-size: 11px;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        color: #94a3b8;
        font-weight: 600;
        margin-bottom: 6px;
    }
    .card-value {
        font-size: 16px;
        font-weight: 600;
        color: #f1f5f9;
    }
    .card-value-lg {
        font-size: 22px;
        font-weight: 700;
        color: #38bdf8;
    }

    /* Badges de Status */
    .status-badge-ativa {
        background-color: rgba(34, 197, 94, 0.15);
        color: #4ade80;
        border: 1px solid rgba(34, 197, 94, 0.3);
        padding: 4px 12px;
        border-radius: 20px;
        font-size: 13px;
        font-weight: 600;
        display: inline-block;
    }
    .status-badge-outros {
        background-color: rgba(239, 68, 68, 0.15);
        color: #f87171;
        border: 1px solid rgba(239, 68, 68, 0.3);
        padding: 4px 12px;
        border-radius: 20px;
        font-size: 13px;
        font-weight: 600;
        display: inline-block;
    }

    /* Seções e Abas */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
        background-color: #1e293b;
        padding: 6px;
        border-radius: 10px;
        border: 1px solid #334155;
    }
    .stTabs [data-baseweb="tab"] {
        height: 42px;
        border-radius: 6px;
        color: #94a3b8;
        font-weight: 500;
        padding: 0 16px;
    }
    .stTabs [aria-selected="true"] {
        background-color: #0284c7 !important;
        color: #ffffff !important;
    }

    /* Tabelas */
    div[data-testid="stDataFrame"] {
        border: 1px solid #334155;
        border-radius: 8px;
        overflow: hidden;
    }

    /* Alertas customizados */
    .alert-danger {
        background-color: rgba(239, 68, 68, 0.1);
        border: 1px solid #ef4444;
        border-left: 6px solid #ef4444;
        padding: 16px;
        border-radius: 8px;
        color: #fca5a5;
    }
    .alert-success {
        background-color: rgba(34, 197, 94, 0.1);
        border: 1px solid #22c55e;
        border-left: 6px solid #22c55e;
        padding: 16px;
        border-radius: 8px;
        color: #86efac;
    }
</style>
""", unsafe_allow_html=True)

# --- CABEÇALHO DO SISTEMA ---
st.markdown("""
<div class="main-header">
    <div class="main-title">🛡️ Painel Executivo de Inteligência Fiscal</div>
    <div class="main-subtitle">Consulta consolidada de Dados Cadastrais, Quadro de Sócios (QSA), CNAEs e Diagnóstico da Dívida Ativa da União (PGFN).</div>
</div>
""", unsafe_allow_html=True)

# --- CARREGAMENTO DE BASES LOCAIS ---
@st.cache_data
def carregar_bases():
    df_pgfn = pd.DataFrame()
    df_cnds = pd.DataFrame()
    
    try:
        with zipfile.ZipFile('Consulta_Lista_Devedores_2026_08_13.zip', 'r') as z:
            filename = z.namelist()[0]
            lines = z.open(filename).readlines()
            start_idx = 0
            for idx, line in enumerate(lines):
                if 'CPF/CNPJ' in line.decode('latin1'):
                    start_idx = idx
                    break
            import io
            csv_content = "".join([l.decode('latin1') for l in lines[start_idx:]])
            df_pgfn = pd.read_csv(io.StringIO(csv_content), sep=';', quotechar='"')
            df_pgfn.columns = [c.strip() for c in df_pgfn.columns]
    except Exception:
        pass

    try:
        df_cnds = pd.read_excel("LISTAGEM_CNDs_DEZ_1.xlsx", sheet_name=0)
    except Exception:
        pass
        
    return df_pgfn, df_cnds

df_pgfn, df_cnds = carregar_bases()

# --- BARRA DE PESQUISA (CONTAINER DESTACADO) ---
with st.container():
    col_input, col_btn = st.columns([4, 1])
    with col_input:
        cnpj_input = st.text_input(
            "Digite o CNPJ para pesquisa:",
            placeholder="Ex: 31.945.912/0001-60",
            label_visibility="collapsed"
        )
    with col_btn:
        btn_buscar = st.button("🔍 Pesquisar CNPJ", use_container_width=True, type="primary")

# --- PROCESSAMENTO DA CONSULTA ---
if btn_buscar or cnpj_input:
    if cnpj_input.strip():
        cnpj_limpo = re.sub(r'\D', '', cnpj_input)
        
        dados_api = {}
        with st.spinner("Consultando bases de dados oficiais..."):
            try:
                url = f"https://brasilapi.com.br/api/cnpj/v1/{cnpj_limpo}"
                req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
                with urllib.request.urlopen(req) as resp:
                    dados_api = json.loads(resp.read().decode('utf-8'))
            except Exception:
                st.error("⚠️ CNPJ não localizado ou falha na consulta cadastral. Verifique o número digitado.")

        if dados_api:
            # Extração de Variáveis
            razao_social = dados_api.get("razao_social", "N/A")
            nome_fantasia = dados_api.get("nome_fantasia") or "Não informado"
            situacao = dados_api.get("descricao_situacao_cadastral", "N/A")
            data_situacao = dados_api.get("data_situacao_cadastral", "N/A")
            data_inicio = dados_api.get("data_inicio_atividade", "N/A")
            capital_social = dados_api.get("capital_social", 0.0)
            
            logradouro = dados_api.get("logradouro", "")
            numero = dados_api.get("numero", "")
            bairro = dados_api.get("bairro", "")
            municipio = dados_api.get("municipio", "")
            uf = dados_api.get("uf", "")
            cep = dados_api.get("cep", "")
            email = dados_api.get("email") or "Não informado"
            tel = dados_api.get("ddd_telefone_1", "")
            ddd_tel = f"({tel[:2]}) {tel[2:]}" if tel else "Não informado"

            cnae_principal_cod = dados_api.get("cnae_fiscal", "")
            cnae_principal_desc = dados_api.get("cnae_fiscal_descricao", "")
            cnaes_secundarios = dados_api.get("cnaes_secundarios", [])

            optante_simples = "Sim" if dados_api.get("opcao_pelo_simples") else "Não"
            optante_mei = "Sim" if dados_api.get("opcao_pelo_mei") else "Não"
            qsa = dados_api.get("qsa", [])

            # --- CARD PRINCIPAL DE IDENTIFICAÇÃO ---
            badge_class = "status-badge-ativa" if situacao.upper() == "ATIVA" else "status-badge-outros"
            
            st.markdown(f"""
            <div class="info-card" style="margin-top: 15px;">
                <div style="display: flex; justify-content: space-between; align-items: flex-start; flex-wrap: wrap; gap: 10px;">
                    <div>
                        <div style="font-size: 20px; font-weight: 700; color: #f8fafc;">{razao_social}</div>
                        <div style="color: #94a3b8; font-size: 13px; margin-top: 2px;">Nome Fantasia: <strong style="color: #cbd5e1;">{nome_fantasia}</strong> | CNPJ: <strong style="color: #cbd5e1;">{cnpj_input}</strong></div>
                    </div>
                    <div>
                        <span class="{badge_class}">SITUAÇÃO: {situacao}</span>
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)

            # --- ESTRUTURA EM ABAS ---
            tab1, tab2, tab3, tab4, tab5 = st.tabs([
                "📋 Visão Geral", 
                "👥 Quadro Societário (QSA)", 
                "💼 Atividades (CNAE)", 
                "⚠️ Dívida Ativa (PGFN)", 
                "🌐 Mapeamento CNDs"
            ])

            # TAB 1: VISÃO GERAL
            with tab1:
                st.write("")
                col1, col2, col3, col4 = st.columns(4)
                
                with col1:
                    st.markdown(f"""
                    <div class="info-card">
                        <div class="card-label">Capital Social</div>
                        <div class="card-value-lg">R$ {capital_social:,.2f}</div>
                    </div>
                    """, unsafe_allow_html=True)
                with col2:
                    st.markdown(f"""
                    <div class="info-card">
                        <div class="card-label">Data de Abertura</div>
                        <div class="card-value">{data_inicio}</div>
                    </div>
                    """, unsafe_allow_html=True)
                with col3:
                    st.markdown(f"""
                    <div class="info-card">
                        <div class="card-label">Data da Situação</div>
                        <div class="card-value">{data_situacao}</div>
                    </div>
                    """, unsafe_allow_html=True)
                with col4:
                    st.markdown(f"""
                    <div class="info-card">
                        <div class="card-label">Regimes Tributários</div>
                        <div class="card-value" style="font-size:14px;">Simples: <b>{optante_simples}</b> | MEI: <b>{optante_mei}</b></div>
                    </div>
                    """, unsafe_allow_html=True)

                col_end, col_cont = st.columns(2)
                with col_end:
                    st.markdown(f"""
                    <div class="info-card">
                        <div class="card-label" style="color: #38bdf8;">📍 Endereço Fiscal Cadastrado</div>
                        <div style="font-size: 14px; line-height: 1.6; color: #cbd5e1; margin-top: 8px;">
                            <b>Logradouro:</b> {logradouro}, Nº {numero}<br>
                            <b>Bairro:</b> {bairro} | <b>CEP:</b> {cep}<br>
                            <b>Município/UF:</b> {municipio} - {uf}
                        </div>
                    </div>
                    """, unsafe_allow_html=True)

                with col_cont:
                    st.markdown(f"""
                    <div class="info-card">
                        <div class="card-label" style="color: #38bdf8;">📞 Canais de Contato</div>
                        <div style="font-size: 14px; line-height: 1.6; color: #cbd5e1; margin-top: 8px;">
                            <b>E-mail Oficial:</b> {email}<br>
                            <b>Telefone Comercial:</b> {ddd_tel}<br>
                            <b>Fonte dos Dados:</b> Receita Federal do Brasil (via BrasilAPI)
                        </div>
                    </div>
                    """, unsafe_allow_html=True)

            # TAB 2: QUADRO SOCIETÁRIO (QSA)
            with tab2:
                st.write("")
                if qsa:
                    df_qsa = pd.DataFrame(qsa)
                    df_qsa = df_qsa.rename(columns={
                        'nome_socio': 'Nome do Sócio / Administrador',
                        'qualificacao_socio': 'Qualificação / Cargo',
                        'faixa_etaria': 'Faixa Etária'
                    })
                    cols_exibir = [c for c in ['Nome do Sócio / Administrador', 'Qualificação / Cargo', 'Faixa Etária'] if c in df_qsa.columns]
                    st.dataframe(df_qsa[cols_exibir], use_container_width=True, hide_index=True)
                else:
                    st.info("Nenhum sócio ou administrador listado no cadastro público deste CNPJ.")

            # TAB 3: CNAEs
            with tab3:
                st.write("")
                st.markdown(f"""
                <div class="info-card">
                    <div class="card-label" style="color: #38bdf8;">Atividade Econômica Principal</div>
                    <div style="font-size: 16px; font-weight: 600; color: #f8fafc; margin-top: 6px;">
                        CNAE {cnae_principal_cod} — <span style="color:#94a3b8;">{cnae_principal_desc}</span>
                    </div>
                </div>
                """, unsafe_allow_html=True)

                if cnaes_secundarios:
                    st.write(f"**Atividades Secundárias ({len(cnaes_secundarios)} registradas):**")
                    df_sec = pd.DataFrame(cnaes_secundarios).rename(columns={'codigo': 'Código CNAE', 'descricao': 'Descrição da Atividade'})
                    st.dataframe(df_sec, use_container_width=True, hide_index=True)

            # TAB 4: DÍVIDA ATIVA (PGFN)
            with tab4:
                st.write("")
                encontrados = pd.DataFrame()
                if not df_pgfn.empty:
                    encontrados = df_pgfn[df_pgfn['CPF/CNPJ'].str.replace(r'\D', '', regex=True) == cnpj_limpo]

                if len(encontrados) > 0:
                    row = encontrados.iloc[0]
                    valor_debito = row.get('Valor Total', 'N/A')
                    st.markdown(f"""
                    <div class="alert-danger">
                        <div style="font-size: 18px; font-weight: 700; margin-bottom: 8px;">🚨 DÉBITO ENCONTRADO NA PGFN</div>
                        <div><b>Razão Social Cadastrada:</b> {row.get('Nome', 'N/A')}</div>
                        <div><b>Valor Total Inscrito:</b> <span style="font-size: 18px; font-weight: 700;">R$ {valor_debito}</span></div>
                        <div style="font-size: 12px; margin-top: 8px; opacity: 0.8;">Origem: Base Local da Procuradoria-Geral da Fazenda Nacional.</div>
                    </div>
                    """, unsafe_allow_html=True)
                else:
                    st.markdown("""
                    <div class="alert-success">
                        <div style="font-size: 16px; font-weight: 700;">🟢 SITUAÇÃO REGULAR NA PGFN</div>
                        <div style="font-size: 13px; margin-top: 4px;">Nenhum débito inscrito na Dívida Ativa da União foi encontrado para este CNPJ na base consultada.</div>
                    </div>
                    """, unsafe_allow_html=True)

            # TAB 5: CNDs
            with tab5:
                st.write("")
                if not df_cnds.empty:
                    filtro_uf = df_cnds[df_cnds['UF'] == uf] if ('UF' in df_cnds.columns and uf) else df_cnds
                    st.markdown(f"**Robôs e Portais Mapeados para o Estado de {uf} ({municipio}):**")
                    cols_cnd = [c for c in ['ORIGEM', 'UF', 'TIPO'] if c in filtro_uf.columns]
                    st.dataframe(filtro_uf[cols_cnd].head(15), use_container_width=True, hide_index=True)
                else:
                    st.info("Nenhuma base de CNDs carregada no repositório.")
    else:
        st.warning("Por favor, informe um número de CNPJ no campo acima.")
