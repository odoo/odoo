#let etp(dados) = peca(
  "ESTUDO TECNICO PRELIMINAR",
  [
    = 1. Descricao da Necessidade
    #dados.necessidade

    = 2. Objeto da Solucao
    #dados.objeto

    = 3. Estimativa de Custo
    #tabela_custos(dados.custos)
  ]
)
