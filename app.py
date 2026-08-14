# ==============================================================================
# RECURSO DE VALIDAÇÃO DE CAPAG E ENQUADRAMENTO DE EDITAL (MÓDULO DE SERVIÇO)
# ==============================================================================
class ServicoAnaliseTransacao:
    """
    Camada de Serviço (services/): Realiza a regra de negócio e o cruzamento 
    de dados cadastrais com a lista de devedores da PGFN.
    """

    def __init__(self, df_pgfn: pd.DataFrame):
        self.df_pgfn = df_pgfn

    def processar_cruzamento(self, cnpj_limpo: str, dados_cadastrais: dict) -> dict:
        resultado_pgfn = self._buscar_pgfn(cnpj_limpo)
        
        optante_simples = dados_cadastrais.get("opcao_pelo_simples", False)
        porte = dados_cadastrais.get("porte", "")
        situacao = dados_cadastrais.get("descricao_situacao_cadastral", "")
        
        elegivel_simples_mei = optante_simples or "MICROEMPRESA" in porte.upper() or "MEI" in porte.upper()

        return {
            "cnpj_analisado": cnpj_limpo,
            "razao_social": dados_cadastrais.get("razao_social"),
            "situacao_ativa": situacao.upper() == "ATIVA",
            "optante_simples_ou_mei": elegivel_simples_mei,
            "possui_debitos": resultado_pgfn["tem_debito"],
            "valor_total_debito": resultado_pgfn["valor_total"],
            "registros_detalhe": resultado_pgfn["registros"]
        }

    def _buscar_pgfn(self, cnpj_limpo: str) -> dict:
        if self.df_pgfn.empty:
            return {"tem_debito": False, "valor_total": "R$ 0,00", "registros": pd.DataFrame()}
            
        encontrados = self.df_pgfn[
            self.df_pgfn["CPF/CNPJ"].str.replace(r"\D", "", regex=True) == cnpj_limpo
        ]
        
        if len(encontrados) > 0:
            valor = encontrados.iloc[0].get("Valor Total", "R$ 0,00")
            return {"tem_debito": True, "valor_total": valor, "registros": encontrados}
            
        return {"tem_debito": False, "valor_total": "R$ 0,00", "registros": pd.DataFrame()}
