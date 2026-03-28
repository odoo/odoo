#let dfd(dados) = peca(
  "DOCUMENTO DE FORMALIZACAO DE DEMANDA",
  [
    = 1. Identificacao
    #campo("Unidade Requisitante", dados.secretaria)
    #campo("Responsavel", dados.responsavel)
    #campo("Referencia", dados.referencia)

    = 2. Objeto
    #dados.objeto

    = 3. Justificativa
    #dados.necessidade
  ]
)
