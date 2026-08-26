import requests
import time

from google_scholar import (normalizar_texto, pontuacao_titulo,)

LIMIAR_SIMILARIDADE_OPENALEX = 0.80
MAX_TENTATIVAS_429 = 5

session = requests.Session()

session.headers.update({
    "User-Agent": "GEOINFO-Bibliometric-Analysis/1.0"
})

# -=-=-=-=-=-=-=- tratar erros -=-=-=-=-=-=-=- #
class ErroTemporarioOpenAlex(Exception):
    """Erro de rede/servidor — deve ser tentado novamente depois, não tratado como ausência de dado."""
    pass

def _requisitar_com_retry(url, params=None, tentativas=MAX_TENTATIVAS_429):
    """
    Faz a requisição tratando 429/5xx com backoff.
    Levanta ErroTemporarioOpenAlex se esgotar as tentativas por
    causa de infraestrutura
    """
    for tentativa in range(1, tentativas + 1):
        try:
            time.sleep(1.0)
            resp = session.get(url, params=params, timeout=15)

            print(f"[DEBUG] URL real: {resp.url}")
            print(f"[DEBUG] Status: {resp.status_code}")

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

            dado = resp.json()
            meta = dado.get("meta", {})
            print(f"[DEBUG] meta.count={meta.get('count')} | resultados nesta página={len(dado.get('results', []))}")

            return dado

        except requests.RequestException as erro:
            print(f"[ERRO] OpenAlex: {erro}")

            if tentativa < tentativas:
                espera = 3 * tentativa
                print(f"Aguardando {espera}s antes de tentar de novo...")
                time.sleep(espera)

    raise ErroTemporarioOpenAlex(url)

# -=-=-=-=-=-=-=- extrai metadados -=-=-=-=-=-=-=- #
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
        "url": work.get("id"), 
    }

# -=-=-=-=-=-=-=- busca pelo autocomplete -=-=-=-=-=-=-=- #
def _autocomplete_openalex(titulo, email=None):
    """
    Usa o endpoint de autocomplete do OpenAlex — o mesmo usado pela
    busca da interface do site, que na prática encontra trabalhos
    que a busca por filter=title.search não encontra
    """
    base = "https://api.openalex.org/autocomplete/works"

    params = {"q": titulo}
    if email:
        params["mailto"] = email

    print(f"[DEBUG] Autocomplete: buscando {titulo!r}")

    dado = _requisitar_com_retry(base, params)
    resultados = dado.get("results", [])

    print(f"[DEBUG] Autocomplete retornou {len(resultados)} candidato(s)")

    return resultados

def _buscar_work_por_id(openalex_id, email=None):
    """
    Busca o objeto work completo a partir de um ID do OpenAlex
    (necessário porque o autocomplete só retorna um resumo).
    """
    # normaliza (aceita tanto "W123..." quanto a URL completa)
    id_curto = openalex_id.split("/")[-1]

    base = f"https://api.openalex.org/works/{id_curto}"

    params = {}
    if email:
        params["mailto"] = email

    return _requisitar_com_retry(base, params)


