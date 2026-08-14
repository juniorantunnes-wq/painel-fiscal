import streamlit as st
import pandas as pd
import zipfile
import re
import urllib.request
import json

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(
    page_title="Sistema de Inteligência Fiscal",
    page_icon="⚖️",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# --- ESTILIZAÇÃO CSS CORPORATIVA PREMIUM (CLEAN & ENTERPRISE) ---
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

    /* Reset Geral para Light/Enterprise Theme */
    html, body, [class*="css"], .stApp {
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif !important;
        background-color: #f1f5f9 !important;
        color: #0f172a !important;
    }

    /* Container Principal */
    .block-container {
        padding-top: 2rem !important;
        padding-bottom: 3rem !important;
        max-width: 1280px !important;
    }

    /* Topbar / Navbar Corporate */
    .navbar-header {
        background: #ffffff;
        border: 1px solid #e2e8f0;
        border-radius: 12px;
        padding: 20px 28px;
        margin-bottom: 20px;
        box-shadow: 0 1px 3px 0 rgba(0, 0, 0, 0.05);
        display: flex;
        justify-content: space-between;
        align-items: center;
    }
    .brand-title {
        font-size: 20px;
        font-weight: 700;
        color: #0f172a;
        margin: 0;
        letter-spacing: -0.02em;
    }
    .brand-subtitle {
        font-size: 13px;
        color: #64748b;
        margin-top: 2px;
    }

    /* Input & Botão de Pesquisa */
    div[data-baseweb="input"] {
        background-color: #ffffff !important;
        border: 1px solid #cbd5e1 !important;
        border-radius: 8px !important;
        box-shadow: 0 1px 2px 0 rgba(0, 0, 0, 0.05);
    }
    div[data-baseweb="input"]:focus-within {
        border-color: #2563eb !important;
        box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.1) !important;
    }
    .stButton > button {
        background-color: #1e293b !important;
        color: #ffffff !important;
        font-weight: 600 !important;
        border-radius: 8px !important;
        border: none !important;
        height: 42px !important;
        transition: all 0.2s ease !important;
    }
    .stButton > button:hover {
        background-color: #0f172a !important;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
    }

    /* Componentes de Cards (KPIs) */
    .kpi-card {
        background: #ffffff;
        border: 1px solid #e2e8f0;
        border-radius: 10px;
        padding: 16px 20px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.04);
    }
    .kpi-label {
        font-size: 11px;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        color: #64748b;
        margin-bottom: 4px;
    }
    .kpi-value {
        font-size: 16px;
        font-weight: 600;
        color: #0f172a;
    }
    .kpi-value-highlight {
        font-size: 20px;
        font-weight: 700;
        color: #2563eb;
    }

    /* Badges Status Cadastral */
    .badge-ativa {
        background-color: #dcfce7;
        color: #166534;
        border: 1px solid #bbf7d0;
        padding: 4px 12px;
        border-radius: 9999px;
        font-size: 12px;
        font-weight: 600;
        display: inline-block;
    }
    .badge-outros {
        background-color: #fee2e2;
        color: #991b1b;
        border: 1px solid #fecaca;
        padding: 4px 12px;
        border-radius: 9999px;
        font-size: 12px;
        font-weight: 600;
        display: inline-block;
    }

    /* Abas Customizadas (Navegação Clara e Legível) */
    .stTabs [data-baseweb="tab-list"] {
        background-color: #e2e8f0 !important;
        padding: 4px !important;
        border-radius: 8px !important;
        gap: 4px !important;
    }
    .stTabs [data-baseweb="tab"] {
        height: 38px !important;
        border-radius: 6px !important;
        color: #475569 !important;
        font-weight: 600 !important;
        font-size: 13px !important;
        background-color: transparent !important;
        border: none !important;
    }
    .stTabs [aria-selected="true"] {
        background-color: #ffffff !important;
        color: #0f172a !important;
        box-shadow: 0 1px 3px rgba(0,0,0,0.1) !important;
    }

    /* Tabelas HTML Customizadas Enterprise */
    .custom-table {
        width: 100%;
        border-collapse: collapse;
        margin-top: 10px;
        font-size: 13px;
        background: #ffffff;
        border: 1px solid #e2e8f0;
        border-radius: 8px;
        overflow: hidden;
    }
    .custom-table th {
        background-color: #f8fafc;
        color: #475569;
        font-weight: 600;
        text-align: left;
        padding: 12px 16px;
        border-bottom: 1px solid #e2e8f0;
        text-transform: uppercase;
        font-size: 11px;
        letter-spacing: 0.05em;
    }
    .custom-table td {
        padding: 12px 16px;
        border-bottom: 1px solid #f1f5f9;
        color: #1e293b;
    }
    .custom-table tr:last-child td {
        border-bottom: none;
    }
    .custom-table tr:hover {
        background-color: #f8fafc;
    }

    /* Status Alerts */
    .alert-box-danger {
        background-color: #fef2f2;
        border: 1px solid #fecaca;
        border-left: 4px solid #ef4444;
        padding: 16px 20px;
        border-radius: 8px;
        color: #991b1b;
    }
    .alert-box-success {
        background-color: #f0fdf4;
        border: 1px solid #bbf7d0;
        border-left: 4px solid #22c55e;
        padding: 16px 20px;
        border-radius: 8px;
        color: #166534;
    }
