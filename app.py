import io
import json
import re
import urllib.parse
import urllib.request
import zipfile
from datetime import datetime
import pandas as pd
import streamlit as st

# ==============================================================================
# CONFIGURAÇÕES DO ESCRITÓRIO E CONSULTORES TRIBUTÁRIOS
# ==============================================================================
NOME_ESCRITORIO = "Seu Escritório Contábil & Tributário"
NUMERO_WHATSAPP = "5585999999999"  # Insira o DDD + Número (Ex: 5585999999999)

# ==============================================================================
# BASE DE EDITAIS E REGRAS DE TRANSAÇÃO PGFN (Mapeamento de Regras Fiscais)
# ==============================================================================
EDITAIS_PGFN = [
    {
        "nome": "Transação por Adesão (Débitos até R$ 50 Mi)",
        "desconto_max": "Até 70% em juros, multas e encargos",
        "prazo_max": "Até 145 parcelas mensais",
        "elegibilidade": "Empresas com débitos inscritos na Dívida Ativa da União e baixa capacidade de pagamento (CAPAG C or D).",
    },
    {
        "nome": "Transação para Microempresas e EPP (Simples Nacional / MEI)",
        "desconto_max": "Até 50% do valor total da dívida",
        "prazo_max": "Entrada facilitada + até 60 parcelas",
        "elegibilidade": "Optantes do Simples Nacional ou MEI com débitos previdenciários e tributários.",
    },
    {
        "nome": "Transação Individual ou de Pequeno Valor",
        "desconto_max": "Até 50% sobre o montante principal/juros",
        "prazo_max": "Até 60 meses (Previdenciário) ou 145 meses (Demais)",
        "elegibilidade": "Débitos consolidados de menor valor ou devedores em recuperação judicial.",
    },
]

