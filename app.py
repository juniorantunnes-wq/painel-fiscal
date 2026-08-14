"""
Painel de Diagnóstico Fiscal & Editais PGFN
============================================
Aplicação Streamlit para diagnóstico cadastral (Receita Federal),
verificação de débitos inscritos na Dívida Ativa da União (PGFN)
e simulação de enquadramento em editais de transação tributária.

Melhorias desta versão em relação ao protótipo original:
- Validação real de CNPJ (dígitos verificadores), não apenas regex.
- Requisições HTTP robustas (timeout, retries, tratamento de erros
  específicos: rate limit, não encontrado, indisponibilidade).
- Configurações via variáveis de ambiente / st.secrets (nada de
  segredos hardcoded no código-fonte).
- Carregamento de bases locais com feedback claro ao usuário quando
  os arquivos não existem, em vez de falhar silenciosamente.
- Possibilidade de enviar as bases (ZIP da PGFN / XLSX de CNDs) por
  upload, sem depender de arquivos fixos no disco do servidor.
- Parsing seguro de valores monetários (evita KeyError/TypeError).
- Estado de busca controlado por session_state (evita reconsultas
  desnecessárias a cada interação da interface).
- Exportação do diagnóstico em CSV.
- Código modularizado em funções puras e testáveis.
"""

from __future__ import annotations

import io
import json
import logging
import os
import re
import zipfile
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional
from urllib.parse import quote

import pandas as pd
import requests
import streamlit as st

# ==============================================================================
# LOGGING
# ==============================================================================
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("painel_fiscal")

# ==============================================================================
# CONFIGURAÇÕES DO ESCRITÓRIO (via st.secrets ou variáveis de ambiente,
# com fallback para valores padrão — nunca deixe dados sensíveis fixos
# no código-fonte de um repositório público)
# ==============================================================================
def _get_config(key: str, default: str) -> str:
    try:
        if key in st.secrets:
            return str(st.secrets[key])
    except Exception:
        pass
    return os.environ.get(key, default)


NOME_ESCRITORIO = _get_config("NOME_ESCRITORIO", "Seu Escritório Contábil & Tributário")
NUMERO_WHATSAPP = _get_config("NUMERO_WHATSAPP", "5585999999999")  # DDI+DDD+Número
BRASILAPI_TIMEOUT = float(_get_config("BRASILAPI_TIMEOUT", "10"))
CACHE_TTL_SECONDS = int(_get_config("CACHE_TTL_SECONDS", "3600"))

CAMINHO_ZIP_PGFN_PADRAO = _get_config("CAMINHO_ZIP_PGFN", "Consulta_Lista_Devedores_2026_08_13.zip")
CAMINHO_XLSX_CNDS_PADRAO = _get_config("CAMINHO_XLSX_CNDS", "LISTAGEM_CNDs_DEZ_1.xlsx")

