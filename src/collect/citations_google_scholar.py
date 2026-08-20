import pandas as pd
from pathlib import Path

from google_scholar import (criar_contexto, coletar_citacoes_artigo,)

# -=-=-=-=-=- configuracoes -=-=-=-=-=-=- #
DIR = Path("./data/processed/")
ARQUIVO_ARTIGOS = DIR / "geoinfo_artigos_processado.csv"

ARQUIVO_SAIDA = DIR / "citacoes_geoinfo.csv"

# ler artigos geoinfo
df_artigos = pd.read_csv(ARQUIVO_ARTIGOS)
print(f"Artigos para processar: {len(df_artigos)}")

# colunas finais
COLUNAS = [
    # Artigo que foi citado
    "titulo_original",
    "ano_original",

    # Artigo que citou
    "titulo",
    "ano",
    "autores",
    "instituicoes",
    "idioma",
    "pais",
    "veiculo_publicacao",
    "doi",
    "url",
]

todas_citacoes = []


# contexto do scholar
playwright, context, page = criar_contexto(headless=False)

try:
    # processar artigos
    for indice, linha in df_artigos.iterrows():
        titulo = linha["titulo"]
        ano = linha["ano"]

        print("\n")
        print("=-" * 30)
        print(f"ARTIGO {indice + 1}/{len(df_artigos)}")
        print("=-" * 30)

        print(f"Título: {titulo}")
        print(f"Ano: {ano}")

        # valida
        if pd.isna(titulo):
            print("[AVISO] Título vazio. Pulando.")
            continue

        titulo = str(titulo).strip()

        if pd.isna(ano):
            ano = None
        else:
            try:
                ano = int(ano)
            except (ValueError, TypeError):
                ano = None

        # buscar citações
        try:
            citacoes = (coletar_citacoes_artigo(page=page, titulo=titulo, ano=ano,))
        except Exception as e:
            print("\n[ERRO]")
            print(e)
            continue

        # nenhuma citacao
        if not citacoes:
            print("\nNenhuma citação encontrada.")
            continue

        # normalizar resultados
        for citacao in citacoes:
            registro = {
                "titulo_original": citacao.get("titulo_original", titulo),
                "ano_original": citacao.get("ano_original", ano),

                "titulo": citacao.get("titulo"),
                "ano": citacao.get("ano"),
                "autores": citacao.get("autores"),
                "instituicoes": citacao.get("instituicoes"),
                "idioma": citacao.get("idioma"),
                "pais": citacao.get("pais"),
                "veiculo_publicacao": citacao.get("veiculo_publicacao"),
                "doi": citacao.get("doi"),
                "url": citacao.get("url"),
            }

            todas_citacoes.append(registro)

        # salvar progresso
        df_saida = pd.DataFrame(todas_citacoes, columns=COLUNAS)
        df_saida.to_csv(ARQUIVO_SAIDA, index=False, encoding="utf-8-sig")

        print(f"\n{len(citacoes)} citações adicionadas.")
        print(f"Total acumulado: {len(todas_citacoes)}")
        
finally:
    context.close()
    playwright.stop()


print("\n")
print("=-" * 30)
print("[SUCESSO] Processamento finalizado!")
print("=-" * 30)

print(f"Total de registros: {len(todas_citacoes)}")
print(f"Arquivo: {ARQUIVO_SAIDA}")