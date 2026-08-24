import pandas as pd
from pathlib import Path
import time

from openalex import (buscar_obra_geoinfo_openalex, buscar_citantes_openalex, ErroTemporarioOpenAlex,)

DIR_RAW = Path("./data/raw/")
DIR_PROCESSED = Path("./data/processed/")
ARQUIVO_ARTIGOS = DIR_PROCESSED / "geoinfo_artigos_processed.csv"  # artigos originais do GEOINFO
ARQUIVO_SAIDA = DIR_RAW / "citacoes_openalex.csv"
ARQUIVO_PROGRESSO = DIR_RAW / "openalex_progresso.csv"  # controla quais originais já foram processados

EMAIL = "giuliakatherine.gkr@gmail.com"

COLUNAS = [
    "titulo_original", "ano_original", "url_original",
    "titulo", "ano", "autores", "instituicoes", "pais",
    "idioma", "doi", "tipo_documento", "topico", "subcampo",
    "campo", "dominio_tematico", "fonte_publicacao",
    "status_acesso_aberto", "openalex_id", "url",
]


df_artigos = pd.read_csv(ARQUIVO_ARTIGOS)

# Controle de progresso (por artigo original)
if ARQUIVO_PROGRESSO.exists():
    df_progresso = pd.read_csv(ARQUIVO_PROGRESSO)
    titulos_processados = set(df_progresso["titulo_original"])
else:
    df_progresso = pd.DataFrame(columns=["titulo_original", "status"])
    titulos_processados = set()

if ARQUIVO_SAIDA.exists():
    todas_citacoes = pd.read_csv(ARQUIVO_SAIDA).to_dict("records")
else:
    todas_citacoes = []

total = len(df_artigos)
print(f"Artigos GEOINFO: {total}")
print(f"Já processados: {len(titulos_processados)}")

try:
    for indice, linha in df_artigos.iterrows():
        titulo_original = str(linha["titulo"]).strip()

        if titulo_original in titulos_processados:
            continue

        ano_original = linha.get("ano")
        ano_original = int(ano_original) if pd.notna(ano_original) else None

        url_original = linha.get("url_artigo")

        print(f"\n[{indice + 1}/{total}] {titulo_original}")

        try:
            obra = buscar_obra_geoinfo_openalex(titulo_original, email=EMAIL)
        except ErroTemporarioOpenAlex:
            print("[AVISO] Indisponibilidade temporária — tentando de novo na próxima execução.")
            continue  # não marca como processado

        if not obra:
            df_progresso.loc[len(df_progresso)] = [titulo_original, "NAO_ENCONTRADO_NO_OPENALEX"]
            df_progresso.to_csv(ARQUIVO_PROGRESSO, index=False, encoding="utf-8-sig")
            continue

        try:
            citantes = buscar_citantes_openalex(obra, email=EMAIL)
        except ErroTemporarioOpenAlex:
            print("[AVISO] Indisponibilidade temporária ao buscar citantes — tentando de novo na próxima execução.")
            continue  # não marca como processado

        print(f"[SUCESSO] {len(citantes)} citante(s) encontrado(s) no OpenAlex")

        for citante in citantes:
            registro = {
                "titulo_original": titulo_original,
                "ano_original": ano_original,
                "url_original": url_original,
            }
            registro.update(citante)
            todas_citacoes.append(registro)

        df_progresso.loc[len(df_progresso)] = [titulo_original, "OK"]
        df_progresso.to_csv(ARQUIVO_PROGRESSO, index=False, encoding="utf-8-sig")

        df_saida = pd.DataFrame(todas_citacoes, columns=COLUNAS)
        df_saida.to_csv(ARQUIVO_SAIDA, index=False, encoding="utf-8-sig")

        time.sleep(0.5)

except KeyboardInterrupt:
    print("\n\n[AVISO] Interrompido manualmente. Progresso salvo até aqui.")

print(f"\nConcluído (ou pausado). Arquivo: {ARQUIVO_SAIDA}")