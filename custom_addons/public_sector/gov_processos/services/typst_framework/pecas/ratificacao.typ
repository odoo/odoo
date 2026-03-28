#let ratificacao(dados) = peca(
  "RATIFICACAO",
  [
    Reconhece-se a regularidade da instrucao apresentada no processo nº #dados.processo.

    #if dados.valor != "" [
      O valor global estimado do objeto e de #dados.valor.
    ]

    #if dados.fundamento != "" [
      A medida observa o seguinte fundamento: #dados.fundamento.
    ]

    #v(12mm)
    #dados.local
    #if dados.data != "" [, #dados.data]

    #assinatura(dados.assinante_nome, dados.assinante_cargo)
  ]
)
