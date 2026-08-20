from pathlib import Path
from difflib import SequenceMatcher
import re
import unicodedata
from urllib.parse import quote_plus, urlparse, parse_qs

from playwright.sync_api import (sync_playwright, TimeoutError as PlaywrightTimeoutError,)

BASE_URL = "https://scholar.google.com"

PROFILE_DIR = Path("chrome_profile")

# -=-=-=-=-=-=- normalizacoes -=-=-=-=-=-=- #
def normalizar_texto(texto):
    """
    Normaliza textos
    """
    if texto is None:
        return ""

    texto = str(texto).lower().strip()
    texto = unicodedata.normalize("NFKD", texto)
    texto = "".join(c for c in texto if not unicodedata.combining(c))
    texto = re.sub(r"[^a-z0-9\s]", " ", texto)
    texto = re.sub(r"\s+", " ", texto).strip()

    return texto

def palavras_titulo(texto):
    """
    Retorna o conjunto de palavras do título.
    """
    texto = normalizar_texto(texto)

    if not texto:
        return set()

    return set(texto.split())

def similaridade_titulo(titulo1, titulo2):
    """
    Similaridade baseada no SequenceMatcher.
    """
    t1 = normalizar_texto(titulo1)
    t2 = normalizar_texto(titulo2)

    if not t1 or not t2:
        return 0.0

    return SequenceMatcher(None, t1, t2).ratio()

def cobertura_palavras(titulo1, titulo2):
    """
    Mede quantas palavras do título procurado aparecem
    no título encontrado.
    """
    palavras1 = palavras_titulo(titulo1)
    palavras2 = palavras_titulo(titulo2)

    if not palavras1:
        return 0.0

    return len(palavras1 & palavras2) / len(palavras1)

def pontuacao_titulo(titulo1, titulo2):
    """
    Calcula uma pontuação mais robusta para comparação
    de títulos.
    """
    seq = similaridade_titulo(titulo1, titulo2)
    cobertura = cobertura_palavras(titulo1, titulo2)

    # peso maior para cobertura das palavras
    score = (0.4 * seq + 0.6 * cobertura)

    return score

def extrair_ano(texto):
    """
    Extrai o ano do texto bibliográfico.
    """
    if not texto:
        return None

    match = re.search(r"\b(19|20)\d{2}\b", texto)

    if match:
        return int(match.group(0))

    return None

# -=-=-=-=-=-=- playwright -=-=-=-=-=-=- #
def criar_contexto(headless=False):
    """
    Cria contexto persistente do Chromium.
    """
    playwright = sync_playwright().start()

    context = (
        playwright.chromium
        .launch_persistent_context(
            user_data_dir=str(PROFILE_DIR),
            headless=headless,
            viewport={"width": 1366, "height": 768,},
            locale="pt-BR",
        )
    )

    if context.pages:
        page = context.pages[0]
    else:
        page = context.new_page()

    return (playwright, context, page)


# -=-=-=-=-=-=- verificar bloqueio -=-=-=-=-=-=- #
def scholar_bloqueado(page):
    """
    Verifica se o Google Scholar apresentou bloqueio/captcha.
    """
    try:
        texto = (page.locator("body").inner_text().lower())
    except Exception:
        return False

    termos = [
        "unusual traffic",
        "not a robot",
        "captcha",
        "não é um robô",
    ]

    return any(termo in texto for termo in termos)


# -=-=-=-=-=-=- extrair informacoes -=-=-=-=-=-=- #
def extrair_titulo_e_link(titulo_element):
    """
    Extrai título e URL de um h3.gs_rt de forma robusta.
    """
    link = titulo_element.locator("a").first

    if link.count() > 0:
        titulo = re.sub(r"\s+", " ", link.inner_text().strip()).strip()
        url = link.get_attribute("href")
        return titulo, url

    # sem <a>: limpa TODAS as tags [...] do início
    titulo_bruto = titulo_element.inner_text().strip()

    titulo = re.sub(r"^\s*(\[[^\]]+\]\s*)+", "", titulo_bruto).strip()
    titulo = re.sub(r"\s+", " ", titulo).strip()

    return titulo, None

