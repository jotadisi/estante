#!/usr/bin/env python3
"""Gera a Estante a partir de livros.json.

    python gerar.py                 -> escreve index.html (site completo, para o GitHub Pages)
    python gerar.py caminho.html    -> também escreve uma prévia sem <html>/<head> (formato de Artifact)

Para acrescentar um livro: edite livros.json e rode de novo.
Capa: ponha a imagem em capas/ASIN.jpg (400 px de largura basta). Sem imagem, o livro ganha a capa desenhada.
"""
import html
import json
import struct
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

PASTA = Path(__file__).resolve().parent
dados = json.loads((PASTA / "livros.json").read_text(encoding="utf-8"))
TAG = dados["tag"]
e = html.escape

# Ofertas conferidas à mão: cada selo vale por algumas horas e some sozinho depois (o JavaScript
# da página compara com o relógio de quem visita). Sem JavaScript, nenhum selo aparece.
OFERTAS = dados.get("ofertas") or {}
ITENS_OFERTA = OFERTAS.get("itens") or {}
if ITENS_OFERTA:
    _conferido = datetime.fromisoformat(OFERTAS["conferido_em"])
    OFERTAS_ATE = (_conferido + timedelta(hours=OFERTAS.get("validade_horas", 24))).isoformat()
    OFERTAS_QUANDO = _conferido.strftime("%d/%m às %Hh%M")
else:
    OFERTAS_ATE = ""
    OFERTAS_QUANDO = ""

AVISO = "Como participante do Programa de Associados da Amazon, sou remunerado pelas compras qualificadas efetuadas."


def dimensoes_jpeg(caminho: Path):
    """Largura e altura de um JPEG, para o navegador reservar o espaço da capa antes de ela carregar."""
    b = caminho.read_bytes()
    i = 2
    while i < len(b) - 9:
        if b[i] != 0xFF:
            i += 1
            continue
        if b[i + 1] in (0xC0, 0xC1, 0xC2):
            altura, largura = struct.unpack(">HH", b[i + 5:i + 9])
            return largura, altura
        i += 2 + struct.unpack(">H", b[i + 2:i + 4])[0]
    return None


CAPAS = {}
for _arq in sorted((PASTA / "capas").glob("*.jpg")):
    _dim = dimensoes_jpeg(_arq)
    if _dim:
        CAPAS[_arq.stem] = _dim

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

/* Livro com foto da capa: a capa fica de pé sobre o tecido da prateleira; título e autor descem para o corpo */
.com-capa .capa { height: 270px; min-height: 0; padding: 20px 18px; display: grid; place-items: center; align-content: center; }
.com-capa .capa a { display: block; line-height: 0; max-width: 100%; }
.com-capa .capa img { display: block; width: auto; height: auto; max-width: 100%; max-height: 228px; border-radius: 1px 3px 3px 1px;
  box-shadow: 0 1px 2px rgba(0,0,0,.3), 0 10px 22px rgba(0,0,0,.35); }
.ficha { display: grid; gap: 3px; }
.ficha h3 { font-size: 22px; line-height: 1.15; }
.ficha .autor { font-size: 12px; letter-spacing: 0.12em; text-transform: uppercase; color: var(--apagado); }
.selo-oferta { z-index: 1; box-shadow: 0 1px 3px rgba(0,0,0,.3); }

/* Selos de oferta: escondidos por padrão; o script só mostra enquanto a conferência vale */
.capa { position: relative; }
.selo-oferta, .chip-ofertas, .aviso-ofertas { display: none; }
.ofertas-validas .selo-oferta { display: inline-block; }
.ofertas-validas .chip-ofertas { display: inline-flex; }
.ofertas-validas .aviso-ofertas { display: block; }
.selo-oferta { position: absolute; top: 12px; right: 12px; background: var(--dourado); color: #1c2026;
  font-size: 12px; font-weight: 600; letter-spacing: 0.04em; padding: 3px 8px; border-radius: 3px; }
.livro.em-oferta { border-color: var(--dourado); box-shadow: 0 0 0 1px var(--dourado); }
.chip-ofertas { align-items: center; gap: 6px; cursor: pointer; font: inherit; font-size: 15px; font-weight: 600;
  padding: 6px 14px; border-radius: 999px; border: 1px solid var(--tinta); background: var(--tinta); color: var(--papel); }
