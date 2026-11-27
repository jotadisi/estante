#!/usr/bin/env python3
"""Atualiza os selos de oferta da Estante com os preços da API Creators da Amazon.

Roda todo dia no GitHub Actions (.github/workflows/ofertas.yml), antes do gerar.py:

    python3 ofertas.py     consulta os livros de livros.json e reescreve ofertas.json
    python3 gerar.py       refaz o index.html com os selos

Regra: livro em estoque com preço 40% ou mais abaixo do preço de referência da Amazon (o preço
de capa) ganha o selo "Em oferta". O limite muda com a variável OFERTA_MINIMA (ex.: 30 = 30%).
O selo vale 24 horas, porque a Amazon não permite usar dados da API por mais tempo, e some
sozinho da página. Nenhum preço é gravado: só quais livros estavam em oferta e a hora.

Precisa dos segredos AMAZON_CREDENTIAL_ID e AMAZON_CREDENTIAL_SECRET.
"""
from __future__ import annotations

import json
import os
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

PASTA = Path(__file__).resolve().parent
ARQ_LIVROS = PASTA / "livros.json"
ARQ_OFERTAS = PASTA / "ofertas.json"

BRASILIA = timezone(timedelta(hours=-3), "Brasília")
MARKETPLACE = "www.amazon.com.br"
URL_TOKEN = "https://api.amazon.com/auth/o2/token"  # credenciais 3.1 (América do Norte + Brasil)
URL_GETITEMS = "https://creatorsapi.amazon/catalog/v1/getItems"
ESCOPO = "creatorsapi::default"
RECURSOS = ["offersV2.listings.price", "offersV2.listings.availability", "offersV2.listings.isBuyBoxWinner"]
POR_CHAMADA = 10  # máximo aceito pela GetItems
SEM_ESTOQUE = {"OUT_OF_STOCK", "UNAVAILABLE"}
VALIDADE_HORAS = 24
ROTULO = "Em oferta"
TAG_PADRAO = "joaoestudos-20"


class ErroAmazon(Exception):
    """Falha ao falar com a Amazon."""


class ContaNaoElegivel(ErroAmazon):
    """A Amazon suspendeu a consulta de preços (menos de 10 vendas qualificadas em 30 dias)."""


def http_json(url: str, dados: dict, cabecalhos: dict | None = None,
              servico: str = "a Amazon", timeout: int = 30) -> dict:
    cab = {"User-Agent": "estante-ofertas/1.0", "Accept": "application/json",
           "Content-Type": "application/json"}
    cab.update(cabecalhos or {})
    pedido = urllib.request.Request(url, data=json.dumps(dados).encode("utf-8"), headers=cab, method="POST")
    try:
        with urllib.request.urlopen(pedido, timeout=timeout) as resposta:
            return json.loads(resposta.read().decode("utf-8") or "{}")
    except urllib.error.HTTPError as erro:
        detalhe = erro.read().decode("utf-8", "replace")[:600]
        raise ErroAmazon(f"{servico} respondeu HTTP {erro.code}: {detalhe}") from None
    except urllib.error.URLError as erro:
        raise ErroAmazon(f"não consegui falar com {servico}: {erro.reason}") from None


def obter_token(credential_id: str, secret: str) -> str:
    resposta = http_json(os.environ.get("AMAZON_TOKEN_URL") or URL_TOKEN, {
        "grant_type": "client_credentials",
        "client_id": credential_id,
        "client_secret": secret,
        "scope": os.environ.get("AMAZON_TOKEN_SCOPE") or ESCOPO,
    }, servico="a Amazon (login da Creators API)")
    token = resposta.get("access_token")
    if not token:
        raise ErroAmazon("a Amazon não devolveu access_token; confira as credenciais da Creators API")
    return token


def _valor(bruto) -> float | None:
    try:
        valor = float(bruto)
    except (TypeError, ValueError):
        return None
    return valor if valor > 0 else None


def preco_e_referencia(item: dict) -> tuple[float | None, float | None]:
    """Preço atual e preço de referência (capa) da oferta principal. Sem estoque: (None, None)."""
    listagens = (item.get("offersV2") or {}).get("listings") or []
    if not listagens:
        return None, None
    escolhida = next((l for l in listagens if l.get("isBuyBoxWinner")), listagens[0])
    if (escolhida.get("availability") or {}).get("type") in SEM_ESTOQUE:
        return None, None
    preco = escolhida.get("price") or {}
    base = preco.get("savingBasis") or {}
    return _valor((preco.get("money") or {}).get("amount")), _valor((base.get("money") or {}).get("amount"))


