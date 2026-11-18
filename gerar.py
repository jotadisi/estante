#!/usr/bin/env python3
"""Gera a Estante a partir de livros.json.

    python gerar.py                 -> escreve index.html (site completo, para o GitHub Pages)
    python gerar.py caminho.html    -> também escreve uma prévia sem <html>/<head> (formato de Artifact)

Para acrescentar um livro: edite livros.json e rode de novo.
"""
import html
import json
import sys
from datetime import date
from pathlib import Path

PASTA = Path(__file__).resolve().parent
dados = json.loads((PASTA / "livros.json").read_text(encoding="utf-8"))
TAG = dados["tag"]
e = html.escape

AVISO = "Como participante do Programa de Associados da Amazon, sou remunerado pelas compras qualificadas efetuadas."

CSS = """
/* Layout: ex-libris no topo, depois uma prateleira por assunto; cada livro é uma capa
   de tecido (cor do assunto, título em dourado) com a nota pessoal logo abaixo. */
:root {
  --pedra: #eceff1;
  --papel: #fbfbfa;
  --tinta: #1c2026;
  --apagado: #5b6570;
  --linha: #d3d9de;
  --dourado: #e2cf97;
  --acento: #6b2733;
  --arquitetura: #3c4f5e;
  --estetica: #6b2733;
  --filosofia: #23305a;
  --literatura: #2f4b3b;
  --serif: "EB Garamond", Garamond, "Times New Roman", serif;
  --sans: "Source Sans 3", "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
}
@media (prefers-color-scheme: dark) {
  :root:not([data-theme="light"]) {
    --pedra: #121417; --papel: #1a1d22; --tinta: #e8eaed; --apagado: #a3abb4; --linha: #2c3239;
    --dourado: #e6d5a2; --acento: #e0a0aa; color-scheme: dark;
  }
}
:root[data-theme="dark"] {
  --pedra: #121417; --papel: #1a1d22; --tinta: #e8eaed; --apagado: #a3abb4; --linha: #2c3239;
  --dourado: #e6d5a2; --acento: #e0a0aa; color-scheme: dark;
}
* { box-sizing: border-box; }
body { background: var(--pedra); color: var(--tinta); font-family: var(--sans); font-size: 16px; line-height: 1.55; margin: 0; }
.pagina {
  max-width: 1080px; margin: 0 auto; padding-block: 28px 56px;
  padding-left: max(16px, env(safe-area-inset-left, 0px)); padding-right: max(16px, env(safe-area-inset-right, 0px));
  display: grid; gap: 44px;
}
h1, h2, h3 { font-family: var(--serif); font-weight: 600; margin: 0; text-wrap: balance; }
p { margin: 0; }
a { color: var(--acento); }
:focus-visible { outline: 2px solid var(--acento); outline-offset: 3px; }
.rotulo { font-size: 12px; letter-spacing: 0.16em; text-transform: uppercase; color: var(--apagado); }

/* Ex-libris */
.exlibris { justify-self: center; text-align: center; display: grid; gap: 10px; max-width: 640px; padding: 28px 24px;
  border: 1px solid var(--tinta); outline: 1px solid var(--tinta); outline-offset: 5px; background: var(--papel); }
.exlibris h1 { font-size: clamp(36px, 8vw, 56px); line-height: 1; letter-spacing: -0.01em; }
.exlibris .sub { color: var(--apagado); font-size: 17px; }
nav.assuntos { display: flex; flex-wrap: wrap; justify-content: center; gap: 8px; }
nav.assuntos a { text-decoration: none; color: var(--tinta); border: 1px solid var(--linha); background: var(--papel);
  padding: 6px 14px; border-radius: 999px; font-size: 15px; }
nav.assuntos a:hover { border-color: var(--tinta); }

/* Prateleiras */
section.prateleira { display: grid; gap: 18px; scroll-margin-top: 16px; }
.prateleira-topo { display: grid; gap: 4px; border-bottom: 2px solid var(--tinta); padding-bottom: 10px; }
.prateleira-topo h2 { font-size: clamp(28px, 5vw, 36px); }
.prateleira-topo p { color: var(--apagado); }
.livros { display: grid; grid-template-columns: repeat(auto-fill, minmax(230px, 1fr)); gap: 18px; }

/* Livro */
.livro { display: grid; grid-template-rows: auto 1fr; background: var(--papel); border: 1px solid var(--linha); min-width: 0; }
.capa { padding: 22px 18px 18px; display: grid; gap: 6px; align-content: end; min-height: 150px; color: var(--dourado);
  border-bottom: 3px double var(--dourado); }
.arquitetura .capa { background: var(--arquitetura); }
.estetica .capa { background: var(--estetica); }
.filosofia .capa { background: var(--filosofia); }
.literatura .capa { background: var(--literatura); }
.capa h3 { font-size: 24px; line-height: 1.12; }
.capa .autor { font-size: 13px; letter-spacing: 0.12em; text-transform: uppercase; opacity: 0.9; }
.corpo { padding: 16px 18px 18px; display: grid; gap: 10px; align-content: start; }
.detalhe { font-size: 13px; color: var(--apagado); }
.nota { font-family: var(--serif); font-size: 18px; line-height: 1.4; }
.ver { justify-self: start; margin-top: 4px; text-decoration: none; font-weight: 600; font-size: 15px; color: var(--acento);
  border-bottom: 1px solid currentColor; padding-bottom: 1px; }
.ver::after { content: " \\2192"; }

footer.rodape { border-top: 1px solid var(--linha); padding-top: 18px; display: grid; gap: 6px; color: var(--apagado); font-size: 14px; }
@media (prefers-reduced-motion: no-preference) { html { scroll-behavior: smooth; } }
"""