def extrair_resultados(page):

    print("\n" + "=-" * 30)
    print("Extraindo resultados")
    print("=-" * 30)

    resultados = page.locator("div.gs_ri")
    quantidade = resultados.count()
    print(f"Blocos .gs_ri encontrados: {quantidade}")

    candidatos = []

    for i in range(quantidade):
        resultado = resultados.nth(i)
        titulo_element = resultado.locator("h3.gs_rt").first

        if titulo_element.count() == 0:
            print(f"\n[{i}] IGNORADO: h3.gs_rt não encontrado")
            continue

        titulo, url = extrair_titulo_e_link(titulo_element)
        print(f"\n[{i}] Título:")

        print(repr(titulo))

        if not titulo:
            print(f"[{i}] IGNORADO: título vazio")
            continue

        info_element = resultado.locator(".gs_a").first

        if info_element.count() > 0:
            info = (info_element.inner_text().strip())
        else:
            info = ""

        info = re.sub(r"\s+", " ", info).strip()

        if " - " in info:
            autores = (info.split(" - ")[0].strip())
        else:
            autores = info

        ano = extrair_ano(info)
        partes = info.split(" - ")

        if len(partes) >= 2:
            venue = (partes[-1].strip())
        else:
            venue = None

        citation_url = None
        citation_count = 0

        citation_link = resultado.locator('a[href*="cites="]').first

        if citation_link.count() > 0:
            citation_url = (citation_link.get_attribute("href"))
            citation_text = (citation_link.inner_text().strip())

            match = re.search(r"\d+", citation_text)

            if match:
                citation_count = int(match.group(0))

        dominio = None

        if url:
            url_lower = url.lower()

            if "academia.edu" in url_lower:
                dominio = "academia.edu"
            elif "doi.org" in url_lower:
                dominio = "doi.org"
            elif "ieeexplore.ieee.org" in url_lower:
                dominio = "ieee"
            elif "springer.com" in url_lower:
                dominio = "springer"
            elif "sciencedirect.com" in url_lower:
                dominio = "sciencedirect"
            else:
                dominio = "outro"

        candidato = {
            "titulo": titulo,
            "url": url,
            "autores": autores,
            "ano": ano,
            "venue": venue,
            "citation_count": citation_count,
            "citation_url": citation_url,
            "dominio": dominio,
        }

        candidatos.append(candidato)

        print(f"[{i}] Resultado extraído!")
        print(f"\tTítulo: {titulo}")
        print(f"\tAno: {ano}")
        print(f"\tURL: {url}")
        print(f"\tDomínio: {dominio}")

    print("\n" + "=-" * 30)
    print(f"Resultados extraídos: {len(candidatos)}")
    print("=-" * 30)

    return candidatos

# -=-=-=-=-=-=- executar a busca -=-=-=-=-=-=-=- #
def executar_busca(page, consulta,):
    """
    Executa uma busca no Google Scholar.
    """
    print(f"\nConsulta:")
    print(consulta)
    page.goto(BASE_URL, wait_until="domcontentloaded", timeout=30000)
    page.wait_for_timeout(2000)

    if scholar_bloqueado(page):
        print("\nGoogle Scholar bloqueou a requisição.")
        return []

    campo = page.locator('input[name="q"]').first

    if campo.count() == 0:
        print("Campo de pesquisa não encontrado.")
        return []

    campo.fill(consulta)
    page.wait_for_timeout(500)
    campo.press("Enter")

    # esperar os resultados
    try:
        page.locator("div.gs_ri").first.wait_for(state="visible", timeout=15000)
    except PlaywrightTimeoutError:
        print("\nNenhum resultado carregado.")
        return []

    page.wait_for_timeout(2000)

    if scholar_bloqueado(page):
        print("\nGoogle Scholar bloqueou a requisição.")
        return []

    candidatos = (extrair_resultados(page))
    print(f"Resultados encontrados: {len(candidatos)}")
    return candidatos

