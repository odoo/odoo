// ══════════════════════════════════════════════════════════════════════
//  TIMBRE.TYP — Biblioteca de Componentes — Prefeitura de Borba/AM
//  Secretaria Municipal de Saúde — SEMSA
//
//  Este módulo exporta:
//    • Paleta de cores institucional
//    • Variáveis de imagem (brasão, texto do header, barra do rodapé)
//    • Componentes de conteúdo: caixa, legal, alerta, aviso, info,
//      ficha, tabela, falha-card, check
//
//  COMO USAR — no seu documento .typ:
//    #import "timbre.typ": *
//
//    // Imagens do timbre (declaradas aqui no escopo raiz)
//    #let _b = timbre-brasao
//    #let _h = timbre-header-text
//    #let _f = timbre-footer
//
//    // Configurar página com timbre
//    #set page(
//      header: context {
//        if counter(page).get().first() > 1 [
//          #grid(columns: (auto, 1fr), column-gutter: 12pt, align: horizon,
//            _b, _h)
//          #line(length: 100%, stroke: (paint: c-rule, thickness: 0.6pt))
//        ]
//      },
//      footer: context {
//        if counter(page).get().first() > 1 [
//          #line(length: 100%, stroke: (paint: c-rule, thickness: 0.4pt))
//          #v(2pt) #_f
//        ]
//      },
//    )
//
//  NOTA TÉCNICA IMPORTANTE:
//    As variáveis timbre-brasao, timbre-header-text e timbre-footer
//    devem ser reatribuídas a novas variáveis LOCAIS no arquivo que
//    importa este módulo (conforme exemplo acima). Isso garante que
//    o renderer Typst resolva os SVGs corretamente no contexto do
//    header/footer.
//
//  ASSETS NECESSÁRIOS (na pasta assets/ ao lado deste arquivo):
//    assets/brasao.svg         — brasão municipal em SVG
//    assets/header_text.svg    — bloco tipográfico BORBA + slogan
//    assets/footer_timbre.svg  — barra tricolor verde|azul|amarelo + endereço
// ══════════════════════════════════════════════════════════════════════

// ── Paleta institucional ────────────────────────────────────────────────
#let c-navy     = rgb("#1A3A5C")
#let c-blue     = rgb("#2E75B6")
#let c-green    = rgb("#15803D")
#let c-gbg      = rgb("#F0FDF4")
#let c-amber    = rgb("#92400E")
#let c-red      = rgb("#991B1B")
#let c-rbg      = rgb("#FEF2F2")
#let c-ibdr     = rgb("#1E40AF")
#let c-ibg      = rgb("#EFF6FF")
#let c-stripe   = rgb("#F8FAFC")
#let c-rule     = rgb("#E2E8F0")
#let c-muted    = rgb("#64748B")
#let c-blue-lt  = rgb("#93C5DE")
#let c-blue-md  = rgb("#5B8DB8")
#let c-navy-dk  = rgb("#243F6A")
#let c-muted-lt = rgb("#94A3B8")

// ── Variáveis de imagem exportadas ─────────────────────────────────────
// Use estas variáveis como base, copiando para variáveis locais
// no arquivo principal antes de passá-las ao set page().
#let timbre-brasao      = image("assets/brasao.svg",         height: 1.9cm)
#let timbre-header-text = image("assets/header_text.svg",    height: 1.9cm)
#let timbre-footer      = image("assets/footer_timbre.svg",  width: 100%)

// ══════════════════════════════════════════════════════════════════════
//  COMPONENTES
// ══════════════════════════════════════════════════════════════════════

// ── Caixa lateral colorida ──────────────────────────────────────────────
// stroke nativo — sem block(height:100%) que causaria gaps de página
#let caixa(cor, titulo, corpo) = block(
  width: 100%,
  fill: cor.lighten(92%),
  stroke: (left: (paint: cor, thickness: 4pt)),
  inset: (left: 14pt, right: 12pt, top: 10pt, bottom: 10pt),
  radius: (right: 3pt),
  spacing: 0.9em,
)[
  #if titulo != "" [
    #text(weight: "semibold", size: 9pt, fill: cor, tracking: 0.5pt)[#upper(titulo)]
    #linebreak()
    #v(2pt)
  ]
  #set text(size: 10pt)
  #corpo
]

