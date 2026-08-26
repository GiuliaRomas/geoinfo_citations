import pandas as pd
from difflib import SequenceMatcher

# -=-=-=-=-=- correcao das instituicoes dos artigos GEOINFO -=-=-=-=-=-=- #
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


# -=-=-=-=- calcula a similaridade entre dois textos -=-=-=-=- #
def similaridade_titulos(titulo1, titulo2):
    return SequenceMatcher(
        None,
        titulo1.lower().strip(),
        titulo2.lower().strip()
    ).ratio()


# -=-=-=-=- limpa artigos geoinfo -=-=-=-=- #
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



##### pré-processamento final #####
import re
import unicodedata
from difflib import SequenceMatcher

import numpy as np
import pandas as pd



# ============================================================
# LIMPEZA GERAL
# ============================================================

CARACTERES_INVISIVEIS = {
    "\u200b": "",
    "\u200e": "",
    "\ufeff": "",
    "\ufffc": "",
}


def remover_caracteres_invisiveis(texto):
    if pd.isna(texto):
        return texto

    texto = str(texto)

    for caractere, substituto in CARACTERES_INVISIVEIS.items():
        texto = texto.replace(caractere, substituto)

    return texto


def limpar_texto(texto):
    if pd.isna(texto):
        return pd.NA

    texto = str(texto).strip()

    if not texto:
        return pd.NA

    texto = remover_caracteres_invisiveis(texto)
    texto = unicodedata.normalize("NFC", texto)
    texto = re.sub(r"\s+", " ", texto)

    return texto


def limpar_artigos(df):
    df = df.copy()

    df.columns = (
        df.columns
        .str.strip()
        .str.lower()
        .str.replace(" ", "_")
    )

    valores_nulos = [
        "", " ", "NA", "N/A",
        "NULL", "null",
        "None", "none",
        "<NA>", "-"
    ]

    df = df.replace(valores_nulos, pd.NA)

    colunas_texto = df.select_dtypes(
        include=["object", "string"]
    ).columns

    for coluna in colunas_texto:
        df[coluna] = df[coluna].apply(limpar_texto)

    return df


# ============================================================
# CORREÇÃO DE ENCODING — GEOINFO
# ============================================================

CORRECOES_GEOINFO = {
    # palavras/sequências específicas
    "Săo": "São",
    "SŃo": "São",
    "simulańŃo": "simulação",
    "inundaçőes": "inundações",
    "Inteligęncia": "Inteligência",
    "climßticas": "climáticas",
    "Josķ": "José",
    "cientĒficos": "científicos",
    "Padr§es": "Padrões",
    "InformašŃo": "Informação",
    "Ant¶nio": "Antônio",
    "CŌmara": "Câmara",
    "Itajubß": "Itajubá",
    "PontifĒcia": "Pontifícia",
    "ClassificańŃo": "Classificação",
    "S¶nia VirgĒnia": "Sônia Virgínia",

    # casos específicos
    "Para´ıba": "Paraíba",
    "S˜ao": "São",
    "Cieˆncia": "Ciência",
    "contig³idade": "contiguidade",
    "Gonc¸alves": "Gonçalves",
    "Vic¸osa": "Viçosa",
    "Antōnio": "Antônio",
    "Jºnior": "Júnior",
    "Mendonþa": "Mendonça",
    "LaÚrcio": "Laércio",
    "SantarÕm": "Santarém",
    "estratÚgia": "estratégia",
    "GeracĖ": "Geração",
    "TriangulacĖ": "Triangulação",
    "S┤eries": "Séries",
    "Climatol┤ogicas": "Climatológicas",
    "M┤aquinas": "Máquinas",
    "geogrˇficos": "geográficos",
    "trajetˇria": "trajetória",
    "Intercāmbio": "Intercâmbio",
    "Van·cia": "Vânia",
    "J·nior": "Júnior",
    "Ara·jo": "Araújo",
    "L·bia": "Lúbia",
    "Desirče": "Desirée",
    "Universitč": "Université",
    "ParÃ": "Pará",
    "ClÃudia": "Cláudia",
    "Espíırito": "Espírito",
    "K—rting": "Körting",
    "JoŃo": "João",

    # símbolos
    "¢": "-",
    "§": "õ",
    "Ò": "ã",
    "Ý": "í",
    "į": "á",
    "ă": "ã"
}


