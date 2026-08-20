import pandas as pd
from difflib import SequenceMatcher


INSTITUICOES_MANUAIS = {
    "GAUS: Graph Analysis of Urban Systems":
        "Universidade Federal do Rio Grande do Sul (UFRGS)",

    "TopoGeo: a data model for elaboration of cadastral survey plans and land register documents":
        "Universidade Federal do Pernambuco (UFPE)",

    "Rule-based evolution of typed spatiotemporal objects":
        "Instituto Nacional de Pesquisas Espaciais (INPE)",

    "Desenvolvimento de Sistemas de Informaçăo Geográfica Cooperativos seguindo o Padrăo Modelo-Visăo-Controle":
        "Universidade Federal do Rio de Janeiro (UFRJ)",

    "Designing and Performing Geographic Analysis Processes with GISCASE":
        "Universidade Federal do Rio Grande do Sul (UFRGS)",
}

EDICOES_MANUAIS = {
    "GAUS: Graph Analysis of Urban Systems":
        "24a. Edição São José dos Campos 2023",

    "TopoGeo: a data model for elaboration of cadastral survey plans and land register documents":
        "22a. Edição On-Line 2021",

    "Rule-based evolution of typed spatiotemporal objects":
        "9a. Edição Campos do Jordão 2007",

    "Desenvolvimento de Sistemas de Informaçăo Geográfica Cooperativos seguindo o Padrăo Modelo-Visăo-Controle":
        "7a. Edição Campos do Jordão 2005",

    "Designing and Performing Geographic Analysis Processes with GISCASE":
        "7a. Edição Campos do Jordão 2005",
}


def corrigir_instituicoes_manuais(df):
    """
    Preenche instituições ausentes com base nas correções
    verificadas manualmente nos artigos.
    """
    for titulo, instituicao in INSTITUICOES_MANUAIS.items():
        mask = ((df["titulo"] == titulo) & (df["instituicoes"].isna() | (df["instituicoes"].fillna("").str.strip() == "")))
        df.loc[mask, "instituicoes"] = instituicao

    return df

def corrigir_edicoes_manuais(df):
    """
    Preenche edicoes ausentes com base nas correções
    verificadas manualmente nos artigos.
    """
    for titulo, edicao in EDICOES_MANUAIS.items():
        mask = ((df["titulo"] == titulo) & (df["edicao"].isna()(df["edicao"].fillna("").str.strip() == "")))
        df.loc[mask, "edicao"] = edicao

    return df



def similaridade_titulos(titulo1, titulo2):
    return SequenceMatcher(
        None,
        titulo1.lower().strip(),
        titulo2.lower().strip()
    ).ratio()



def limpar_artigos(df):
    df = df.copy()

    # padroniza nomes das colunas
    df.columns = (df.columns.str.strip().str.lower().str.replace(" ", "_"))

    # limpeza das strings
    colunas_texto = df.select_dtypes(include=["object", "string"]).columns

    for coluna in colunas_texto:
        df[coluna] = (df[coluna].astype("string").str.strip().str.replace(r"\s+", " ", regex=True))

    # padronizacao dos nulos
    valores_nulos = [
        "", " ", "NA", "N/A",
        "NULL", "null",
        "None", "none",
        "<NA>", "-"
    ]

    df = df.replace(valores_nulos, pd.NA)

    return df