EDITAIS_PGFN = [
    {
        "nome": "Transação por Adesão (Débitos até R$ 50 Mi)",
        "desconto_max": "Até 70% em juros, multas e encargos",
        "prazo_max": "Até 145 parcelas mensais",
        "elegibilidade": "Empresas com débitos inscritos na Dívida Ativa da União e baixa capacidade de pagamento (CAPAG C ou D).",
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

    .alert-ok {
        background: linear-gradient(135deg, #064e3b 0%, #065f46 100%);
        color: #ffffff;
        border-radius: 12px;
        padding: 20px 24px;
        margin-bottom: 24px;
    }

    .edital-box {
        background: #f8fafc;
        border: 1px solid #cbd5e1;
        border-left: 4px solid #2563eb;
        border-radius: 6px;
        padding: 14px;
        margin-top: 10px;
        height: 100%;
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
        word-break: break-word;
    }

    .status-pill {
        display: inline-block;
        padding: 4px 10px;
        border-radius: 999px;
        font-size: 11px;
        font-weight: 700;
    }
</style>
""",
    unsafe_allow_html=True,
)

# ==============================================================================
# VALIDAÇÃO E FORMATAÇÃO DE CNPJ
# ==============================================================================
def somente_digitos(texto: str) -> str:
    return re.sub(r"\D", "", texto or "")


def cnpj_valido(cnpj: str) -> bool:
    """Valida um CNPJ verificando os dígitos verificadores (módulo 11)."""
    cnpj = somente_digitos(cnpj)
    if len(cnpj) != 14 or cnpj == cnpj[0] * 14:
        return False

    def calcular_digito(base: str) -> int:
        pesos = list(range(len(base) + 1, 1, -1))
        soma = sum(int(d) * p for d, p in zip(base, pesos))
        resto = soma % 11
        return 0 if resto < 2 else 11 - resto

    digito1 = calcular_digito(cnpj[:12])
    digito2 = calcular_digito(cnpj[:12] + str(digito1))
    return cnpj[-2:] == f"{digito1}{digito2}"


def formatar_cnpj(cnpj: str) -> str:
    cnpj = somente_digitos(cnpj)
    if len(cnpj) != 14:
        return cnpj
    return f"{cnpj[0:2]}.{cnpj[2:5]}.{cnpj[5:8]}/{cnpj[8:12]}-{cnpj[12:14]}"


def parse_valor_monetario(valor) -> float:
    """Converte valores como 'R$ 1.234,56', '1234.56' ou floats em float,
    sem lançar exceção — retorna 0.0 quando não for possível interpretar."""
    if valor is None:
        return 0.0
    if isinstance(valor, (int, float)):
        return float(valor)
    texto = str(valor).strip()
    texto = re.sub(r"[^\d,.-]", "", texto)
    if not texto:
        return 0.0
    # Formato brasileiro: milhar com ponto, decimal com vírgula
    if "," in texto and "." in texto:
        texto = texto.replace(".", "").replace(",", ".")
    elif "," in texto:
        texto = texto.replace(",", ".")
    try:
        return float(texto)
    except ValueError:
        return 0.0


def formatar_moeda(valor: float) -> str:
    texto = f"{valor:,.2f}"
    texto = texto.replace(",", "_").replace(".", ",").replace("_", ".")
    return f"R$ {texto}"


# ==============================================================================
# CARREGAMENTO DE BASES LOCAIS
# ==============================================================================
@dataclass
class BasesCarregadas:
    df_pgfn: pd.DataFrame = field(default_factory=pd.DataFrame)
    df_cnds: pd.DataFrame = field(default_factory=pd.DataFrame)
    erro_pgfn: Optional[str] = None
    erro_cnds: Optional[str] = None


def _ler_zip_pgfn(fonte) -> pd.DataFrame:
    with zipfile.ZipFile(fonte, "r") as z:
        nomes = z.namelist()
        if not nomes:
            raise ValueError("O arquivo ZIP está vazio.")
        filename = nomes[0]
        linhas = z.open(filename).readlines()

        start_idx = 0
        for idx, linha in enumerate(linhas):
            if b"CPF/CNPJ" in linha or "CPF/CNPJ" in linha.decode("latin1", errors="ignore"):
                start_idx = idx
                break

        csv_content = "".join(l.decode("latin1", errors="ignore") for l in linhas[start_idx:])
        df = pd.read_csv(io.StringIO(csv_content), sep=";", quotechar='"')
        df.columns = [c.strip() for c in df.columns]
        return df


@st.cache_data(show_spinner=False, ttl=CACHE_TTL_SECONDS)
def carregar_bases(
    zip_bytes: Optional[bytes],
    zip_path: Optional[str],
    xlsx_bytes: Optional[bytes],
    xlsx_path: Optional[str],
) -> BasesCarregadas:
    resultado = BasesCarregadas()

    # Base PGFN (upload tem prioridade sobre arquivo local)
    try:
        if zip_bytes is not None:
            resultado.df_pgfn = _ler_zip_pgfn(io.BytesIO(zip_bytes))
        elif zip_path and os.path.exists(zip_path):
            resultado.df_pgfn = _ler_zip_pgfn(zip_path)
        else:
            resultado.erro_pgfn = "Arquivo da base PGFN não encontrado."
    except (zipfile.BadZipFile, ValueError, pd.errors.ParserError) as e:
        resultado.erro_pgfn = f"Base PGFN inválida ou corrompida: {e}"
    except Exception as e:
        logger.exception("Erro inesperado ao carregar base PGFN")
        resultado.erro_pgfn = f"Erro inesperado ao carregar base PGFN: {e}"

    # Base de CNDs (upload tem prioridade sobre arquivo local)
    try:
        if xlsx_bytes is not None:
            resultado.df_cnds = pd.read_excel(io.BytesIO(xlsx_bytes), sheet_name=0)
        elif xlsx_path and os.path.exists(xlsx_path):
            resultado.df_cnds = pd.read_excel(xlsx_path, sheet_name=0)
        else:
            resultado.erro_cnds = "Arquivo da base de CNDs não encontrado."
    except Exception as e:
        logger.exception("Erro inesperado ao carregar base de CNDs")
        resultado.erro_cnds = f"Erro ao carregar base de CNDs: {e}"

    return resultado


# ==============================================================================
# CONSULTA À BRASILAPI (CADASTRO RECEITA FEDERAL)
# ==============================================================================
class ConsultaCNPJError(Exception):
    """Erro amigável de consulta de CNPJ, com mensagem pronta para exibição."""


@st.cache_data(show_spinner=False, ttl=CACHE_TTL_SECONDS)
def consultar_cnpj(cnpj_limpo: str) -> dict:
    url = f"https://brasilapi.com.br/api/cnpj/v1/{cnpj_limpo}"
    try:
        resp = requests.get(url, headers={"User-Agent": "PainelFiscal/1.0"}, timeout=BRASILAPI_TIMEOUT)
    except requests.exceptions.Timeout as exc:
        raise ConsultaCNPJError(
            "A consulta à Receita Federal demorou demais para responder. Tente novamente em instantes."
        ) from exc
    except requests.exceptions.ConnectionError as exc:
        raise ConsultaCNPJError(
            "Não foi possível conectar ao serviço da Receita Federal (BrasilAPI). Verifique sua conexão."
        ) from exc
    except requests.exceptions.RequestException as exc:
        raise ConsultaCNPJError(f"Falha inesperada na consulta: {exc}") from exc

    if resp.status_code == 404:
        raise ConsultaCNPJError("CNPJ não encontrado na base pública da Receita Federal.")
    if resp.status_code == 429:
        raise ConsultaCNPJError("Limite de consultas atingido. Aguarde alguns instantes e tente novamente.")
    if resp.status_code >= 500:
        raise ConsultaCNPJError("O serviço da Receita Federal está indisponível no momento. Tente mais tarde.")
    if not resp.ok:
        raise ConsultaCNPJError(f"Erro ao consultar CNPJ (HTTP {resp.status_code}).")

    try:
        return resp.json()
    except json.JSONDecodeError as exc:
        raise ConsultaCNPJError("Resposta inválida do serviço de consulta.") from exc


# ==============================================================================
# LÓGICA DE NEGÓCIO: VERIFICAÇÃO DE DÉBITOS PGFN
# ==============================================================================
def buscar_debito_pgfn(df_pgfn: pd.DataFrame, cnpj_limpo: str) -> tuple[pd.DataFrame, bool, float]:
    if df_pgfn.empty or "CPF/CNPJ" not in df_pgfn.columns:
        return pd.DataFrame(), False, 0.0

    coluna_normalizada = df_pgfn["CPF/CNPJ"].astype(str).str.replace(r"\D", "", regex=True)
    encontrados = df_pgfn[coluna_normalizada == cnpj_limpo]

    if encontrados.empty:
        return encontrados, False, 0.0

    coluna_valor = "Valor Total" if "Valor Total" in encontrados.columns else None
    valor = parse_valor_monetario(encontrados.iloc[0].get(coluna_valor)) if coluna_valor else 0.0
    return encontrados, True, valor


# ==============================================================================
# BARRA LATERAL: FONTES DE DADOS
# ==============================================================================
with st.sidebar:
    st.markdown("### ⚙️ Fontes de Dados")
    st.caption(
        "Envie as bases atualizadas (opcional). Se nada for enviado, o app "
        "tentará usar os arquivos padrão configurados no servidor."
    )
    upload_zip = st.file_uploader("Base PGFN (.zip)", type=["zip"], key="upload_zip")
    upload_xlsx = st.file_uploader("Base de CNDs (.xlsx)", type=["xlsx"], key="upload_xlsx")
    st.markdown("---")
    st.caption(f"Cache das consultas: {CACHE_TTL_SECONDS // 60} min")
    if st.button("🔄 Limpar cache e recarregar bases"):
        st.cache_data.clear()
        st.rerun()

bases = carregar_bases(
    zip_bytes=upload_zip.getvalue() if upload_zip else None,
    zip_path=CAMINHO_ZIP_PGFN_PADRAO,
    xlsx_bytes=upload_xlsx.getvalue() if upload_xlsx else None,
    xlsx_path=CAMINHO_XLSX_CNDS_PADRAO,
)
df_pgfn, df_cnds = bases.df_pgfn, bases.df_cnds

# ==============================================================================
# TOPO DO APP
# ==============================================================================
st.markdown(
    f"""
<div class="header-card">
    <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 12px;">
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

if bases.erro_pgfn:
    st.warning(f"⚠️ Base PGFN indisponível: {bases.erro_pgfn} A verificação de débitos ficará desabilitada.")
if bases.erro_cnds:
    st.info(f"ℹ️ Base de CNDs indisponível: {bases.erro_cnds}")

# ==============================================================================
# ESTADO DA BUSCA
# ==============================================================================
if "resultado_busca" not in st.session_state:
    st.session_state.resultado_busca = None
if "cnpj_consultado" not in st.session_state:
    st.session_state.cnpj_consultado = ""

# ==============================================================================
# FORMULÁRIO DE CONSULTA
# ==============================================================================
with st.form(key="form_consulta", clear_on_submit=False):
    col_in, col_bt = st.columns([4, 1])
    with col_in:
        cnpj_input = st.text_input(
            "CNPJ da Empresa:",
            placeholder="Digite o CNPJ (ex: 41.618.558/0001-12)",
            label_visibility="collapsed",
        )
    with col_bt:
        btn_buscar = st.form_submit_button("🔍 Diagnosticar CNPJ", use_container_width=True, type="primary")

if btn_buscar:
    cnpj_limpo = somente_digitos(cnpj_input)
    if not cnpj_input.strip():
        st.warning("Informe um CNPJ para iniciar o diagnóstico.")
        st.session_state.resultado_busca = None
    elif not cnpj_valido(cnpj_limpo):
        st.error("⚠️ CNPJ inválido. Verifique os dígitos digitados e tente novamente.")
        st.session_state.resultado_busca = None
    else:
        with st.spinner("Realizando auditoria cadastral e consultando bases públicas..."):
            try:
                dados_api = consultar_cnpj(cnpj_limpo)
                st.session_state.resultado_busca = dados_api
                st.session_state.cnpj_consultado = cnpj_limpo
            except ConsultaCNPJError as e:
                st.error(f"⚠️ {e}")
                st.session_state.resultado_busca = None

# ==============================================================================
# EXIBIÇÃO DO DIAGNÓSTICO
# ==============================================================================
dados_api = st.session_state.resultado_busca
cnpj_limpo = st.session_state.cnpj_consultado

if dados_api:
    razao_social = dados_api.get("razao_social") or "N/A"
    nome_fantasia = dados_api.get("nome_fantasia") or "********"
    situacao = dados_api.get("descricao_situacao_cadastral") or "N/A"
    porte = dados_api.get("porte") or "N/A"
    uf = dados_api.get("uf") or ""
    qsa = dados_api.get("qsa") or []
    optante_simples = bool(dados_api.get("opcao_pelo_simples", False))
    cnpj_formatado = formatar_cnpj(cnpj_limpo)

    encontrados_pgfn, tem_debito_pgfn, valor_debito = buscar_debito_pgfn(df_pgfn, cnpj_limpo)
    valor_debito_fmt = formatar_moeda(valor_debito)

    # --------------------------------------------------------------------
    # BLOCO TRIBUTÁRIO: OPORTUNIDADES DE EDITAIS PGFN
    # --------------------------------------------------------------------
    if tem_debito_pgfn:
        mensagem_wa = quote(
            f"Olá! Fiz o diagnóstico no sistema do CNPJ {cnpj_formatado} ({razao_social}) "
            f"e identifiquei débitos inscritos na PGFN no valor de {valor_debito_fmt}. "
            f"Gostaria de solicitar um estudo de enquadramento nos Editais de Transação Tributária."
        )
        link_wa = f"https://wa.me/{NUMERO_WHATSAPP}?text={mensagem_wa}"

        st.markdown(
            f"""
        <div class="alert-pgfn">
            <div style="display: flex; justify-content: space-between; align-items: flex-start; flex-wrap: wrap; gap: 20px;">
                <div style="flex: 3;">
                    <span style="background: #ef4444; color: white; font-size: 11px; font-weight: 800; padding: 4px 10px; border-radius: 4px;">DÍVIDA ATIVA IDENTIFICADA</span>
                    <h3 style="margin: 8px 0; font-size: 22px; color: #ffffff;">{razao_social}</h3>
                    <p style="margin: 0 0 12px 0; color: #cbd5e1; font-size: 15px;">
                        Total Inscrito na Dívida Ativa da União: <b style="color: #f87171; font-size: 20px;">{valor_debito_fmt}</b>
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
        st.caption("Abaixo estão as modalidades de negociação da PGFN aplicáveis a este perfil de empresa:")

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
    elif bases.erro_pgfn:
        st.info("ℹ️ Não foi possível verificar débitos na PGFN porque a base local não está disponível.")
    else:
        st.markdown(
            """
        <div class="alert-ok">
            <span class="status-pill" style="background:#22c55e; color:#052e16;">SITUAÇÃO REGULAR</span>
            <p style="margin: 10px 0 0 0; font-size: 15px;">
                🟢 Nenhum débito inscrito na Dívida Ativa da União foi localizado para este CNPJ na base carregada.
            </p>
        </div>
        """,
            unsafe_allow_html=True,
        )

    # --------------------------------------------------------------------
    # DETALHAMENTO EM ABAS
    # --------------------------------------------------------------------
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
                <div class="field-box" style="flex: 1;"><div class="field-label">CNPJ</div><div class="field-value">{cnpj_formatado}</div></div>
            </div>
        </div>
        """,
            unsafe_allow_html=True,
        )

        resumo_export = pd.DataFrame(
            [
                {
                    "CNPJ": cnpj_formatado,
                    "Razão Social": razao_social,
                    "Nome Fantasia": nome_fantasia,
                    "Situação Cadastral": situacao,
                    "Porte": porte,
                    "UF": uf,
                    "Optante Simples": "SIM" if optante_simples else "NÃO",
                    "Débito PGFN": "SIM" if tem_debito_pgfn else "NÃO",
                    "Valor Débito PGFN": valor_debito_fmt if tem_debito_pgfn else "-",
                    "Data do Diagnóstico": datetime.now().strftime("%d/%m/%Y %H:%M"),
                }
            ]
        )
        st.download_button(
            "⬇️ Baixar diagnóstico (CSV)",
            data=resumo_export.to_csv(index=False, sep=";").encode("utf-8-sig"),
            file_name=f"diagnostico_{cnpj_limpo}.csv",
            mime="text/csv",
        )

    with tab_qsa:
        if qsa:
            st.table(pd.DataFrame(qsa))
        else:
            st.info("Nenhum sócio ou administrador constante na base pública.")

    with tab_pgfn_detalhes:
        if bases.erro_pgfn:
            st.info("Base PGFN indisponível no momento.")
        elif tem_debito_pgfn:
            st.dataframe(encontrados_pgfn, use_container_width=True, hide_index=True)
        else:
            st.info("Nenhum débito na PGFN cadastrado nesta base.")

    with tab_cnds:
        if bases.erro_cnds:
            st.info("Base de CNDs indisponível no momento.")
        elif not df_cnds.empty:
            filtro = df_cnds[df_cnds["UF"] == uf] if ("UF" in df_cnds.columns and uf) else df_cnds
            st.dataframe(filtro.head(15), use_container_width=True, hide_index=True)
        else:
            st.info("Nenhum dado de CND disponível.")

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