def consultar(asins: list[str], token: str, tag: str) -> dict[str, tuple]:
    precos: dict[str, tuple] = {}
    for inicio in range(0, len(asins), POR_CHAMADA):
        if inicio:
            time.sleep(1.1)  # gentileza com o limite de requisições
        try:
            resposta = http_json(URL_GETITEMS, {
                "itemIds": asins[inicio:inicio + POR_CHAMADA],
                "itemIdType": "ASIN",
                "partnerTag": tag,
                "marketplace": MARKETPLACE,
                "resources": RECURSOS,
            }, {"Authorization": f"Bearer {token}", "x-marketplace": MARKETPLACE},
                servico="a Amazon (GetItems)")
        except ErroAmazon as erro:
            if "AssociateNotEligible" in str(erro):
                raise ContaNaoElegivel(str(erro)) from None
            raise
        resultado = resposta.get("itemsResult") or resposta.get("itemResults") or {}
        for item in resultado.get("items") or []:
            asin = (item.get("asin") or "").upper()
            if asin:
                precos[asin] = preco_e_referencia(item)
        for erro in resposta.get("errors") or []:
            print(f"  aviso da Amazon: {erro.get('code')}: {erro.get('message')}")
    return precos


def escolher_ofertas(precos: dict[str, tuple], minima: float, ordem: list[str]) -> dict[str, str]:
    """ASIN -> rótulo do selo, na ordem da estante."""
    em_oferta = {asin for asin, (preco, ref) in precos.items()
                 if preco and ref and preco <= ref * (1 - minima)}
    return {asin: ROTULO for asin in ordem if asin in em_oferta}


def ler_minima() -> float:
    bruto = os.environ.get("OFERTA_MINIMA", "").strip().replace("%", "").replace(",", ".")
    if not bruto:
        return 0.40
    try:
        valor = float(bruto)
    except ValueError:
        raise SystemExit(f"OFERTA_MINIMA inválida: {bruto!r}") from None
    return valor / 100 if valor > 1 else valor  # aceita "40", "40%" ou "0.40"


def main() -> None:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except AttributeError:
        pass
    credential_id = os.environ.get("AMAZON_CREDENTIAL_ID", "").strip()
    secret = os.environ.get("AMAZON_CREDENTIAL_SECRET", "").strip()
    tag = os.environ.get("AMAZON_PARTNER_TAG", "").strip() or TAG_PADRAO
    if not (credential_id and secret):
        raise SystemExit("Faltam os segredos AMAZON_CREDENTIAL_ID e AMAZON_CREDENTIAL_SECRET no repositório.")

    dados = json.loads(ARQ_LIVROS.read_text(encoding="utf-8"))
    livros = [livro for secao in dados["secoes"] for livro in secao["livros"]]
    asins = [livro["asin"].upper() for livro in livros]
    minima = ler_minima()
    agora = datetime.now(BRASILIA).replace(second=0, microsecond=0)

    print(f"{len(asins)} livros na estante. Consultando a Amazon...")
    try:
        precos = consultar(asins, obter_token(credential_id, secret), tag)
    except ContaNaoElegivel:
        # Não é erro do robô: a Amazon só libera a API com 10 vendas em 30 dias. Os selos
        # antigos somem sozinhos quando vencem; amanhã ele tenta de novo.
        print("A Amazon suspendeu a consulta de preços (AssociateNotEligible). Nada foi alterado.")
        return
    except ErroAmazon as erro:
        raise SystemExit(f"Erro: {erro}")

    itens = escolher_ofertas(precos, minima, asins)
    for livro in livros:
        asin = livro["asin"].upper()
        situacao = "★ em oferta" if asin in itens else ("sem preço hoje" if not precos.get(asin, (None,))[0] else "–")
        print(f"  {situacao:15} {livro['titulo'][:60]}")

    ARQ_OFERTAS.write_text(json.dumps({
        "conferido_em": agora.isoformat(),
        "validade_horas": VALIDADE_HORAS,
        "criterio": f"API da Amazon: {round(minima * 100)}% ou mais abaixo do preço de capa",
        "itens": itens,
    }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"\n{len(itens)} livro(s) em oferta. Selos válidos até {agora + timedelta(hours=VALIDADE_HORAS):%d/%m %Hh%M}.")


if __name__ == "__main__":
    main()
