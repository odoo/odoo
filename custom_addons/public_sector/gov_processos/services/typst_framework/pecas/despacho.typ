#let despacho(dados) = peca(
  "DESPACHO",
  [
    = 1. Relatorio
    Documento vinculado ao processo nº #dados.processo.

    #if dados.referencia != "" [
      Referencia interna: #dados.referencia.
    ]

    = 2. Encaminhamento
    #if dados.encaminhamento != "" [
      #dados.encaminhamento
    ] else [
      Encaminhem-se os autos para analise e deliberacao da autoridade competente.
    ]

    #assinatura(dados.assinante_nome, dados.assinante_cargo)
  ]
)
