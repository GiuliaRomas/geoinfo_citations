import requests
import time

from google_scholar import (normalizar_texto, pontuacao_titulo,)

LIMIAR_SIMILARIDADE_OPENALEX = 0.80
MAX_TENTATIVAS_429 = 5

class ErroTemporarioOpenAlex(Exception):
    """Erro de rede/servidor — deve ser re-tentado depois, não tratado como ausência de dado."""
    pass

def _requisitar_com_retry(url, params=None, tentativas=MAX_TENTATIVAS_429):
    """
    Faz a requisição tratando 429/5xx com backoff.
    Levanta ErroTemporarioOpenAlex se esgotar as tentativas por
    causa de infraestrutura 
    """
    for tentativa in range(1, tentativas + 1):
        try:
            resp = requests.get(url, params=params, timeout=15)

            if resp.status_code == 429:
                espera = resp.headers.get("Retry-After")
                espera = min(int(espera), 120) if espera else (2 ** tentativa)
                print(f"[AVISO] 429 recebido. Aguardando {espera}s (tentativa {tentativa}/{tentativas})...")
                time.sleep(espera)
                continue

            if resp.status_code in (500, 502, 503, 504):
                espera = 5 * tentativa
                print(f"[AVISO] {resp.status_code} recebido. Aguardando {espera}s (tentativa {tentativa}/{tentativas})...")
                time.sleep(espera)
                continue

            resp.raise_for_status()
            return resp.json()

        except requests.RequestException as erro:
            print(f"[ERRO] OpenAlex: {erro}")

            if tentativa < tentativas:
                espera = 3 * tentativa
                print(f"Aguardando {espera}s antes de tentar de novo...")
                time.sleep(espera)

    raise ErroTemporarioOpenAlex(url)


def _extrair_metadados_work(work):
    """
    Extrai os campos de interesse de um objeto 'work' do OpenAlex
    """
    instituicoes = set()
    paises = set()
    autores = []

    for autoria in work.get("authorships", []):
        nome = (autoria.get("author") or {}).get("display_name")
        if nome:
            autores.append(nome)
        for inst in autoria.get("institutions", []):
            if inst.get("display_name"):
                instituicoes.add(inst["display_name"])
            if inst.get("country_code"):
                paises.add(inst["country_code"])

    topico_principal = work.get("primary_topic") or {}

    fonte = ((work.get("primary_location") or {}).get("source") or {}).get("display_name")

    return {
        "titulo": work.get("title"),
        "ano": work.get("publication_year"),
        "autores": "; ".join(autores) or None,
        "instituicoes": "; ".join(sorted(instituicoes)) or None,
        "pais": "; ".join(sorted(paises)) or None,
        "idioma": work.get("language"),
        "doi": work.get("doi"),
        "tipo_documento": work.get("type"),
        "topico": topico_principal.get("display_name"),
        "subcampo": (topico_principal.get("subfield") or {}).get("display_name"),
        "campo": (topico_principal.get("field") or {}).get("display_name"),
        "dominio_tematico": (topico_principal.get("domain") or {}).get("display_name"),
        "fonte_publicacao": fonte,
        "status_acesso_aberto": (work.get("open_access") or {}).get("oa_status"),
        "openalex_id": work.get("id"),
        "url": work.get("id"),  # link estável do próprio OpenAlex
    }


def buscar_obra_geoinfo_openalex(titulo, ano=None, email=None):
    """
    Busca o artigo ORIGINAL do GEOINFO no OpenAlex por título,
    valida por similaridade e retorna o work completo (usado
    depois para obter cited_by_api_url).
    """
    base = "https://api.openalex.org/works"

    params = {"search": titulo, "per_page": 5}
    if ano:
        params["filter"] = f"publication_year:{ano}"
    if email:
        params["mailto"] = email

    dado = _requisitar_com_retry(base, params)
    resultados = dado.get("results", [])

    if not resultados:
        if ano:
            return buscar_obra_geoinfo_openalex(titulo, ano=None, email=email)
        return None

    titulo_normalizado = normalizar_texto(titulo)
    melhor = None
    melhor_score = 0.0

    for candidato in resultados:
        titulo_candidato = candidato.get("title") or ""
        score = pontuacao_titulo(titulo, titulo_candidato)

        if normalizar_texto(titulo_candidato) == titulo_normalizado:
            melhor = candidato
            melhor_score = 1.0
            break

        if score > melhor_score:
            melhor = candidato
            melhor_score = score

    if not melhor or melhor_score < LIMIAR_SIMILARIDADE_OPENALEX:
        print(f"[AVISO] Artigo GEOINFO não encontrado no OpenAlex: {titulo!r} (score: {melhor_score:.3f})")
        return None

    return melhor


def buscar_citantes_openalex(work, email=None):
    """
    Dado um work do OpenAlex (o artigo original já casado), busca
    todas as obras que o citam
    """
    cited_by_url = work.get("cited_by_api_url")

    if not cited_by_url:
        return []

    citantes = []
    cursor = "*"

    while cursor:
        params = {"per_page": 200, "cursor": cursor}
        if email:
            params["mailto"] = email

        dado = _requisitar_com_retry(cited_by_url, params)

        for citante_raw in dado.get("results", []):
            citantes.append(_extrair_metadados_work(citante_raw))

        cursor = (dado.get("meta") or {}).get("next_cursor")

        if not dado.get("results"):
            break

        time.sleep(0.3)

    return citantes