#let legal(corpo)       = caixa(c-green, "Base Legal", corpo)
#let alerta(corpo)      = caixa(c-amber, "Atenção", corpo)
#let aviso(tit, corpo)  = caixa(c-red, tit, corpo)
#let info(tit, corpo)   = caixa(c-ibdr, tit, corpo)

// ── Ficha de identificação ──────────────────────────────────────────────
// #ficha(("Label", "Valor"), ("Label 2", "Valor 2"), ...)
#let ficha(..pares) = {
  let rows = pares.pos()
  let n = rows.len()
  block(
    width: 100%,
    stroke: (paint: c-rule, thickness: 0.5pt),
    radius: 4pt, clip: true, spacing: 0.9em,
  )[
    #for (i, par) in rows.enumerate() {
      grid(
        columns: (4.2cm, 1fr),
        block(
          fill: if calc.odd(i) { c-stripe } else { white },
          inset: (x: 11pt, y: 7pt), width: 100%,
        )[#text(size: 9pt, weight: "medium", fill: c-navy)[#par.at(0)]],
        block(
          fill: white, inset: (x: 11pt, y: 7pt), width: 100%,
        )[#text(size: 9pt)[#par.at(1)]],
      )
      if i < n - 1 {
        line(length: 100%, stroke: (paint: c-rule, thickness: 0.4pt))
      }
    }
  ]
}

// ── Tabela com cabeçalho navy ───────────────────────────────────────────
// #tabela((1fr, 2cm), ("Col 1", "Col 2"), ("a", "b"), ...)
#let tabela(colunas, header, ..linhas) = block(
  width: 100%, spacing: 0.9em, radius: 4pt, clip: true,
  stroke: (paint: c-rule, thickness: 0.5pt),
)[
  #block(fill: c-navy, width: 100%, inset: (x: 10pt, y: 7pt))[
    #grid(columns: colunas, column-gutter: 8pt,
      ..header.map(h => text(fill: white, size: 9pt, weight: "semibold")[#h]))
  ]
  #for (i, linha) in linhas.pos().enumerate() {
    block(
      fill: if calc.odd(i) { c-stripe } else { white },
      width: 100%, inset: (x: 10pt, y: 6pt),
      stroke: (bottom: (paint: c-rule, thickness: 0.4pt)),
    )[
      #grid(columns: colunas, column-gutter: 8pt,
        ..linha.map(c => text(size: 9.5pt)[#c]))
    ]
  }
]

// ── Card de falha numerada ──────────────────────────────────────────────
// #falha-card("F1", "Título")[Corpo do card]
#let falha-card(num, titulo, corpo) = block(
  width: 100%, spacing: 0.4em,
  stroke: (paint: c-rule, thickness: 0.5pt), radius: 3pt, clip: true,
)[
  #grid(
    columns: (1.8cm, 1fr),
    block(fill: c-red, inset: (x: 6pt, y: 12pt), width: 100%)[
      #align(center)[#text(fill: white, weight: "bold", size: 10pt)[#num]]
    ],
    block(inset: (x: 13pt, y: 10pt))[
      #text(weight: "semibold", fill: c-navy, size: 10pt)[#titulo]
      #v(3pt)
      #set text(size: 10pt)
      #corpo
    ],
  )
]

// ── Checkmark verde ─────────────────────────────────────────────────────
// #check[Texto do item aprovado]
#let check(corpo) = grid(
  columns: (1.4em, 1fr), column-gutter: 5pt, align: (top, top),
  text(fill: c-green, weight: "bold")[✓],
  block()[#set text(size: 10.5pt); #corpo],
)
