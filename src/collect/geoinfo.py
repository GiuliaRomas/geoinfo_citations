import time
import requests
import pandas as pd

from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse

import re
from html import unescape

import pymupdf
import io
from pypdf import PdfReader

# -=-=-=-=-=-=- configuracoes -=-=-=-=-=-=- #
URL_PORTAL_GEOINFO = ("http://mtc-m16d.sid.inpe.br/ibi/8JMKD3MGP7W/3GDK2ML")
URL_COLECAO_GEOINFO = ("http://mtc-m16d.sid.inpe.br/col/sid.inpe.br/mtc-m19/2014/06.02.15.03/doc/default.html")
REQUEST_DELAY = 2
MAX_RETRIES = 3

# -=-=-=-=-=-=- sessao -=-=-=-=-=-=- #
session = requests.Session()
session.headers.update({
    "User-Agent": (
        "Mozilla/5.0 "
        "(Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 "
        "(KHTML, like Gecko) "
        "Chrome/150.0 Safari/537.36"
    )
})

# -=-=-=-=-=-=- requisicao -=-=-=-=-=-=- #
def baixar_pagina(url, tentativas=MAX_RETRIES):
    """
    Faz uma requisição HTTP e retorna o HTML da página.
    """
    for tentativa in range(1, tentativas + 1):
        print(f"[Tentativa {tentativa}/{tentativas}] Requisitando: {url}")

        try:
            response = session.get(url, timeout=(10, 60))
            print(f"Status: {response.status_code}")

            response.raise_for_status()

            time.sleep(REQUEST_DELAY)
            return response.text
        except requests.RequestException as erro:
            print(f"[ERRO] Tentativa {tentativa}: {erro}")

            if tentativa < tentativas:
                espera = 5 * tentativa
                print(f"Aguardando {espera}s...")
                time.sleep(espera)
            else:
                print(f"Falha definitiva: {url}")
                raise


def obter_soup(url):
    """
    Faz uma requisição HTTP e retorna (BeautifulSoup, url_final).
    """
    response = session.get(url, timeout=30)
    response.raise_for_status()

    return BeautifulSoup(response.content, "html.parser"), response.url


# -=-=-=-=-=-=- frames -=-=-=-=-=-=- #
def extract_server_from_frame_body(frame_body_url):
    if not frame_body_url:
        return None

    host = urlparse(frame_body_url).hostname

    if not host:
        return None

    if not host.endswith(".sid.inpe.br"):
        return None

    server = host.replace(".sid.inpe.br", "")

    if not server.startswith("mtc-"):
        return None

    return server


def extract_server_from_url(url):
    """
    Extrai o servidor mtc-* diretamente da URL.
    """
    if not url:
        return None

    host = urlparse(url).netloc

    # remove porta, caso exista
    host = host.split(":")[0]

    if host.endswith(".sid.inpe.br"):
        server = host.replace(".sid.inpe.br", "")

        if server.startswith("mtc-"):
            return server

    return None


def obter_soup_body(url):
    """
    Acessa uma página e, caso ela utilize FRAMESET,
    acessa o frame chamado 'body'.
    """
    soup, url_final = obter_soup(url)

    if soup is None:
        raise RuntimeError(f"[ERRO] Não foi possível obter a página: {url}")

    # servidor vem da URL final (pós-redirect), não da URL pedida
    server = extract_server_from_url(url_final)
    print(f"Servidor obtido da URL final ({url_final}): {server}")

    # procura frame body
    frame_body = soup.find("frame", attrs={"name": "body"})

    if not frame_body:
        print("Frame 'body' não encontrado.")
        return soup, server

    src_body = frame_body.get("src")

    if not src_body:
        print("Frame 'body' não possui src.")
        return soup, server

    # resolve o src relativo em cima da URL final, não da original
    url_body = urljoin(url_final, src_body)
    print(f"Frame body encontrado:\n{url_body}")

    soup_body, url_body_final = obter_soup(url_body)

    if soup_body is None:
        raise RuntimeError(f"[ERRO] Não foi possível acessar o frame body: {url_body}")

    # o servidor que realmente serve o conteúdo é o da URL final do frame body
    server_body = extract_server_from_url(url_body_final)
    if server_body:
        server = server_body

    print(f"Servidor final: {server}")

    return soup_body, server