CORRECOES_GEOINFO_RESIDUAIS = {
    "Sãao Paulo": "São Paulo",
    "Geracç ãao": "Geração de",
    "Triangulação ãao,": "Triangulação,",
    "Séeries": "Séries",
    "Méaquinas": "Máquinas",
    "travelerã trajectories": "travelers' trajectories",
    "distribuédo": "distribuido",
    "junēço": "junção",
    "Triangulacç ãao": "Triangulação",
}

MAPA_IDIOMAS = {
    "中文": "zh",
}

def aplicar_substituicoes(texto, substituicoes):
    for errado, correto in substituicoes.items():
        texto = texto.replace(errado, correto)

    return texto


def corrigir_combinantes(texto):
    texto = re.sub(r"(\w)\s+([̧́̃])", r"\1\2", texto)
    return unicodedata.normalize("NFC", texto)


def corrigir_encoding_geoinfo(texto):
    if pd.isna(texto):
        return texto

    texto = str(texto)
    texto = corrigir_combinantes(texto)
    texto = aplicar_substituicoes(
        texto,
        CORRECOES_GEOINFO
    )
    texto = aplicar_substituicoes(
        texto,
        CORRECOES_GEOINFO_RESIDUAIS
    )

    return unicodedata.normalize("NFC", texto)


def normalizar_texto(texto, corrigir_geoinfo=False):
    if pd.isna(texto):
        return texto

    texto = remover_caracteres_invisiveis(texto)
    texto = unicodedata.normalize("NFC", str(texto))

    if corrigir_geoinfo:
        texto = corrigir_encoding_geoinfo(texto)

    texto = unicodedata.normalize("NFC", texto)
    texto = re.sub(r"\s+", " ", texto).strip()

    return texto


def normalizar_colunas_textuais(df, colunas, corrigir_geoinfo=False):
    df = df.copy()

    for coluna in colunas:
        if coluna in df.columns:
            df[coluna] = df[coluna].apply(
                lambda x: normalizar_texto(
                    x,
                    corrigir_geoinfo=corrigir_geoinfo
                )
            )

    return df


# ============================================================
# PADRONIZAÇÃO DE CAMPOS
# ============================================================

def padronizar_ano(valor):
    if pd.isna(valor):
        return pd.NA

    try:
        valor = int(float(valor))

        if 1900 <= valor <= 2100:
            return valor

    except (ValueError, TypeError):
        pass

    return pd.NA


def padronizar_numero_edicao(valor):
    if pd.isna(valor):
        return pd.NA

    try:
        valor = int(float(valor))

        if valor > 0:
            return valor

    except (ValueError, TypeError):
        pass

    return pd.NA


def padronizar_doi(valor):
    if pd.isna(valor):
        return pd.NA

    valor = str(valor).strip().lower()

    if not valor:
        return pd.NA

    prefixos = (
        "https://doi.org/",
        "http://doi.org/",
        "https://dx.doi.org/",
        "http://dx.doi.org/",
        "doi:",
        "doi ",
    )

    for prefixo in prefixos:
        if valor.startswith(prefixo):
            valor = valor[len(prefixo):]

    return valor.strip() or pd.NA


def padronizar_openalex_id(valor):
    if pd.isna(valor):
        return pd.NA

    valor = str(valor).strip().rstrip("/")

    return valor or pd.NA


def limpar_url(valor):
    if pd.isna(valor):
        return pd.NA

    valor = str(valor).strip().rstrip("/")

    return valor or pd.NA


def padronizar_categoria(valor):
    if pd.isna(valor):
        return pd.NA

    valor = str(valor).strip().lower()

    return valor or pd.NA


def padronizar_status_openalex(valor):
    if pd.isna(valor):
        return pd.NA

    valor = str(valor).strip().upper()

    return valor or pd.NA


def padronizar_paises(valor):
    if pd.isna(valor):
        return pd.NA

    paises = [
        pais.strip().upper()
        for pais in str(valor).split(";")
        if pais.strip()
    ]

    paises = list(dict.fromkeys(paises))

    return "; ".join(paises) if paises else pd.NA


def padronizar_idioma(valor):
    if pd.isna(valor):
        return pd.NA

    valor = str(valor).strip().lower()

    if not valor:
        return pd.NA

    return MAPA_IDIOMAS.get(valor, valor)


# ============================================================
# CORREÇÕES MANUAIS
# ============================================================

