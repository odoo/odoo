#let tr(dados) = peca(
  "TERMO DE REFERENCIA",
  [
    = 1. Objeto
    #dados.objeto

    = 2. Fundamentacao
    #dados.fundamento

    = 3. Requisitos da Contratacao
    #lista_itens(dados.pontos_chave)

    = 4. Observacoes Finais
    #dados.observacoes_finais
  ]
)