def aguardar_verificacao(page):
    print("\n" + "=-" * 30)
    print("[AVISO] Verificação do Google Scholar")
    print("=-" * 30)
    print("Resolva a verificação manualmente no navegador.")
    print("Depois pressione ENTER aqui no terminal.")

    while True:
        input("\nPressione ENTER quando terminar...")
        texto = page.locator("body").inner_text().lower()

        termos_captcha = [
            "mostre que você não é um robô",
            "prove que você não é um robô",
            "not a robot",
            "unusual traffic",
            "captcha",
        ]

        bloqueado = any(termo in texto for termo in termos_captcha)

        if not bloqueado:
            print("\nVerificação aparentemente concluída.")
            return True

        print("\n[AVISO] A verificação ainda aparece.")
        print("Resolva-a no navegador e tente novamente.")


# -=-=-=-=-=-=- busca artigo -=-=-=-=-=-=- #

def buscar_artigo(page, titulo, ano=None):
    titulo_busca = (str(titulo).replace('"', '').strip())

    print("\n" + "=-" * 30)
    print("Buscando artigo")
    print("=-" * 30)
    print(f"Título procurado:")

    print(titulo_busca)

    if ano is not None:
        print(f"Ano informado: {ano}")

    # normaliza titulo
    titulo_normalizado = normalizar_texto(titulo_busca)

    url_busca = (BASE_URL + "/scholar?hl=pt-BR&q=" + quote_plus(titulo_busca))

    print("\nURL:")
    print(url_busca)

    # abrir
    try:
        page.goto(url_busca, wait_until="domcontentloaded", timeout=30000)
        page.wait_for_timeout(3500)
    except Exception as e:
        print("\n[ERRO] Erro ao abrir Google Scholar:")
        print(e)
        return None

    # captcha
    if scholar_bloqueado(page):
        print("\n[AVISO] Google Scholar apresentou uma verificação.")
        sucesso = aguardar_verificacao(page)

        if not sucesso:
            return None

    # espera os resultados
    try:
        page.locator("div.gs_ri").first.wait_for(state="visible", timeout=15000)
    except PlaywrightTimeoutError:
        print("\nNenhum resultado apareceu.")
        print(f"URL atual: {page.url}")
        return None

    # extrai
    candidatos = extrair_resultados(page)

    if not candidatos:
        print("\n[AVISO] Nenhum candidato foi extraído.")
        return None

    # compara titulos
    for candidato in candidatos:
        titulo_candidato_normalizado = (normalizar_texto(candidato["titulo"]))

        # igualdade
        candidato["titulo_exato"] = (titulo_candidato_normalizado == titulo_normalizado)

        # similaridade
        candidato["similaridade"] = pontuacao_titulo(titulo_busca, candidato["titulo"])
        candidato["similaridade_sequence"] = similaridade_titulo(titulo_busca, candidato["titulo"])

        candidato["cobertura"] = cobertura_palavras(titulo_busca, candidato["titulo"])

    # procura titulo exato
    candidatos_exatos = [candidato for candidato in candidatos if candidato["titulo_exato"]]

    # se existir titulo exato
    if candidatos_exatos:
        # se houver mais de um igual, preferir o que possui citation_url.

        candidatos_exatos_com_citacao = [candidato for candidato in candidatos_exatos if candidato["citation_url"]]

        if candidatos_exatos_com_citacao:
            melhor = (candidatos_exatos_com_citacao[0])
        else:
            melhor = candidatos_exatos[0]

        print("\n" + "=-" * 30)
        print("[SUCESSO] Artigo encontrado — título exato")
        print("=-" * 30)

        print(f"Título:")
        print(melhor["titulo"])

        print(f"\nTítulo procurado:")
        print(titulo_busca)

        print(f"\nAno:")
        print(melhor["ano"])

        print(f"URL:")
        print(melhor["url"])

        print(f"Domínio:")
        print(melhor["dominio"])

        print(f"Citações:")
        print(melhor["citation_count"])

        print(f"Citation URL:")
        print(melhor["citation_url"])

        return melhor

    # nao exato -> ordena por similaridade
    candidatos_ordenados = sorted(candidatos, key=lambda x: (x["similaridade"], x["cobertura"]), reverse=True)

    # mostra candidatos
    print("\n" + "=-" * 30)
    print("Candidatos")
    print("=-" * 30)

    for i, candidato in enumerate(candidatos_ordenados, start=1):
        print(f"\n{i}. {candidato['titulo']}")
        print(f"Similaridade: {candidato['similaridade']:.3f}")
        print(f"Cobertura: {candidato['cobertura']:.3f}")
        print(f"Ano: {candidato['ano']}")
        print(f"URL: {candidato['url']}")
        print(f"Domínio: {candidato['dominio']}")

    # melhor candidato
    melhor = candidatos_ordenados[0]

    # limiar
    LIMIAR_SIMILARIDADE = 0.80

    if (melhor["similaridade"] >= LIMIAR_SIMILARIDADE):
        print("\n" + "=-" * 30)
        print("[SUCESSO] Artigo encontrado!")
        print("=-" * 30)

        print(f"Título:")
        print(melhor["titulo"])
        print(f"\nSimilaridade:")
        print(f"{melhor['similaridade']:.3f}")
        print(f"\nAno:")
        print(melhor["ano"])
        print(f"\nURL:")
        print(melhor["url"])
        print(f"\nDomínio:")
        print(melhor["dominio"])
        return melhor

    # cobertura muito alta
    if melhor["cobertura"] >= 0.90:
        print("\nCandidato possui alta cobertura de palavras.")
        print(f"Cobertura: {melhor['cobertura']:.3f}")
        print("[SUCESSO] Aceitando candidato.")
        return melhor

    # nao encontrado
    print("\n" + "=-" * 30)
    print("[FALHA] ARTIGO NÃO ENCONTRADO")
    print("=-" * 30)

    print(f"Melhor candidato:")
    print(melhor["titulo"])
    print(f"\nSimilaridade:")
    print(f"{melhor['similaridade']:.3f}")
    print(f"\nCobertura:")
    print(f"{melhor['cobertura']:.3f}")
    print(f"\nAno:")
    print(melhor["ano"])
    print(f"\nURL:")
    print(melhor["url"])

    return None