def corrigir_instituicoes_manuais(df):
    df = df.copy()

    for titulo, instituicao in INSTITUICOES_MANUAIS.items():
        mascara = (
            (df["titulo"] == titulo)
            & df["instituicoes"].isna()
        )

        df.loc[mascara, "instituicoes"] = instituicao

    return df


def corrigir_edicoes_manuais(df):
    df = df.copy()

    for titulo, edicao in EDICOES_MANUAIS.items():
        mascara = (
            (df["titulo"] == titulo)
            & df["edicao"].isna()
        )

        df.loc[mascara, "edicao"] = edicao

    return df


# ============================================================
# ESTRUTURA
# ============================================================

def garantir_colunas(df, colunas):
    df = df.copy()

    for coluna in colunas:
        if coluna not in df.columns:
            df[coluna] = pd.NA

    return df[colunas]


def verificar_estrutura(dataframes):
    referencia = list(next(iter(dataframes.values())).columns)

    ok = True

    for nome, df in dataframes.items():
        if list(df.columns) != referencia:
            print(f"[ERRO] Estrutura diferente: {nome}")
            ok = False

    if ok:
        print("[OK] Estruturas padronizadas.")

    return ok


# ============================================================
# DIAGNÓSTICO
# ============================================================

def resumo_nulos(df, nome):
    resumo = pd.DataFrame({
        "nulos": df.isna().sum(),
        "percentual": (df.isna().mean() * 100).round(2),
    }).sort_values("nulos", ascending=False)

    print(f"\n{nome}")
    print(resumo)


def resumo_tipos(df, nome):
    resumo = pd.DataFrame({
        "tipo": df.dtypes.astype(str),
        "nulos": df.isna().sum(),
        "percentual_nulos": (
            df.isna().mean() * 100
        ).round(2),
        "valores_unicos": [
            df[col].nunique(dropna=True)
            for col in df.columns
        ],
    })

    print(f"\n{'=' * 60}")
    print(nome)
    print("=" * 60)
    print(resumo)


def caracteres_nao_ascii(df, colunas):
    resultados = {}

    for coluna in colunas:
        if coluna not in df.columns:
            continue

        caracteres = set()

        for valor in df[coluna].dropna().astype(str):
            caracteres.update(
                caractere
                for caractere in valor
                if ord(caractere) > 127
            )

        if caracteres:
            resultados[coluna] = sorted(caracteres)

    return resultados


def encontrar_valores_com_caracteres(
    df,
    coluna,
    caracteres
):
    if coluna not in df.columns:
        return pd.Series(dtype="object")

    mascara = df[coluna].fillna("").astype(str).apply(
        lambda texto: any(
            caractere in texto
            for caractere in caracteres
        )
    )

    return df.loc[mascara, coluna]


# ============================================================
# UTILITÁRIOS
# ============================================================

def similaridade_titulos(titulo1, titulo2):
    return SequenceMatcher(
        None,
        titulo1.lower().strip(),
        titulo2.lower().strip()
    ).ratio()




# ============================================================
# INSTITUIÇÕES — FORMATO NUMERADO (GEOINFO)
# ============================================================

def dividir_instituicoes_numeradas(texto):
    """
    Formato bruto do GEOINFO: "1 Instituição A 2 Instituição B 3 Instituição A"
    (um segmento por autor, numerado, sem separador ';'). Divide
    pelos marcadores numéricos e remove repetições, produzindo o
    formato "; "-separado usado no resto do pipeline.
    """
    if pd.isna(texto):
        return texto

    texto = str(texto)
    partes = re.split(r"\b\d+\s+", texto)
    partes = [p.strip() for p in partes if p.strip()]
    partes_unicas = list(dict.fromkeys(partes))

    return "; ".join(partes_unicas) if partes_unicas else pd.NA


# ============================================================
# AUTORES — REPARO DE SPLIT INCOMPLETO (SCHOLAR)
# ============================================================

def reparar_autores_nao_divididos(valor):
    """
    Alguns registros do Scholar escapam do split "Autores - Veículo,
    Ano" quando o travessão usado é um en/em dash em vez de hífen
    comum. Detecta e corta novamente.
    """
    if pd.isna(valor):
        return valor
    valor = str(valor)
    for separador in [" - ", " – ", " — "]:
        if separador in valor:
            return valor.split(separador)[0].strip()
    return valor


# ============================================================
# MAPAS DE PADRONIZAÇÃO — INSTITUIÇÕES E AUTORES
# (variações de grafia confirmadas manualmente -> forma canônica)
# ============================================================

