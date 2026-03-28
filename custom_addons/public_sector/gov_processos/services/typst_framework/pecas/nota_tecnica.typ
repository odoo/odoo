#let nota_tecnica(dados) = peca(
  "NOTA TECNICA",
  [
    = 1. Assunto
    #if dados.assunto != "" [#dados.assunto] else [#dados.objeto]

    = 2. Analise
    #if dados.fatos_relevantes != "" [#dados.fatos_relevantes] else [#dados.necessidade]

    = 3. Pontos-Chave
    #lista_itens(dados.pontos_chave)

    = 4. Conclusao
    #if dados.encaminhamento != "" [#dados.encaminhamento] else [#dados.observacoes_finais]

    #if dados.assinante_nome != "" [
      #assinatura(dados.assinante_nome, dados.assinante_cargo)
    ]
  ]
)