# ==============================================================================
# CONFIGURAÇÃO DA PÁGINA
# ==============================================================================
st.set_page_config(
    page_title=f"Inteligência Fiscal & Editais PGFN - {NOME_ESCRITORIO}",
    page_icon="⚖️",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ==============================================================================
# ESTILIZAÇÃO CSS
# ==============================================================================
st.markdown(
    """
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

    .stApp {
        background-color: #f1f5f9 !important;
        font-family: 'Inter', sans-serif !important;
        color: #0f172a !important;
    }

    .block-container {
        padding-top: 1.5rem !important;
        padding-bottom: 3rem !important;
        max-width: 1200px !important;
    }

    .header-card {
        background: #ffffff;
        border: 1px solid #cbd5e1;
        border-radius: 12px;
        padding: 24px;
        margin-bottom: 20px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.05);
    }

    .alert-pgfn {
        background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%);
        color: #ffffff;
        border-radius: 12px;
        padding: 24px;
        margin-bottom: 24px;
        box-shadow: 0 10px 15px -3px rgba(0,0,0,0.1);
    }

    .edital-box {
        background: #f8fafc;
        border: 1px solid #cbd5e1;
        border-left: 4px solid #2563eb;
        border-radius: 6px;
        padding: 14px;
        margin-top: 10px;
    }

    .btn-wa {
        background-color: #22c55e !important;
        color: #ffffff !important;
        font-weight: 700 !important;
        padding: 12px 20px !important;
        border-radius: 8px !important;
        text-decoration: none !important;
        display: inline-block !important;
        text-align: center !important;
    }

    .field-box {
        border: 1px solid #e2e8f0;
        padding: 8px 12px;
        background-color: #ffffff;
        margin-bottom: -1px;
        margin-right: -1px;
    }

    .field-label {
        font-size: 10px;
        font-weight: 700;
        color: #64748b;
        text-transform: uppercase;
    }

    .field-value {
        font-size: 13px;
        font-weight: 600;
        color: #0f172a;
    }
</style>
""",
    unsafe_allow_html=True,
)


# ==============================================================================
# VALIDAÇÃO MATEMÁTICA DE CNPJ
# ==============================================================================
def cnpj_valido(cnpj: str) -> bool:
    cnpj_limpo = re.sub(r"\D", "", cnpj)
    if len(cnpj_limpo) != 14 or cnpj_limpo == cnpj_limpo[0] * 14:
        return False

    def calcular_digito(base: str) -> int:
        pesos = list(range(len(base) + 1, 1, -1))
        soma = sum(int(d) * p for d, p in zip(base, pesos))
        resto = soma % 11
        return 0 if resto < 2 else 11 - resto

    digito1 = calcular_digito(cnpj_limpo[:12])
    digito2 = calcular_digito(cnpj_limpo[:12] + str(digito1))
    return cnpj_limpo[-2:] == f"{digito1}{digito2}"


# ==============================================================================
# CARREGAMENTO DE BASES LOCAIS
# ==============================================================================
@st.cache_data
def carregar_bases():
    df_pgfn = pd.DataFrame()
    df_cnds = pd.DataFrame()

    try:
        with zipfile.ZipFile("Consulta_Lista_Devedores_2026_08_13.zip", "r") as z:
            filename = z.namelist()[0]
            lines = z.open(filename).readlines()
            start_idx = 0
            for idx, line in enumerate(lines):
                if "CPF/CNPJ" in line.decode("latin1"):
                    start_idx = idx
                    break
            csv_content = "".join([l.decode("latin1") for l in lines[start_idx:]])
            df_pgfn = pd.read_csv(io.StringIO(csv_content), sep=";", quotechar='"')
            df_pgfn.columns = [c.strip() for c in df_pgfn.columns]
    except Exception:
        pass

    try:
        df_cnds = pd.read_excel("LISTAGEM_CNDs_DEZ_1.xlsx", sheet_name=0)
    except Exception:
        pass

    return df_pgfn, df_cnds


df_pgfn, df_cnds = carregar_bases()

# ==============================================================================
# TOPO DO APP
# ==============================================================================
st.markdown(
    f"""
<div class="header-card">
    <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap;">
        <div>
            <h2 style="margin: 0; font-size: 24px; color: #0f172a;">⚖️ Portal de Diagnóstico Fiscal & Oportunidades PGFN</h2>
            <p style="margin: 4px 0 0 0; color: #64748b; font-size: 14px;">Análise Contábil de Regularidade, Simulador de Editais de Transação e Emissão de CNDs</p>
        </div>
        <div>
            <span style="background: #e0e7ff; color: #3730a3; padding: 6px 12px; border-radius: 6px; font-weight: 700; font-size: 13px;">
                {NOME_ESCRITORIO}
            </span>
        </div>
    </div>
</div>
""",
    unsafe_allow_html=True,
)

# ==============================================================================
# FORMULÁRIO DE CONSULTA
# ==============================================================================
col_in, col_bt = st.columns([4, 1])
with col_in:
    cnpj_input = st.text_input(
        "CNPJ da Empresa:",
        placeholder="Digite o CNPJ (ex: 41.618.558/0001-12)",
        label_visibility="collapsed",
    )
with col_bt:
    btn_buscar = st.button("🔍 Diagnosticar CNPJ", use_container_width=True, type="primary")

if btn_buscar or cnpj_input:
    if cnpj_input.strip():
        cnpj_limpo = re.sub(r"\D", "", cnpj_input)

        if not cnpj_valido(cnpj_limpo):
            st.error("⚠️ CNPJ inválido. Verifique os dígitos digitados e tente novamente.")
        else:
            dados_api = {}
            with st.spinner("Realizando auditoria cadastral e consultando bases públicas..."):
                try:
                    url = f"https://brasilapi.com.br/api/cnpj/v1/{cnpj_limpo}"
                    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
                    with urllib.request.urlopen(req) as resp:
                        dados_api = json.loads(resp.read().decode("utf-8"))
                except Exception:
                    st.error("⚠️ CNPJ não encontrado na base pública da Receita Federal.")

            if dados_api:
                razao_social = dados_api.get("razao_social", "N/A")
                nome_fantasia = dados_api.get("nome_fantasia") or "********"
                situacao = dados_api.get("descricao_situacao_cadastral", "N/A")
                porte = dados_api.get("porte", "N/A")
                uf = dados_api.get("uf", "")
                qsa = dados_api.get("qsa", [])
                optante_simples = dados_api.get("opcao_pelo_simples", False)

                # Verification PGFN
                encontrados_pgfn = pd.DataFrame()
                tem_debito_pgfn = False
                valor_debito_str = "R$ 0,00"

                if not df_pgfn.empty:
                    encontrados_pgfn = df_pgfn[
                        df_pgfn["CPF/CNPJ"].str.replace(r"\D", "", regex=True) == cnpj_limpo
                    ]
                    if len(encontrados_pgfn) > 0:
                        tem_debito_pgfn = True
                        valor_debito_str = encontrados_pgfn.iloc[0].get("Valor Total", "R$ 0,00")

                # ==============================================================================
                # BLOCO TRIBUTÁRIO: OPORTUNIDADES DE EDITAIS PGFN
                # ==============================================================================
                if tem_debito_pgfn:
                    text_wa = urllib.parse.quote(
                        f"Olá! Fiz o diagnóstico no sistema do CNPJ {cnpj_input} ({razao_social}) "
                        f"e identifiquei débitos inscritos na PGFN no valor de R$ {valor_debito_str}. "
                        f"Gostaria de solicitar um estudo de enquadramento nos Editais de Transação Tributária."
                    )
                    link_wa = f"https://wa.me/{NUMERO_WHATSAPP}?text={text_wa}"

                    st.markdown(
                        f"""
                    <div class="alert-pgfn">
                        <div style="display: flex; justify-content: space-between; align-items: flex-start; flex-wrap: wrap; gap: 20px;">
                            <div style="flex: 3;">
                                <span style="background: #ef4444; color: white; font-size: 11px; font-weight: 800; padding: 4px 10px; border-radius: 4px;">DÍVIDA ATIVA IDENTIFICADA</span>
                                <h3 style="margin: 8px 0; font-size: 22px; color: #ffffff;">{razao_social}</h3>
                                <p style="margin: 0 0 12px 0; color: #cbd5e1; font-size: 15px;">
                                    Total Inscrito na Dívida Ativa da União: <b style="color: #f87171; font-size: 20px;">R$ {valor_debito_str}</b>
                                </p>
                                <div style="font-size: 13px; color: #94a3b8; line-height: 1.5;">
                                    ⚠️ Esta empresa possui pendência fiscal que impede a emissão de CND e certidões negativas para licitações e operações de crédito.
                                </div>
                            </div>
                            <div style="flex: 1; text-align: right; min-width: 250px;">
                                <a href="{link_wa}" target="_blank" class="btn-wa" style="width: 100%;">
                                    💬 Solicitar Estudo de Enquadramento
                                </a>
                            </div>
                        </div>
                    </div>
                    """,
                        unsafe_allow_html=True,
                    )

                    st.markdown("### 🎯 Simulador de Editais Elegíveis (Transação PGFN)")
                    st.caption(
                        "Abaixo estão as modalidades de negociação da PGFN aplicáveis a este perfil de empresa:"
                    )

                    cols_ed = st.columns(len(EDITAIS_PGFN))
                    for idx, edital in enumerate(EDITAIS_PGFN):
                        with cols_ed[idx]:
                            st.markdown(
                                f"""
                            <div class="edital-box">
                                <div style="font-weight: 700; color: #1e3a8a; font-size: 14px; margin-bottom: 6px;">{edital['nome']}</div>
                                <div style="font-size: 12px; color: #047857; font-weight: 700; margin-bottom: 4px;">✅ {edital['desconto_max']}</div>
                                <div style="font-size: 12px; color: #3b82f6; font-weight: 600; margin-bottom: 8px;">🗓️ {edital['prazo_max']}</div>
                                <div style="font-size: 11px; color: #64748b;">{edital['elegibilidade']}</div>
                            </div>
                            """,
                                unsafe_allow_html=True,
                            )
                    st.write("")
                else:
                    st.success(
                        "🟢 **SITUAÇÃO REGULAR NA PGFN**: Nenhum débito inscrito na Dívida Ativa da União foi localizado para este CNPJ."
                    )

                # ==============================================================================
                # DETALHAMENTO EM ABAS
                # ==============================================================================
                tab_cartao, tab_qsa, tab_pgfn_detalhes, tab_cnds = st.tabs(
                    [
                        "📋 Cadastro Completo (RFB)",
                        "👥 Quadro Societário (QSA)",
                        "⚖️ Detalhamento PGFN",
                        "🌐 Mapeamento de CNDs",
                    ]
                )

                with tab_cartao:
                    st.markdown(
                        f"""
                    <div style="background: white; padding: 20px; border-radius: 8px; border: 1px solid #cbd5e1;">
                        <div style="display: flex; flex-wrap: wrap;">
                            <div class="field-box" style="flex: 2;"><div class="field-label">Razão Social</div><div class="field-value">{razao_social}</div></div>
                            <div class="field-box" style="flex: 2;"><div class="field-label">Nome Fantasia</div><div class="field-value">{nome_fantasia}</div></div>
                            <div class="field-box" style="flex: 1;"><div class="field-label">Porte</div><div class="field-value">{porte}</div></div>
                        </div>
                        <div style="display: flex; flex-wrap: wrap;">
                            <div class="field-box" style="flex: 1;"><div class="field-label">Situação Cadastral</div><div class="field-value">{situacao}</div></div>
                            <div class="field-box" style="flex: 1;"><div class="field-label">UF</div><div class="field-value">{uf}</div></div>
                            <div class="field-box" style="flex: 1;"><div class="field-label">Optante Simples</div><div class="field-value">{"SIM" if optante_simples else "NÃO"}</div></div>
                        </div>
                    </div>
                    """,
                        unsafe_allow_html=True,
                    )

                with tab_qsa:
                    if qsa:
                        st.table(pd.DataFrame(qsa))
                    else:
                        st.info("Nenhum sócio ou administrador constante na base pública.")

                with tab_pgfn_detalhes:
                    if tem_debito_pgfn:
                        st.dataframe(encontrados_pgfn, use_container_width=True, hide_index=True)
                    else:
                        st.info("Nenhum débito na PGFN cadastrado nesta base.")

                with tab_cnds:
                    if not df_cnds.empty:
                        filtro = (
                            df_cnds[df_cnds["UF"] == uf]
                            if ("UF" in df_cnds.columns and uf)
                            else df_cnds
                        )
                        st.dataframe(filtro.head(15), use_container_width=True, hide_index=True)

# ==============================================================================
# RODAPÉ DE TRANSPARÊNCIA E CONFORMIDADE
# ==============================================================================
st.markdown("---")
st.markdown(
    f"""
<div style="background-color: #ffffff; border: 1px solid #cbd5e1; border-radius: 8px; padding: 16px; font-size: 12px; color: #475569; line-height: 1.6;">
    <b>AVISO LEGAL DE TRANSPARÊNCIA E PRIVACIDADE:</b><br>
    As informações apresentadas são públicas e não confidenciais, obtidas em estrita conformidade com o 
    <b>Decreto nº 8.777/2016 (Política de Dados Abertos)</b> e a <b>Lei nº 12.527/2011 (Lei de Acesso à Informação)</b>. 
    Este portal é gerido por <b>{NOME_ESCRITORIO}</b> como ferramenta de diagnóstico e assessoria tributária em regularização fiscal e transação junto à PGFN e Receita Federal.
</div>
""",
    unsafe_allow_html=True,
)