MAPA_INSTITUICOES_CANONICAS = {
    "Puc-Rio": "PUC-Rio",
    "Empresa Brasileira de Pesquisa Agropecuaria (Embrapa)":
        "Empresa Brasileira de Pesquisa Agropecuária (EMBRAPA)",
    "Empresa de Informática e Informação do Município de Belo Horizonte (PRODABEL]":
        "Empresa de Informática e Informação do Município de Belo Horizonte (PRODABEL)",
    "Instituto Federal do Ceara (IFCE)":
        "Instituto Federal do Ceará (IFCE)",
    "Instituto Federal do Parana (IFPR)":
        "Instituto Federal do Paraná (IFPR)",
    "Instituto Tecnologico de Aeronáutica (ITA)":
        "Instituto Tecnológico de Aeronáutica (ITA)",
    "National Center for Monitoring and Early Warning of Natural Disasters (Cemaden)":
        "National Center for Monitoring and Early Warning of Natural Disasters (CEMADEN)",
    "National Institute for Space Research – (INPE)":
        "National Institute for Space Research (INPE)",
    "Pontifícia Universidade Católica de Minas Gerais (Puc Minas)":
        "Pontifícia Universidade Católica de Minas Gerais (PUC Minas)",
    "Puc-Rio": "PUC-Rio",  # já existente
    "Pontifícia Universidade Católica do Rio de Janeiro (Puc-Rio)":
        "Pontifícia Universidade Católica do Rio de Janeiro (PUC-Rio)",
    "Universidade Estadual Paulista (Unesp)":
        "Universidade Estadual Paulista (UNESP)",
    "Universidade Federal de São João del Rei (UFSJ)":
        "Universidade Federal de São João Del Rei (UFSJ)",
    "Universidade Federal de Sao João del-Rei (UFSJ)":
        "Universidade Federal de São João Del-Rei (UFSJ)",
    "Universidade Federal de São João del-Rei (UFSJ)":
        "Universidade Federal de São João Del-Rei (UFSJ)",
    "Universidade Federal de Sao João Del-Rei (UFSJ)":
        "Universidade Federal de São João Del-Rei (UFSJ)",
    "Universidade Federal de Sao JoŃo del Rei (UFSJ)":
        "Universidade Federal de São João Del Rei (UFSJ)",
    "Universidade Salvador (Unifacs)":
        "Universidade Salvador (UNIFACS)",
    "Universidade Tecnologica Federal do Paraná (UTFPR)":
        "Universidade Tecnológica Federal do Paraná (UTFPR)",
    "University of Sao Paulo (USP)":
        "University of São Paulo (USP)",
    "Universidade Federal de Sao João del Rei (UFSJ)":
        "Universidade Federal de São João Del Rei (UFSJ)"
}

MAPA_AUTORES_CANONICOS = {
    "Campelo, Claudio E. C.": "Campelo, Cláudio E. C.",
    "Baptista, Claudio de Souza": "Baptista, Cláudio de Souza",
    "D Gimenez": "D Giménez",   # variação sem acento -> com acento
}


def aplicar_mapa_multivalorado(valor, mapa, separador="; "):
    """
    Aplica um mapa de padronização (variação -> forma canônica) a
    um campo multivalorado, removendo duplicatas que a correção
    possa gerar, preservando a ordem original.
    """
    if pd.isna(valor):
        return valor
    partes = [p.strip() for p in str(valor).split(separador) if p.strip()]
    partes_corrigidas = [mapa.get(p, p) for p in partes]
    partes_unicas = list(dict.fromkeys(partes_corrigidas))
    return separador.join(partes_unicas)


def padronizar_instituicoes(valor):
    return aplicar_mapa_multivalorado(valor, MAPA_INSTITUICOES_CANONICAS)


def padronizar_autores(valor):
    return aplicar_mapa_multivalorado(valor, MAPA_AUTORES_CANONICOS)