</style>
""", unsafe_allow_html=True)

# --- TOPBAR DA APLICAÇÃO ---
st.markdown("""
<div class="navbar-header">
    <div>
        <div class="brand-title">⚖️ Sistema de Inteligência Fiscal e Conformidade</div>
        <div class="brand-subtitle">Plataforma corporativa de consulta cadastral, quadro de sócios e diagnóstico da Dívida Ativa da União.</div>
    </div>
</div>
""", unsafe_allow_html=True)

# --- CARREGAR BASES LOCAIS ---
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

# --- CAMPO DE BUSCA PRINCIPAL ---
col_search, col_btn = st.columns([5, 1])
with col_search:
    cnpj_input = st.text_input(
        "CNPJ",
        placeholder="Informe o CNPJ para análise completa (ex: 41.618.558/0001-12)",
        label_visibility="collapsed"
    )
with col_btn:
    btn_buscar = st.button("Consultar CNPJ", use_container_width=True)

# --- EXECUÇÃO E RETORNO DOS DADOS ---
if btn_buscar or cnpj_input:
    if cnpj_input.strip():
        cnpj_limpo = re.sub(r'\D', '', cnpj_input)
        
        dados_api = {}
        with st.spinner("Buscando registros oficiais..."):
            try:
                url = f"https://brasilapi.com.br/api/cnpj/v1/{cnpj_limpo}"
                req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
                with urllib.request.urlopen(req) as resp:
                    dados_api = json.loads(resp.read().decode('utf-8'))
            except Exception:
                st.error("⚠️ Não foi possível localizar o CNPJ informado na base da Receita Federal.")

        if dados_api:
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

            # CARD DE IDENTIFICAÇÃO DA EMPRESA
            badge_class = "badge-ativa" if situacao.upper() == "ATIVA" else "badge-outros"
            
            st.markdown(f"""
            <div style="background: #ffffff; border: 1px solid #e2e8f0; border-radius: 12px; padding: 20px 24px; margin-top: 15px; margin-bottom: 20px; box-shadow: 0 1px 3px rgba(0,0,0,0.04);">
                <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 12px;">
                    <div>
                        <div style="font-size: 18px; font-weight: 700; color: #0f172a;">{razao_social}</div>
                        <div style="font-size: 13px; color: #64748b; margin-top: 2px;">Nome Fantasia: <b style="color: #334155;">{nome_fantasia}</b> &nbsp;|&nbsp; CNPJ: <b style="color: #334155;">{cnpj_input}</b></div>
                    </div>
                    <div>
                        <span class="{badge_class}">SITUAÇÃO: {situacao}</span>
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)

            # ESTRUTURA DE NAVEGAÇÃO EM ABAS
            tab1, tab2, tab3, tab4, tab5 = st.tabs([
                "📋 Visão Geral", 
                "👥 Quadro Societário (QSA)", 
                "💼 Atividades (CNAE)", 
                "⚠️ Dívida Ativa (PGFN)", 
                "🌐 CNDs Mapeadas"
            ])

            # ABA 1: VISÃO GERAL
            with tab1:
                st.write("")
                c1, c2, c3, c4 = st.columns(4)
                
                with c1:
                    st.markdown(f"""
                    <div class="kpi-card">
                        <div class="kpi-label">Capital Social</div>
                        <div class="kpi-value-highlight">R$ {capital_social:,.2f}</div>
                    </div>
                    """, unsafe_allow_html=True)
                with c2:
                    st.markdown(f"""
                    <div class="kpi-card">
                        <div class="kpi-label">Data de Abertura</div>
                        <div class="kpi-value">{data_inicio}</div>
                    </div>
                    """, unsafe_allow_html=True)
                with c3:
                    st.markdown(f"""
                    <div class="kpi-card">
                        <div class="kpi-label">Data Situação</div>
                        <div class="kpi-value">{data_situacao}</div>
                    </div>
                    """, unsafe_allow_html=True)
                with c4:
                    st.markdown(f"""
                    <div class="kpi-card">
                        <div class="kpi-label">Simples Nacional / MEI</div>
                        <div class="kpi-value">Simples: <b>{optante_simples}</b> | MEI: <b>{optante_mei}</b></div>
                    </div>
                    """, unsafe_allow_html=True)

                st.write("")
                col_e, col_c = st.columns(2)
                with col_e:
                    st.markdown(f"""
                    <div class="kpi-card">
                        <div class="kpi-label" style="color:#2563eb;">📍 Endereço Cadastral</div>
                        <div style="font-size: 13px; line-height: 1.6; color: #334155; margin-top: 8px;">
                            <b>Logradouro:</b> {logradouro}, Nº {numero}<br>
                            <b>Bairro:</b> {bairro} | <b>CEP:</b> {cep}<br>
                            <b>Município/UF:</b> {municipio} - {uf}
                        </div>
                    </div>
                    """, unsafe_allow_html=True)

                with col_c:
                    st.markdown(f"""
                    <div class="kpi-card">
                        <div class="kpi-label" style="color:#2563eb;">📞 Contato Oficial</div>
                        <div style="font-size: 13px; line-height: 1.6; color: #334155; margin-top: 8px;">
                            <b>E-mail:</b> {email}<br>
                            <b>Telefone:</b> {ddd_tel}<br>
                            <b>Órgão Registrador:</b> Receita Federal do Brasil
                        </div>
                    </div>
                    """, unsafe_allow_html=True)

            # ABA 2: QUADRO SOCIETÁRIO (QSA DENTRO DE TABELA HTML PROFISSIONAL)
            with tab2:
                st.write("")
                if qsa:
                    rows_html = ""
                    for socio in qsa:
                        nome_socio = socio.get('nome_socio', 'N/A')
                        qual_socio = socio.get('qualificacao_socio', 'N/A')
                        faixa_etaria = socio.get('faixa_etaria', 'N/A')
                        rows_html += f"<tr><td><b>{nome_socio}</b></td><td>{qual_socio}</td><td>{faixa_etaria}</td></tr>"

                    table_html = f"""
                    <table class="custom-table">
                        <thead>
                            <tr>
                                <th>Nome do Sócio / Administrador</th>
                                <th>Qualificação / Cargo</th>
                                <th>Faixa Etária</th>
                            </tr>
                        </thead>
                        <tbody>
                            {rows_html}
                        </tbody>
                    </table>
                    """
                    st.markdown(table_html, unsafe_allow_html=True)
                else:
                    st.info("Nenhum sócio ou administrador registrado na base pública do CNPJ.")

            # ABA 3: ATIVIDADES ECONOMICAS (CNAE)
            with tab3:
                st.write("")
                st.markdown(f"""
                <div class="kpi-card" style="margin-bottom: 16px;">
                    <div class="kpi-label" style="color:#2563eb;">Atividade Econômica Principal (CNAE)</div>
                    <div style="font-size: 15px; font-weight: 600; color: #0f172a; margin-top: 4px;">
                        {cnae_principal_cod} — <span style="color: #475569; font-weight: 400;">{cnae_principal_desc}</span>
                    </div>
                </div>
                """, unsafe_allow_html=True)

                if cnaes_secundarios:
                    st.markdown("<div class='kpi-label' style='margin-bottom: 8px;'>Atividades Secundárias Mapeadas</div>", unsafe_allow_html=True)
                    rows_sec = ""
                    for item in cnaes_secundarios:
                        rows_sec += f"<tr><td><b>{item.get('codigo')}</b></td><td>{item.get('descricao')}</td></tr>"
                    
                    st.markdown(f"""
                    <table class="custom-table">
                        <thead>
                            <tr>
                                <th style="width: 160px;">Código CNAE</th>
                                <th>Descrição da Atividade</th>
                            </tr>
                        </thead>
                        <tbody>
                            {rows_sec}
                        </tbody>
                    </table>
                    """, unsafe_allow_html=True)

            # ABA 4: DÍVIDA ATIVA (PGFN)
            with tab4:
                st.write("")
                encontrados = pd.DataFrame()
                if not df_pgfn.empty:
                    encontrados = df_pgfn[df_pgfn['CPF/CNPJ'].str.replace(r'\D', '', regex=True) == cnpj_limpo]

                if len(encontrados) > 0:
                    row = encontrados.iloc[0]
                    valor_debito = row.get('Valor Total', 'N/A')
                    st.markdown(f"""
                    <div class="alert-box-danger">
                        <div style="font-size: 16px; font-weight: 700; margin-bottom: 4px;">🚨 DÉBITO ENCONTRADO NA PGFN</div>
                        <div style="font-size: 13px;"><b>Razão Social Inscrita:</b> {row.get('Nome', 'N/A')}</div>
                        <div style="font-size: 15px; margin-top: 6px;"><b>Valor Inscrito na Dívida Ativa:</b> <span style="font-weight: 700;">R$ {valor_debito}</span></div>
                    </div>
                    """, unsafe_allow_html=True)
                else:
                    st.markdown("""
                    <div class="alert-box-success">
                        <div style="font-size: 15px; font-weight: 700;">🟢 REGULARIDADE FISCAL CONFIRMADA NA PGFN</div>
                        <div style="font-size: 13px; margin-top: 2px;">Nenhum débito pendente na Dívida Ativa da União foi encontrado nesta base.</div>
                    </div>
                    """, unsafe_allow_html=True)

            # ABA 5: CNDs
            with tab5:
                st.write("")
                if not df_cnds.empty:
                    filtro_uf = df_cnds[df_cnds['UF'] == uf] if ('UF' in df_cnds.columns and uf) else df_cnds
                    rows_cnd = ""
                    for idx, row_cnd in filtro_uf.head(10).iterrows():
                        origem = row_cnd.get('ORIGEM', 'N/A')
                        uf_cnd = row_cnd.get('UF', 'N/A')
                        tipo = row_cnd.get('TIPO', 'N/A')
                        rows_cnd += f"<tr><td><b>{origem}</b></td><td>{uf_cnd}</td><td>{tipo}</td></tr>"

                    st.markdown(f"""
                    <table class="custom-table">
                        <thead>
                            <tr>
                                <th>Origem / Órgão</th>
                                <th>UF</th>
                                <th>Tipo de Certidão</th>
                            </tr>
                        </thead>
                        <tbody>
                            {rows_cnd}
                        </tbody>
                    </table>
                    """, unsafe_allow_html=True)
                else:
                    st.info("Nenhuma base local de CNDs disponível.")
    else:
        st.warning("Informe um número de CNPJ válido.")
