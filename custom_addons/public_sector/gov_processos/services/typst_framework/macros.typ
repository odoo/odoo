#let contador_peca = counter("peca")

#let processo_admin(dados, pecas) = [
  #capa(dados)
  #outline(title: [Sumario])
  #pagebreak()
  #for p in pecas [
    #p
  ]
]

#let capa(d) = [
  #align(center)[
    #text(16pt, weight: "bold")[#d.municipio]
    #v(6mm)
    #if d.secretaria != "" [#d.secretaria]
    #if d.fundo != "" [#linebreak() #d.fundo]
    #v(20mm)
    #text(14pt, weight: "bold")[PROCESSO ADMINISTRATIVO]
    #v(5mm)
    Nº #d.processo
    #v(10mm)
    #text(14pt, weight: "bold")[#d.modalidade]
    #if d.subtitulo != "" [
      #v(4mm)
      #d.subtitulo
    ]
    #if d.fundamento != "" [
      #v(10mm)
      #text(weight: "bold")[Fundamento Legal]
      #linebreak()
      #d.fundamento
    ]
    #v(14mm)
    #text(weight: "bold")[OBJETO]
    #v(3mm)
    #d.objeto
    #if d.valor != "" [
      #v(10mm)
      #text(weight: "bold")[VALOR GLOBAL]
      #linebreak()
      #d.valor
    ]
    #v(15mm)
    #d.local
    #if d.data != "" [, #d.data]
  ]
  #pagebreak()
]

#let peca(titulo, corpo) = [
  #let numero = contador_peca.step().first()
  = PECA #numero - #titulo
  #corpo
  #pagebreak()
]

#let campo(nome, valor) = [
  #if valor != "" [
    #text(weight: "bold")[#nome:] #valor
    #linebreak()
  ]
]

#let assinatura(nome, cargo) = [
  #v(25mm)
  #align(center)[
    #line(length: 7cm, stroke: 0.5pt)
    #linebreak()
    #nome
    #if cargo != "" [#linebreak() #cargo]
  ]
]

#let tabela_custos(itens) = [
  #if itens.len() == 0 [
    Nenhum custo informado.
  ] else [
    #table(
      columns: (1fr, 4fr, 1.5fr),
      inset: 6pt,
      stroke: 0.5pt,
      [Grupo], [Descricao], [Valor],
      ..itens.map(item => (
        [#item.grupo],
        [#item.descricao],
        [#item.valor],
      )),
    )
  ]
]

#let lista_itens(texto) = [
  #if texto == "" [
    Nenhum item informado.
  ] else [
    #for item in texto.split("\n").filter(item => item.trim() != "") [
      - #item
    ]
  ]
]
