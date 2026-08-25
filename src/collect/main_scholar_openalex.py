import pandas as pd
from pathlib import Path
import time

from openalex import ErroTemporarioOpenAlex, buscar_metadados_citante_openalex


DIR = Path("./data/processed/")
DIR_RAW = Path("./data/raw/")
ARQUIVO_ENTRADA = DIR_RAW / "citacoes_google_scholar.csv"          # gerado pelo Scholar
ARQUIVO_SAIDA = DIR / "citacoes_geoinfo_enriquecido.csv"

EMAIL = "giuliakatherine@gmail.com"

COLUNAS_ENRIQUECIMENTO = ["instituicoes", "pais", "idioma", "doi", "tipo_documento",
                          "topico", "subcampo", "campo", "dominio_tematico",
                          "fonte_publicacao", "status_acesso_aberto","openalex_id",]

COLUNA_STATUS = "openalex_status"   # "OK" ou "SEM_MATCH" — nunca fica vazia após processar

MARCADOR_SEM_MATCH = "SEM_MATCH"
MARCADOR_OK = "OK"


# RETOMAR DE ONDE PAROU
if ARQUIVO_SAIDA.exists():
    print(f"Retomando progresso de: {ARQUIVO_SAIDA}")
    df = pd.read_csv(ARQUIVO_SAIDA)
else:
    print(f"Iniciando do zero a partir de: {ARQUIVO_ENTRADA}")
    df = pd.read_csv(ARQUIVO_ENTRADA)

for coluna in COLUNAS_ENRIQUECIMENTO + [COLUNA_STATUS]:
    if coluna not in df.columns:
        df[coluna] = pd.NA
    df[coluna] = df[coluna].astype("object")

total = len(df)
ja_processados = (
    df[COLUNA_STATUS].notna().sum() + df["titulo"].isna().sum()
)

print(f"Registros totais (linhas de citação): {total}")
print(f"Já processados (a pular): {ja_processados}")
print(f"Restantes: {total - ja_processados}")

try:
    for indice, linha in df.iterrows():
        titulo = linha["titulo"]

        if pd.isna(titulo):
            continue

        if pd.notna(linha.get(COLUNA_STATUS)):   # <- checa o status, não um campo de dado
            continue

        ano = linha.get("ano")
        ano = int(ano) if pd.notna(ano) else None

        print(f"\n[{indice + 1}/{total}] {titulo}")

        try:
            resultado = buscar_metadados_citante_openalex(titulo, ano=ano)
        except ErroTemporarioOpenAlex:
            print("[AVISO] Indisponibilidade temporária — deixando para a próxima execução.")
            continue  # NÃO marca status — será retentado

        if resultado:
            for coluna in COLUNAS_ENRIQUECIMENTO:
                valor = resultado.get(coluna)
                if coluna == "doi" and pd.notna(df.at[indice, "doi"]):
                    continue
                df.at[indice, coluna] = valor
            df.at[indice, COLUNA_STATUS] = MARCADOR_OK
            print(f"[SUCESSO] {resultado['instituicoes']} | {resultado['topico']}")
        else:
            df.at[indice, COLUNA_STATUS] = MARCADOR_SEM_MATCH
            print("[FALHA] Sem match confiável no OpenAlex.")

        time.sleep(30)

        df.to_csv(ARQUIVO_SAIDA, index=False, encoding="utf-8-sig")

except KeyboardInterrupt:
    print("\n\n[AVISO] Interrompido manualmente. Progresso salvo até aqui.")

print(f"\nConcluído (ou pausado). Arquivo: {ARQUIVO_SAIDA}")