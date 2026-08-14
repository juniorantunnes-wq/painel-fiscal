import streamlit as st
import pandas as pd
import zipfile
import re
import urllib.request
import json

st.set_page_config(page_title="Painel de Inteligência Fiscal", layout="wide")

st.title("🛡️ Sistema de Consulta Fiscal & Dívida Ativa")
st.markdown("Consulte dados cadastrais em **tempo real** e valide débitos inscritos na **PGFN**.")

# --- CARREGAR BASES LOCAIS ---
@st.cache_data
def carregar_bases():
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
        df_pgfn = pd.DataFrame()

    try:
        df_cnds = pd.read_excel("LISTAGEM_CNDs_DEZ_1.xlsx", sheet_name=0)
    except Exception:
        df_cnds = pd.DataFrame()
        
    return df_pgfn, df_cnds

df_pgfn, df_cnds = carregar_bases()

# --- CAMPO DE BUSCA ---
cnpj_input = st.text_input("Digite o CNPJ para consulta:", placeholder="Ex: 19.028.692/0001-04")

if st.button("🔍 Executar Consulta Completa"):
    if cnpj_input:
        cnpj_limpo = re.sub(r'\D', '', cnpj_input)
        
        # 1. Consulta em Tempo Real (BrasilAPI)
        dados_api = {}
        try:
            url = f"https://brasilapi.com.br/api/cnpj/v1/{cnpj_limpo}"
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req) as resp:
                dados_api = json.loads(resp.read().decode('utf-8'))
        except Exception:
            st.error("Não foi possível carregar os dados cadastrais em tempo real. Verifique o CNPJ.")

        razao_social = dados_api.get("razao_social", "Não informada")
        situacao = dados_api.get("descricao_situacao_cadastral", "Desconhecida")
        uf = dados_api.get("uf", "N/A")
        municipio = dados_api.get("municipio", "N/A")
        
        optante_simples = "SIM" if dados_api.get("opcao_pelo_simples") else "NÃO"
        optante_mei = "SIM" if dados_api.get("opcao_pelo_mei") else "NÃO"

        # 2. Consulta Real na Base da PGFN
        encontrados = pd.DataFrame()
        if not df_pgfn.empty:
            encontrados = df_pgfn[df_pgfn['CPF/CNPJ'].str.replace(r'\D', '', regex=True) == cnpj_limpo]

        # --- EXIBIÇÃO ---
        st.subheader(f"🏢 {razao_social}")
        
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Situação Cadastral", situacao)
        c2.metric("UF / Município", f"{uf} - {municipio}")
        c3.metric("Optante Simples", optante_simples)
        c4.metric("Optante MEI", optante_mei)

        st.divider()
        st.subheader("⚠️ Situação na Dívida Ativa da União (PGFN)")
        
        if len(encontrados) > 0:
            row = encontrados.iloc[0]
            st.error(f"🔴 **DÉBITO ENCONTRADO!**\n\n- **Empresa:** {row['Nome']}\n- **Valor Inscrito:** R$ {row['Valor Total']}")
        else:
            st.success("🟢 **REGULAR!** Nenhum débito inscrito na Dívida Ativa da União encontrado nesta base.")

        st.divider()
        st.subheader(f"🌐 Mapeamento de CNDs para {uf} - {municipio}")
        if not df_cnds.empty:
            filtro_uf = df_cnds[df_cnds['UF'] == uf] if 'UF' in df_cnds.columns else df_cnds
            st.write(f"Total de CNDs e Robôs mapeados para este estado ({uf}): **{len(filtro_uf)}**")
            st.dataframe(filtro_uf[['ORIGEM', 'UF', 'TIPO']].head(10), use_container_width=True)
    else:
        st.warning("Por favor, digite um CNPJ válido.")
