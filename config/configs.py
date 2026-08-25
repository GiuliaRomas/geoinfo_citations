from pathlib import Path


# ============================================================
# CAMINHOS
# ============================================================

DATA_DIR = Path("../data")

PATH_GEOINFO = DATA_DIR / "processed/geoinfo_artigos_processed.csv"
PATH_CITACOES_ENRIQUECIDAS = (
    DATA_DIR / "processed/citacoes_geoinfo_enriquecido.csv"
)
PATH_GOOGLE_SCHOLAR = DATA_DIR / "raw/citacoes_google_scholar.csv"
PATH_OPENALEX = DATA_DIR / "raw/citacoes_openalex.csv"

OUTPUT_DIR = DATA_DIR / "processed"


# ============================================================
# COLUNAS
# ============================================================

COLUNAS_PADRAO = [
    "identificador",
    "titulo_original",
    "titulo",
    "ano_original",
    "ano",
    "autores",
    "instituicoes",
    "idioma",
    "pais",
    "veiculo_publicacao",
    "tipo_documento",
    "doi",
    "topico",
    "subcampo",
    "campo",
    "dominio_tematico",
    "fonte_publicacao",
    "status_acesso_aberto",
    "openalex_id",
    "openalex_status",
    "url",
    "url_original",
    "url_artigo",
    "url_metadata",
    "url_edicao",
    "edicao",
    "numero_edicao",
    "fonte_dados",
]

COLUNAS_TEXTO = [
    "titulo_original",
    "titulo",
    "autores",
    "instituicoes",
    "idioma",
    "pais",
    "veiculo_publicacao",
    "tipo_documento",
    "topico",
    "subcampo",
    "campo",
    "dominio_tematico",
    "fonte_publicacao",
    "status_acesso_aberto",
    "openalex_status",
    "edicao",
]


# ============================================================
# CARACTERES
# ============================================================

CARACTERES_INVISIVEIS = {
    "\u200b": "",
    "\u200e": "",
    "\ufeff": "",
    "\ufffc": "",
}