def padronizar_autor(valor):
    """
    Normaliza autores no formato "XX Sobrenome" do Google Scholar:
      - remove reticências finais de truncamento (…)
      - a PRIMEIRA palavra de cada autor é tratada como iniciais
        concatenadas (ex. "MCC", "AHF") e mantida em maiúsculo
      - as demais palavras são capitalizadas normalmente (sobrenome),
        exceto conectivos comuns (de, da, do, dos, das), que ficam
        em minúsculo
    """
    if pd.isna(valor):
        return valor

    valor = str(valor).strip()
    valor = valor.rstrip("…").rstrip(".").strip()

    conectivos = {"de", "da", "do", "das", "dos"}

    autores_individuais = [a.strip() for a in valor.split(",") if a.strip()]
    autores_corrigidos = []

    for autor in autores_individuais:
        palavras = autor.split()
        palavras_corrigidas = []

        for i, palavra in enumerate(palavras):
            base = palavra.strip(".")

            if i == 0 and base.isalpha() and base == base.upper() and len(base) <= 5:
                # primeira palavra = iniciais concatenadas -> mantém maiúsculo
                palavras_corrigidas.append(palavra.upper())
            elif base.lower() in conectivos:
                palavras_corrigidas.append(palavra.lower())
            else:
                # demais palavras = sobrenome -> capitaliza
                palavras_corrigidas.append(palavra.capitalize())

        autores_corrigidos.append(" ".join(palavras_corrigidas))

    return ", ".join(autores_corrigidos)


# ============================================================
# EXPLOSÃO E DIAGNÓSTICO — INSTITUIÇÕES E AUTORES
# ============================================================

def explodir_e_contar(df, coluna, separador="; "):
    """
    Explode uma coluna multivalorada em uma linha por valor
    individual, retornando a contagem de ocorrências de cada
    valor único.
    """
    serie = (
        df[coluna]
        .dropna()
        .astype(str)
        .str.split(separador)
        .explode()
        .str.strip()
    )
    serie = serie[serie != ""]

    return (
        serie
        .value_counts()
        .rename_axis(coluna)
        .reset_index(name="ocorrencias")
    )


def normalizar_para_agrupamento(texto):
    """
    Normalização agressiva (minúsculo, sem acento, sem pontuação)
    usada só para AGRUPAR candidatos a variação do mesmo nome —
    não substitui o texto original em lugar nenhum.
    """
    if pd.isna(texto):
        return ""
    texto = str(texto).lower().strip()
    texto = unicodedata.normalize("NFKD", texto)
    texto = "".join(c for c in texto if not unicodedata.combining(c))
    texto = "".join(c for c in texto if c.isalnum() or c.isspace())
    return " ".join(texto.split())


def gerar_tabela_valores_unicos(df, coluna, origem):
    """
    Gera a tabela de valores únicos de uma coluna multivalorada,
    com contagem, origem e marcação de candidatos a duplicata
    (mesmo nome_normalizado, grafia divergente entre os valores).
    """
    tabela = explodir_e_contar(df, coluna)
    tabela["origem"] = origem
    tabela["nome_normalizado"] = tabela[coluna].apply(normalizar_para_agrupamento)

    variacoes_por_grupo = tabela.groupby("nome_normalizado")[coluna].nunique()
    grupos_com_variacao_real = variacoes_por_grupo[variacoes_por_grupo > 1].index
    tabela["possivel_duplicata"] = tabela["nome_normalizado"].isin(grupos_com_variacao_real)

    return tabela

def contar_caracteres_acentuados(texto):
    """
    Conta quantos caracteres do texto têm acento (usado como
    critério de desempate: nesse dataset, corrupção de encoding
    tende a remover acentos, então mais acentos é sinal de
    grafia mais correta).
    """
    return sum(
        1 for c in unicodedata.normalize("NFD", texto)
        if unicodedata.combining(c)
    )


def gerar_mapa_canonico_automatico(tabela, coluna):
    """
    Para cada grupo de variantes (mesmo nome_normalizado), escolhe
    automaticamente a forma canônica: a variante mais frequente
    (ocorrencias); em empate, a com mais caracteres acentuados.

    Retorna um dict {variante: forma_canonica} cobrindo TODAS as
    variantes de cada grupo com mais de 1 forma distinta — pronto
    para uso em aplicar_mapa_multivalorado.
    """
    mapa = {}

    for nome_normalizado, grupo in tabela.groupby("nome_normalizado"):
        if grupo[coluna].nunique() <= 1:
            continue  # já é único, nada a mapear

        grupo_ordenado = grupo.copy()
        grupo_ordenado["_acentos"] = grupo_ordenado[coluna].apply(contar_caracteres_acentuados)
        grupo_ordenado = grupo_ordenado.sort_values(
            ["ocorrencias", "_acentos"], ascending=[False, False]
        )

        canonica = grupo_ordenado.iloc[0][coluna]

        for variante in grupo[coluna]:
            mapa[variante] = canonica

    return mapa