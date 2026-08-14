import streamlit as st
import pandas as pd
import zipfile
import re
import urllib.request
import json

st.set_page_config(page_title="Painel de Inteligência Fiscal Completo", layout="wide")

st.title("🛡️ Sistema de Consulta Fiscal, Cadastral & Dívida Ativa")
st.markdown("Raio-X completo com **Quadro de Sócios (QSA)**, **CNAEs**, **Contatos** e débitos na **PGFN**.")

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
cnpj_input = st.text_input("Digite o CNPJ para consulta completa:", placeholder="Ex: 31.945.912/0001-60")

if st.button("🔍 Executar Consulta Completa"):
    if cnpj_input:
        cnpj_limpo = re.sub(r'\D', '', cnpj_input)
        
        # 1. Consulta Completa em Tempo Real
        dados_api = {}
        try:
            url = f"https://brasilapi.com.br/api/cnpj/v1/{cnpj_limpo}"
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req) as resp:
                dados_api = json.loads(resp.read().decode('utf-8'))
        except Exception:
            st.error("Não foi possível carregar os dados cadastrais. Verifique o CNPJ digitado.")

        if dados_api:
            # Extração dos dados
            razao_social = dados_api.get("razao_social", "N/A")
            nome_fantasia = dados_api.get("nome_fantasia", "Não informado")
            situacao = dados_api.get("descricao_situacao_cadastral", "N/A")
            data_situacao = dados_api.get("data_situacao_cadastral", "N/A")
            data_inicio = dados_api.get("data_inicio_atividade", "N/A")
            capital_social = dados_api.get("capital_social", 0.0)
            
            # Endereço e Contato
            logradouro = dados_api.get("logradouro", "")
            numero = dados_api.get("numero", "")
            bairro = dados_api.get("bairro", "")
            municipio = dados_api.get("municipio", "")
            uf = dados_api.get("uf", "")
            cep = dados_api.get("cep", "")
            email = dados_api.get("email", "Não informado")
            ddd_tel = f"({dados_api.get('ddd_telefone_1', '')[:2]}) {dados_api.get('ddd_telefone_1', '')[2:]}" if dados_api.get('ddd_telefone_1') else "Não informado"

            # CNAE
            cnae_principal_cod = dados_api.get("cnae_fiscal", "")
            cnae_principal_desc = dados_api.get("cnae_fiscal_descricao", "")
            cnaes_secundarios = dados_api.get("cnaes_secundarios", [])

            # Regimes
            optante_simples = "SIM" if dados_api.get("opcao_pelo_simples") else "NÃO"
            optante_mei = "SIM" if dados_api.get("opcao_pelo_mei") else "NÃO"

            # --- APRESENTAÇÃO ---
            st.subheader(f"🏢 {razao_social}")
            if nome_fantasia and nome_fantasia != "Não informado":
                st.caption(f"**Nome Fantasia:** {nome_fantasia}")

            c1, c2, c3, c4, c5 = st.columns(5)
            c1.metric("Situação Cadastral", situacao)
            c2.metric("Data da Situação", data_situacao)
            c3.metric("Data de Abertura", data_inicio)
            c4.metric("Optante Simples", optante_simples)
            c5.metric("Capital Social", f"R$ {capital_social:,.2f}")

            st.divider()

            # Endereço e Contato
            col_end, col_cont = st.columns(2)
            with col_end:
                st.write("### 📍 Endereço Cadastrado")
                st.write(f"**Logradouro:** {logradouro}, Nº {numero}")
                st.write(f"**Bairro:** {bairro} | **CEP:** {cep}")
                st.write(f"**Cidade/UF:** {municipio} - {uf}")

            with col_cont:
                st.write("### 📞 Contato Registrado")
                st.write(f"**E-mail:** {email}")
                st.write(f"**Telefone:** {ddd_tel}")

            st.divider()

            # Quadro de Sócios (QSA)
            st.write("### 👥 Quadro de Sócios e Administradores (QSA)")
            qsa = dados_api.get("qsa", [])
            if qsa:
                df_qsa = pd.DataFrame(qsa)
                df_qsa = df_qsa.rename(columns={
                    'nome_socio': 'Nome do Sócio / Administrador',
                    'qualificacao_socio': 'Qualificação / Cargo',
                    'faixa_etaria': 'Faixa Etária'
                })
                cols_exibir = [c for c in ['Nome do Sócio / Administrador', 'Qualificação / Cargo', 'Faixa Etária'] if c in df_qsa.columns]
                st.dataframe(df_qsa[cols_exibir], use_container_width=True)
            else:
                st.info("Nenhum sócio ou administrador listado para este CNPJ.")

            st.divider()

            # Atividades Econômicas (CNAE)
            st.write("### 💼 Atividades Econômicas (CNAE)")
            st.write(f"**Atividade Principal:** {cnae_principal_cod} - {cnae_principal_desc}")
            if cnaes_secundarios:
                with st.expander(f"Ver {len(cnaes_secundarios)} Atividades Secundárias"):
                    for cnae in cnaes_secundarios:
                        st.write(f"• **{cnae.get('codigo')}** - {cnae.get('descricao')}")

        st.divider()

        # 2. Consulta PGFN
        st.subheader("⚠️ Situação na Dívida Ativa da União (PGFN)")
        encontrados = pd.DataFrame()
        if not df_pgfn.empty:
            encontrados = df_pgfn[df_pgfn['CPF/CNPJ'].str.replace(r'\D', '', regex=True) == cnpj_limpo]

        if len(encontrados) > 0:
            row = encontrados.iloc[0]
            st.error(f"🔴 **DÉBITO ENCONTRADO!**\n\n- **Razão Social na PGFN:** {row['Nome']}\n- **Valor Inscrito:** R$ {row['Valor Total']}")
        else:
            st.success("🟢 **REGULAR!** Nenhum débito inscrito na Dívida Ativa da União encontrado nesta base.")

        st.divider()

        # 3. Mapeamento de CNDs
        st.subheader(f"🌐 Mapeamento de CNDs para {uf} - {municipio}")
        if not df_cnds.empty:
            filtro_uf = df_cnds[df_cnds['UF'] == uf] if 'UF' in df_cnds.columns else df_cnds
            st.write(f"Total de CNDs e Robôs mapeados para este estado ({uf}): **{len(filtro_uf)}**")
            st.dataframe(filtro_uf[['ORIGEM', 'UF', 'TIPO']].head(10), use_container_width=True)
    else:
        st.warning("Por favor, digite um CNPJ válido.")