# -=-=-=-=-=-=- edicoes -=-=-=-=-=-=- #
def extrair_edicoes():
    """
    Extrai todas as edições disponíveis no GEOINFO.
    """
    print("\nExtraindo edições do GEOINFO...")

    soup, _ = obter_soup_body(URL_COLECAO_GEOINFO)

    edicoes = []

    tabelas = soup.find_all("table", class_="tgy")

    for tabela in tabelas:
        celulas = tabela.find_all("td")

        for td in celulas:
            info = td.find("font", class_="titulo_foto")

            if not info:
                continue

            texto_edicao = info.get_text(" ", strip=True)
            link = td.find("a", href=True)

            if not link:
                continue

            if not texto_edicao:
                print("[AVISO] Edição sem nome encontrada.")
                continue

            url_edicao = urljoin(URL_COLECAO_GEOINFO, link["href"])
            edicoes.append({"edicao": texto_edicao, "url_edicao": url_edicao})

    print(f"\nEdições encontradas: {len(edicoes)}")

    return edicoes

# -=-=-=-=-=-=- metadadados -=-=-=-=-=-=- #
def encontrar_url_metadata(url_artigo):
    print("\nAcessando artigo:")
    print(f"{url_artigo}")

    response = session.get(url_artigo, timeout=30) 
    response.raise_for_status()

    html = response.content.decode("ISO-8859-1", errors="replace")

    match_frame = re.search(r'<frame\b[^>]*\bname=["\']header["\'][^>]*>', html, flags=re.IGNORECASE)
    if not match_frame:
        return None

    frame_html = match_frame.group(0)
    match_src = re.search(r'\bsrc=["\']([^"\']+)["\']', frame_html, flags=re.IGNORECASE)
    if not match_src:
        return None

    src_header = unescape(match_src.group(1))
    print("Frame header encontrado.")

    match_metadata = re.search(r'metadatarepository=([^&"\']+)', src_header, flags=re.IGNORECASE)
    if not match_metadata:
        return None

    metadata_repository = match_metadata.group(1)
    host_artigo = urlparse(response.url).netloc

    url_metadata = f"http://{host_artigo}/{metadata_repository}?ibiurl.backgroundlanguage=en"

    return url_metadata


def extrair_metadados(url_metadata):
    """
    Extrai os metadados da página HTML do URLib.
    """
    print(f"Acessando metadata:\n{url_metadata}")

    soup, _ = obter_soup(url_metadata)

    metadados = {}

    for tr in soup.find_all("tr"):
        abbr = tr.find("abbr")

        if not abbr:
            continue

        campo = abbr.get_text(" ", strip=True)
        celulas = tr.find_all("td")

        if len(celulas) < 2:
            continue

        celula_valor = celulas[-1]

        # remove espaços excessivos, mas preserva separações por <br>
        for elemento in celula_valor.find_all("br"):
            elemento.replace_with("\n")

        valor = celula_valor.get_text(" ", strip=True)

        # normaliza quebras de linha
        valor = re.sub(r"\s*\n\s*", "\n", valor)
        valor = re.sub(r"[ \t]+", " ", valor)

        metadados[campo] = valor

    print(f"Campos encontrados: {len(metadados)}")

    return metadados


def extract_repository_from_goto(goto_url):
    """
    Extrai o repository da URL GOTO.
    """
    if not goto_url:
        return None

    if "/goto/" not in goto_url:
        return None

    repository = goto_url.split("/goto/", 1)[1]
    repository = repository.split("?", 1)[0]

    return repository