.chip-ofertas[aria-pressed="true"] { background: var(--dourado); color: #1c2026; border-color: var(--dourado); }
.aviso-ofertas { font-size: 13px; color: var(--apagado); }
.so-ofertas .livro:not(.em-oferta), .so-ofertas .prateleira:not(.tem-oferta) { display: none; }

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
    oferta = ITENS_OFERTA.get(livro["asin"])
    classe = f"livro {secao} em-oferta" if oferta else f"livro {secao}"
    selo = f'<span class="selo-oferta">★ {e(oferta)}</span>' if oferta else ""
    ver = f'<a class="ver" href="{e(link)}" target="_blank" rel="sponsored noopener">Ver na Amazon</a>'
    dim = CAPAS.get(livro["asin"])
    if dim:
        # A imagem repete o link do botão; fica fora da ordem de tabulação para não ser lida duas vezes
        return (f'<article class="{classe} com-capa">'
                f'<div class="capa">{selo}<a href="{e(link)}" target="_blank" rel="sponsored noopener" tabindex="-1" aria-hidden="true">'
                f'<img src="capas/{e(livro["asin"])}.jpg" width="{dim[0]}" height="{dim[1]}" alt="" loading="lazy" decoding="async"></a></div>'
                f'<div class="corpo"><div class="ficha"><h3>{e(livro["titulo"])}</h3><p class="autor">{e(livro["autor"])}</p></div>'
                f'{detalhe}<p class="nota">{e(livro["nota"])}</p>{ver}</div>'
                f'</article>')
    return (f'<article class="{classe}">'
            f'<div class="capa">{selo}<h3>{e(livro["titulo"])}</h3><p class="autor">{e(livro["autor"])}</p></div>'
            f'<div class="corpo">{detalhe}<p class="nota">{e(livro["nota"])}</p>{ver}</div>'
            f'</article>')


SCRIPT = """<script>
(function () {
  var p = document.querySelector('.pagina');
  var ate = p && p.getAttribute('data-ofertas-ate');
  if (!ate || Date.now() >= Date.parse(ate)) return;
  p.classList.add('ofertas-validas');
  var b = document.querySelector('.chip-ofertas');
  if (b) b.addEventListener('click', function () {
    var on = p.classList.toggle('so-ofertas');
    b.setAttribute('aria-pressed', String(on));
  });
})();
</script>"""


def corpo():
    total = sum(len(s["livros"]) for s in dados["secoes"])
    n_ofertas = sum(1 for s in dados["secoes"] for l in s["livros"] if l["asin"] in ITENS_OFERTA)
    nav = "".join(f'<a href="#{s["id"]}">{e(s["nome"])}</a>' for s in dados["secoes"])
    if n_ofertas:
        nav += f'<button type="button" class="chip-ofertas" aria-pressed="false">★ Em oferta ({n_ofertas})</button>'
    aviso_ofertas = (f'<p class="aviso-ofertas">★ Ofertas conferidas na Amazon em {OFERTAS_QUANDO}. '
                     f'Preço e desconto podem ter mudado; confira na página do livro.</p>') if n_ofertas else ""
    secoes = ""
    for s in dados["secoes"]:
        tem = any(l["asin"] in ITENS_OFERTA for l in s["livros"])
        secoes += (f'<section class="prateleira{" tem-oferta" if tem else ""}" id="{s["id"]}" aria-labelledby="t-{s["id"]}">'
                   f'<div class="prateleira-topo"><h2 id="t-{s["id"]}">{e(s["nome"])}</h2><p>{e(s["descricao"])}</p></div>'
                   f'<div class="livros">{"".join(card(l, s["id"]) for l in s["livros"])}</div></section>')
    hoje = date.today().strftime("%d/%m/%Y")
    return (f'<div class="pagina" data-ofertas-ate="{e(OFERTAS_ATE)}">'
            f'<header class="exlibris"><span class="rotulo">Ex libris · {total} livros</span>'
            f'<h1>{e(dados["nome"])}</h1><p class="sub">{e(dados["subtitulo"])}</p>'
            f'<nav class="assuntos" aria-label="Assuntos">{nav}</nav>{aviso_ofertas}</header>'
            f'{secoes}'
            f'<footer class="rodape"><p>{e(AVISO)}</p>'
            f'<p>Os links levam à Amazon.com.br. Preço e disponibilidade são os que a Amazon mostrar no momento da compra.</p>'
            f'{"<p>Imagens de capa: © das respectivas editoras.</p>" if CAPAS else ""}'
            f'<p>Estante atualizada em {hoje}.</p></footer></div>{SCRIPT}')


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