FONTES = ('<link rel="preconnect" href="https://fonts.googleapis.com">'
          '<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>'
          '<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=EB+Garamond:ital,wght@0,400;0,600;1,400'
          '&family=Source+Sans+3:wght@400;600&display=swap">')


def card(livro, secao):
    link = f"https://www.amazon.com.br/dp/{livro['asin']}?tag={TAG}"
    detalhe = f'<p class="detalhe">{e(livro["detalhe"])}</p>' if livro.get("detalhe") else ""
    return (f'<article class="livro {secao}">'
            f'<div class="capa"><h3>{e(livro["titulo"])}</h3><p class="autor">{e(livro["autor"])}</p></div>'
            f'<div class="corpo">{detalhe}<p class="nota">{e(livro["nota"])}</p>'
            f'<a class="ver" href="{e(link)}" target="_blank" rel="sponsored noopener">Ver na Amazon</a></div>'
            f'</article>')


def corpo():
    total = sum(len(s["livros"]) for s in dados["secoes"])
    nav = "".join(f'<a href="#{s["id"]}">{e(s["nome"])}</a>' for s in dados["secoes"])
    secoes = "".join(
        f'<section class="prateleira" id="{s["id"]}" aria-labelledby="t-{s["id"]}">'
        f'<div class="prateleira-topo"><h2 id="t-{s["id"]}">{e(s["nome"])}</h2><p>{e(s["descricao"])}</p></div>'
        f'<div class="livros">{"".join(card(l, s["id"]) for l in s["livros"])}</div></section>'
        for s in dados["secoes"])
    hoje = date.today().strftime("%d/%m/%Y")
    return (f'<div class="pagina">'
            f'<header class="exlibris"><span class="rotulo">Ex libris · {total} livros</span>'
            f'<h1>{e(dados["nome"])}</h1><p class="sub">{e(dados["subtitulo"])}</p>'
            f'<nav class="assuntos" aria-label="Assuntos">{nav}</nav></header>'
            f'{secoes}'
            f'<footer class="rodape"><p>{e(AVISO)}</p>'
            f'<p>Os links levam à Amazon.com.br. Preço e disponibilidade são os que a Amazon mostrar no momento da compra.</p>'
            f'<p>Estante atualizada em {hoje}.</p></footer></div>')


def cabeca(com_meta_artifact: bool):
    titulo = f'<title>{e(dados["nome"])}</title>'
    desc = f'<meta name="description" content="{e(dados["subtitulo"])}">'
    lados = '<meta name="claude:viewport-fit-sides" content="cover">' if com_meta_artifact else ""
    return f'{titulo}{lados}{desc}{FONTES}<style>{CSS}</style>'


site = ('<!doctype html><html lang="pt-BR"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">'
        f'{cabeca(False)}</head><body>{corpo()}</body></html>\n')
(PASTA / "index.html").write_text(site, encoding="utf-8")
print("index.html gerado")

if len(sys.argv) > 1:
    Path(sys.argv[1]).write_text(cabeca(True) + corpo() + "\n", encoding="utf-8")
    print("prévia gerada em", sys.argv[1])