def gerar_hosts_repository(repository, server_edicao=None):
    """
    Gera possíveis hosts para um repository URLib.
    """
    if not repository:
        return []

    partes = repository.split("/")

    if len(partes) < 2:
        return []

    dominio = partes[0]
    servidor = partes[1]

    hosts = []

    # caso normal
    if dominio == "sid.inpe.br":
        servidor_limpo = servidor.replace("@80", "")
        hosts.append(f"{servidor_limpo}.sid.inpe.br")
    else: # Outros domínios:
        servidor_limpo = servidor.replace("@80", "")
        hosts.append(f"{servidor_limpo}.{dominio}")

    # servidor da edição como fallback
    if server_edicao:
        host_edicao = (f"{server_edicao}.sid.inpe.br")
        if host_edicao not in hosts:
            hosts.append(host_edicao)

    return hosts


def build_article_url(repository, host):
    """
    Constrói a URL da página do artigo a partir
    do repository e de um host candidato.
    """
    if not repository or not host:
        return None

    partes = repository.split("/")

    if len(partes) < 4:
        return None

    namespace = partes[0]
    repository_server = partes[1]
    year = partes[2]
    identifier = "/".join(partes[3:])

    return (
        f"http://{host}/col/"
        f"{namespace}/"
        f"{repository_server}/"
        f"{year}/"
        f"{identifier}/"
        f"doc/thisInformationItemHomePage.html"
    )


def encontrar_url_artigo(repository, server_edicao=None):
    """
    Tenta encontrar a URL real da página do artigo
    testando os hosts possíveis do repository.
    """
    if not repository:
        return None

    hosts = gerar_hosts_repository(repository, server_edicao)
    print(f"[DEBUG] Hosts candidatos: {hosts}")

    for host in hosts:
        url_artigo = build_article_url(repository, host)
        print(f"[DEBUG] Testando host '{host}':\n{url_artigo}")

        try:
            response = session.get(url_artigo, timeout=(10, 30), allow_redirects=True)

            if response.status_code == 200:
                print(f"[OK] Host funcionou: {host}")
                return response.url

            print(f"[AVISO] Host '{host}' retornou HTTP {response.status_code}")
        except requests.RequestException as erro:
            print(f"[AVISO] Falhou com host '{host}': {url_artigo}")

    print(f"[ERRO] Nenhum host funcionou para repository: {repository}")
    return None


def build_article_url_from_repository(repository, server):
    """
    Constrói a URL do artigo usando o servidor da edição.
    Funciona para repositories sid.inpe.br/mtc-*/...
    """
    if not repository:
        return None

    if not server:
        return None

    parts = repository.split("/")

    if len(parts) < 4:
        return None

    namespace = parts[0]
    repository_server = parts[1]
    year = parts[2]
    identifier = parts[3]

    return (
        f"http://{server}.sid.inpe.br/"
        f"col/{namespace}/{repository_server}/"
        f"{year}/{identifier}/"
        f"doc/thisInformationItemHomePage.html"
    )


def testar_url_artigo(url_artigo):
    """
    Verifica se uma URL de artigo realmente existe.
    """
    try:
        response = session.get(url_artigo, timeout=(10, 30), allow_redirects=True)

        if response.status_code == 200:
            return response.url
    except requests.RequestException:
        pass

    return None


def obter_url_artigo(url_goto, repository, server):
    """
    Obtém a URL real do artigo.
    """
    # tentativa normal
    url_artigo = build_article_url_from_repository(repository, server)

    if url_artigo:
        url_valida = testar_url_artigo(url_artigo)

        if url_valida:
            return url_valida

        print(f"[AVISO] Falhou com host '{server}': {url_artigo}")

    # fallback: resolver goto
    print("[AVISO] Tentando resolver URL GOTO diretamente...")

    url_resolvida = resolver_goto(url_goto)

    if url_resolvida:
        return url_resolvida

    # não encontrou
    print("[ERRO] Nenhum host funcionou para repository:")
    print(repository)

    return None

def testar_url_artigo(url_artigo):
    """
    Testa se a URL do artigo existe.
    """
    if not url_artigo:
        return None

    try:
        response = session.get(url_artigo, timeout=(10, 30), allow_redirects=True)
        response.raise_for_status()
        return response.url
    except requests.RequestException:
        return None
    