# -=-=-=-=-=- buscar citacoes -=-=-=-=- #
def buscar_citacoes(page, citation_url):
    """
    Busca todos os artigos que citaram um artigo no Google Scholar.
    """
    if not citation_url:
        print("URL de citações não encontrada.")
        return []

    if citation_url.startswith("/"):
        url = BASE_URL + citation_url
    else:
        url = citation_url

    print("\nAbrindo citações:")
    print(url)

    citacoes = []
    pagina = 1
    starts_processados = set()

    while True:
        print("\n" + "=-" * 30)
        print(f"Página de citações {pagina}")
        print("=-" * 30)
        print(f"URL: {url}")

        try:
            page.goto(url, wait_until="domcontentloaded", timeout=30000,)
            page.wait_for_timeout(3000)
        except Exception as e:
            print("\n[ERRO] Erro ao carregar página:")
            print(e)
            break

        try:
            texto_pagina = (page.locator("body").inner_text())
        except Exception:
            texto_pagina = ""

        texto_lower = texto_pagina.lower()

        if ("unusual traffic" in texto_lower or "not a robot" in texto_lower or "captcha" in texto_lower or "mostre que você não é um robô" in texto_lower):
            print("\nGoogle Scholar bloqueou a requisição.")
            print("\nA página permaneceu aberta para verificação manual.")
            break

        resultados = page.locator("div.gs_ri")
        quantidade = resultados.count()
        print(f"\nResultados encontrados: {quantidade}")

        if quantidade == 0:
            print("\nNenhum resultado encontrado.")
            print("\nURL atual:")
            print(page.url)
            break

        parametros = parse_qs(urlparse(page.url).query)
        start_atual = int(parametros.get("start", ["0"])[0])

        print(f"Start atual: {start_atual}")

        if start_atual in starts_processados:
            print("\nEsta página já foi processada.")
            print("Finalizando para evitar loop.")
            break

        starts_processados.add(start_atual)
        quantidade_antes = len(citacoes)

        for i in range(quantidade):
            resultado = (resultados.nth(i))
            titulo_element = resultado.locator("h3.gs_rt").first

            if titulo_element.count() == 0:
                print(f"\n[{i}] Sem h3.gs_rt")
                continue

            titulo_citante, url_citante = extrair_titulo_e_link(titulo_element)
            if not titulo_citante:
                print(f"\n[{i}] Título vazio")
                continue

            info_element = (resultado.locator(".gs_a").first)

            if info_element.count() > 0:
                info = (info_element.inner_text().strip())
            else:
                info = ""

            if " - " in info:
                autores = (info.split(" - ")[0].strip())
            else:
                autores = info

            ano_citante = (extrair_ano(info))
            partes = info.split(" - ")

            if len(partes) > 1:
                venue = (partes[1].strip())
            else:
                venue = None

            titulo_normalizado = (normalizar_texto(titulo_citante))
            duplicado = False

            for citacao in citacoes:
                titulo_existente = (normalizar_texto(citacao["titulo"]))

                if (titulo_existente == titulo_normalizado):
                    duplicado = True
                    break

            if duplicado:
                print(f"\n[{i}] IGNORADO (duplicado): {titulo_citante}")
                continue

            citacao = {
                "titulo": titulo_citante,
                "autores": autores,
                "ano": ano_citante,
                "veiculo_publicacao": venue,
                "url": url_citante,

                # Ainda serão preenchidos posteriormente
                "instituicoes": None,
                "idioma": None,
                "pais": None
            }

            citacoes.append(
                citacao
            )

            print(f"\n{len(citacoes)}. {titulo_citante}")
            print(f"Autores: {autores}")
            print(f"Ano: {ano_citante}")
            print(f"Venue: {venue}")
            print(f"URL: {url_citante}")

        novos = (len(citacoes) - quantidade_antes)

        print(f"\nNovos artigos nesta página: {novos}")
        print("\nProcurando próxima página...")

        links_navegacao = page.locator("#gs_n a")
        quantidade_links = (links_navegacao.count())
        print(f"Links de páginas encontrados: {quantidade_links}")

        proximos = []

        for i in range(quantidade_links):
            link_pagina = (links_navegacao.nth(i))
            href = (link_pagina.get_attribute("href"))

            if not href:
                continue

            parametros_link = parse_qs(urlparse(href).query)

            start_param = (parametros_link.get("start"))

            if not start_param:
                continue

            try:
                start = int(start_param[0])
            except ValueError:
                continue

            print("Página encontrada: start={start}")

            if start > start_atual:
                proximos.append((start, href))

        if not proximos:
            print("\nNenhuma página posterior encontrada.")
            print("Última página.")

            break

        proximos.sort(key=lambda x: x[0])
        proximo_start, proxima_url = (proximos[0])

        if (proximo_start in starts_processados):
            print("\nPróxima página já foi processada.")
            break

        if proxima_url.startswith("/"):
            url = (BASE_URL + proxima_url)

        else:
            url = proxima_url

        print("\nPróxima página:")

        print(url)
        print(f"Próximo start: {proximo_start}")

        page.wait_for_timeout(2500)
        pagina += 1

    print("\n" + "=-" * 30)
    print("Coleta finalizada!")
    print("=-" * 30)
    print(f"Total de citações coletadas: {len(citacoes)}")

    return citacoes

# -=-=-=-=-=- processa um artigo -=-=-=-=-=-=- #
def coletar_citacoes_artigo(page, titulo, ano=None,):
    """
    Busca o artigo e coleta todas as suas citações.
    """
    artigo = buscar_artigo(page, titulo, ano,)

    if artigo is None:
        print("\nArtigo não encontrado.")
        return []

    citacoes = buscar_citacoes(page, artigo["citation_url"],)

    # adiciona dados do artigo original
    for citacao in citacoes:
        citacao["titulo_original"] = titulo
        citacao["ano_original"] = ano
        citacao["titulo_encontrado"] = artigo["titulo"]
        citacao["url_original"] = artigo["url"]

    return citacoes