def buscar_obra_geoinfo_openalex(titulo, ano=None, email=None):
    """
    Busca o artigo original do GEOINFO no OpenAlex por título, por camadas:
      1. filter=title.search (+ ano, se informado): é mais preciso,
         mas falha fácil com qualquer divergência textual
      2. fallback sem filtro de ano
      3. autocomplete — correspondência mais tolerante
    """
    base = "https://api.openalex.org/works"

    filtro = f'title.search:"{titulo}"'
    if ano:
        filtro += f",publication_year:{ano}"

    params = {"filter": filtro, "per_page": 25}
    if email:
        params["mailto"] = email

    print("\n" + "-" * 70)
    print(f"[DEBUG] Buscando artigo original: {titulo!r}")
    print(f"[DEBUG] Ano informado: {ano}")
    print(f"[DEBUG] Filtro montado: {filtro}")
    print("-" * 70)

    dado = _requisitar_com_retry(base, params)
    resultados = dado.get("results", [])

    if not resultados and ano:
        print("[DEBUG] Zero resultados com ano. Tentando fallback sem filtro de ano...")
        params["filter"] = f'title.search:"{titulo}"'
        dado = _requisitar_com_retry(base, params)
        resultados = dado.get("results", [])

    titulo_normalizado = normalizar_texto(titulo)
    melhor = None
    melhor_score = 0.0

    if resultados:
        print(f"[DEBUG] Avaliando {len(resultados)} candidato(s) via title.search:")

        for i, candidato in enumerate(resultados):
            titulo_candidato = candidato.get("title") or ""
            score = pontuacao_titulo(titulo, titulo_candidato)

            print(f"  [{i}] score={score:.3f} | ano={candidato.get('publication_year')} | {titulo_candidato!r}")

            if normalizar_texto(titulo_candidato) == titulo_normalizado:
                print(f"  [{i}] -> MATCH EXATO")
                melhor = candidato
                melhor_score = 1.0
                break

            if score > melhor_score:
                melhor = candidato
                melhor_score = score

    if melhor and melhor_score >= LIMIAR_SIMILARIDADE_OPENALEX:
        print(f"[DEBUG] Escolhido via title.search: {melhor.get('title')!r} (score={melhor_score:.3f})")
        return melhor

    # autocomplete
    print(f"[DEBUG] title.search não encontrou match confiável (melhor score: {melhor_score:.3f}). Tentando autocomplete...")

    candidatos_autocomplete = _autocomplete_openalex(titulo, email=email)

    melhor_ac = None
    melhor_score_ac = 0.0

    for i, candidato in enumerate(candidatos_autocomplete):
        titulo_candidato = candidato.get("display_name") or ""
        score = pontuacao_titulo(titulo, titulo_candidato)

        print(f"  [autocomplete {i}] score={score:.3f} | {titulo_candidato!r} | id={candidato.get('id')}")

        if normalizar_texto(titulo_candidato) == titulo_normalizado:
            print(f"  [autocomplete {i}] -> MATCH EXATO")
            melhor_ac = candidato
            melhor_score_ac = 1.0
            break

        if score > melhor_score_ac:
            melhor_ac = candidato
            melhor_score_ac = score

    if not melhor_ac or melhor_score_ac < LIMIAR_SIMILARIDADE_OPENALEX:
        print(f"[AVISO] Artigo GEOINFO não encontrado no OpenAlex (nem via autocomplete): {titulo!r} (melhor score: {melhor_score_ac:.3f})")
        return None

    print(f"[DEBUG] Escolhido via autocomplete: {melhor_ac.get('display_name')!r} (score={melhor_score_ac:.3f})")

    # busca o work completo, já que o autocomplete só devolve um resumo
    work_completo = _buscar_work_por_id(melhor_ac["id"], email=email)

    return work_completo


def buscar_citantes_openalex(work, email=None):
    """
    Dado um work do OpenAlex, busca
    todas as obras que o citam
    """
    cited_by_url = work.get("cited_by_api_url")

    print(f"[DEBUG] cited_by_api_url: {cited_by_url}")

    if not cited_by_url:
        print("[DEBUG] Sem cited_by_api_url — nenhum citante a buscar.")
        return []

    citantes = []
    cursor = "*"
    pagina = 1

    while cursor:
        params = {"per_page": 200, "cursor": cursor}
        if email:
            params["mailto"] = email

        print(f"[DEBUG] Buscando citantes — página {pagina}, cursor={cursor!r}")

        dado = _requisitar_com_retry(cited_by_url, params)

        novos = len(dado.get("results", []))
        print(f"[DEBUG] Citantes encontrados nesta página: {novos}")

        for citante_raw in dado.get("results", []):
            citantes.append(_extrair_metadados_work(citante_raw))

        cursor = (dado.get("meta") or {}).get("next_cursor")

        if not dado.get("results"):
            break

        pagina += 1

    print(f"[DEBUG] Total de citantes coletados: {len(citantes)}")

    return citantes

def buscar_metadados_citante_openalex(titulo, ano=None, email=None):
    """
    Busca um artigo CITANTE (título vindo do Scholar) no OpenAlex
    e retorna seus metadados já extraídos 

    Reaproveita buscar_obra_geoinfo_openalex 
    
    Retorna None se não encontrar match confiável em nenhuma das
    camadas de busca.
    """
    work = buscar_obra_geoinfo_openalex(titulo, ano=ano, email=email)

    if work is None:
        return None

    return _extrair_metadados_work(work)