def resolver_host_via_goto(url_goto):
    """
    Segue a URL 'goto'  e descobre para qual host ela aponta hoje.
    """
    try:
        response = session.get(url_goto, timeout=30, allow_redirects=True)
        response.raise_for_status()
        host = urlparse(response.url).netloc.split(":")[0]
        return host.replace(".sid.inpe.br", "")
    except requests.RequestException as erro:
        print(f"[ERRO] Não foi possível resolver via goto: {erro}")
        return None


def resolver_url_artigo(repository, server_edicao, url_goto):
    """
    Descobre a URL correta da página do artigo testando:
      1. o servidor embutido no repository (caso mais comum);
      2. o servidor da página da edição;
      3. o host resolvido seguindo a URL goto.
    """
    if not repository:
        print("none repo")
        return None

    parts = repository.split("/")
    if len(parts) < 4:
        return None

    namespace, repository_server, year, identifier = parts[:4]

    candidatos = []
    if repository_server.startswith("mtc-"):
        candidatos.append(repository_server)
    if server_edicao and server_edicao not in candidatos:
        candidatos.append(server_edicao)

    for host in candidatos:
        url = (f"http://{host}.sid.inpe.br/col/{namespace}/{repository_server}/{year}/{identifier}/doc/thisInformationItemHomePage.html")
        if testar_url_artigo(url):
            return url
        print(f"[AVISO] Falhou com host '{host}': {url}")

    # segue o resolvedor oficial
    host_resolvido = resolver_host_via_goto(url_goto)
    if host_resolvido:
        url = (f"http://{host_resolvido}.sid.inpe.br/col/{namespace}/{repository_server}/{year}/{identifier}/doc/thisInformationItemHomePage.html")
        if testar_url_artigo(url):
            return url

    print(f"[ERRO] Nenhum host funcionou para repository: {repository}")
    return None

def resolver_goto(goto_url):
    """
    Resolve uma URL /goto/ e retorna a URL final real.
    """
    if not goto_url:
        return None

    print(f"[DEBUG] Resolvendo GOTO:")
    print(goto_url)

    try:
        response = session.get(goto_url, timeout=(10, 60), allow_redirects=True)
        response.raise_for_status()

        url_final = response.url

        print(f"[DEBUG] URL retornada pelo servidor:")
        print(url_final)

        # se o servidor realmente redirecionou
        if url_final != goto_url:
            return url_final

        # se não redirecionou, verifica o HTML
        soup = BeautifulSoup(response.content, "html.parser")

        # procura links
        for a in soup.find_all("a", href=True):
            href = a["href"]

            if "thisInformationItemHomePage" in href:
                url = urljoin(response.url, href)

                print(f"[DEBUG] Link encontrado:")
                print(url)

                return url

        # procura frames
        for frame in soup.find_all("frame", src=True):
            src = frame["src"]

            if "thisInformationItemHomePage" in src:
                url = urljoin(response.url, src)

                print(f"[DEBUG] Frame encontrado:")
                print(url)

                return url

        # procura meta refresh
        meta = soup.find("meta", attrs={"http-equiv": re.compile("^refresh$", re.I)})

        if meta:
            content = meta.get("content", "")
            match = re.search(r"url\s*=\s*(.+)", content, flags=re.I)

            if match:
                url = urljoin(response.url, match.group(1).strip())

                print(f"[DEBUG] Meta refresh encontrado:")
                print(url)

                return url

        print("[DEBUG] GOTO não redirecionou nem apresentou URL.")
        return None
    except requests.RequestException as erro:
        print(f"[ERRO] Falha ao resolver GOTO:\n{goto_url}\n{erro}")
        return None

# -=-=-=-=-=-=- artigo -=-=-=-=-=-=- #
def coletar_artigo(url_artigo, edicao, url_edicao):
    """
    Coleta os metadados de um artigo.
    """
    # Encontra metadata
    url_metadata = encontrar_url_metadata(url_artigo)

    if not url_metadata:
        print("Metadata não encontrada.")
        return None

    # extrai metadados
    metadados = extrair_metadados(url_metadata)

    artigo = {
        "titulo": metadados.get("Title"),
        "ano": metadados.get("Year"),
        "autores": metadados.get("Author"),
        "instituicoes": metadados.get("Affiliation"),
        "edicao": edicao,
        "identificador": metadados.get("Identifier"),
        "language": metadados.get("Language"),

        # rastreabilidade
        "url_edicao": url_edicao,
        "url_artigo": url_artigo,
        "url_metadata": url_metadata
    }

    return artigo

# -=-=-=-=-=-=- edicao -=-=-=-=-=-=- #
def coletar_edicao(edicao, url_edicao):
    """
    Coleta todos os artigos de uma edição do GEOINFO.
    """
    print("\n" + "=-" * 30)
    print(f"Processando edição: {edicao}")
    print("=-" * 30)

    if edicao is None or pd.isna(edicao) or str(edicao).strip() == "":
        print(f"[ERRO] Nome da edição inválido: {repr(edicao)}")
        return []

    edicao = str(edicao).strip()

    print(f"[DEBUG] Edição recebida: {repr(edicao)}")
    print(f"[DEBUG] URL edição: {url_edicao}")

    # Acessa página da edição
    soup, server = obter_soup_body(url_edicao)
    
    # encontra os artigos
    tabelas = soup.find_all("table", class_="titleAuthorTABLE")
    print(f"Artigos encontrados: {len(tabelas)}")

    artigos = []

    # percorre os artigos
    for numero, tabela in enumerate(tabelas, start=1):
        link = tabela.find("a", href=True)

        if not link:
            continue

        url_goto = urljoin(url_edicao, link["href"])
        repository = extract_repository_from_goto(url_goto)
        url_artigo = encontrar_url_artigo(repository, server_edicao=server)

        if not url_artigo:
            print("[ERRO] Não foi possível normalizar a URL do artigo.")
            continue

        print(f"\n[{numero}/{len(tabelas)}]")
        print(f"URL artigo:\n{url_artigo}")

        try:
            artigo = coletar_artigo(url_artigo=url_artigo, edicao=edicao, url_edicao=url_edicao)

            if artigo:
                artigo["edicao"] = edicao
                artigos.append(artigo)
        except Exception as erro:
            print("\n[ERRO] Erro ao coletar artigo")
            print(f"URL: {url_artigo}")
            print(f"Erro: {erro}")

        print(f"\nArtigos coletados na edição: {len(artigos)}")
    return artigos

# -=-=-=-=-=-=- coleta todas edicoes do geoinfo -=-=-=-=-=-=- #
def coletar_geoinfo():
    """
    Coleta todos os artigos de todas as edições
    do GEOINFO.
    """
    print("\n" + "=-" * 30)
    print("Iniciando a coleta de dados")
    print("=-" * 30)

    # encontra as edições
    edicoes = extrair_edicoes()
    total_edicoes = len(edicoes)

    registros = []

    print(f"\nTotal de edições: {total_edicoes}")

    # percorre as edições
    for numero, edicao in enumerate(edicoes, start=1):
        print("\n"+ "-" * 60)
        print(f"Edição {numero}/{total_edicoes}")
        print(edicao["edicao"])
        print("-" * 60)

        try:
            artigos = coletar_edicao(edicao=edicao["edicao"], url_edicao=edicao["url_edicao"])
            registros.extend(artigos)
        except Exception as erro:
            print(f"\n[ERRO]:\n{edicao['edicao']}\n{erro}")
            continue

        print(f"\nTotal acumulado: {len(registros)} artigos")

    # dataframe final
    dados = pd.DataFrame(registros)

    print("\n" + "=-" * 30)
    print("[SUCESSO] Coleta de dados do GEOINFO concluída!")
    print(f"Total de artigos: {len(dados)}")
    print("=-" * 30)

    return dados