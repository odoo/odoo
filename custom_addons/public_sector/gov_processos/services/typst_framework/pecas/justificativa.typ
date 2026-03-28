#let justificativa(dados) = peca(
  "JUSTIFICATIVA DE CONTRATACAO",
  [
    = 1. Identificacao
    #campo("Unidade Requisitante", dados.secretaria)
    #campo("Responsavel", dados.responsavel)
    #campo("Natureza de Despesa", dados.natureza)
    #campo("Fonte", dados.fonte)

    = 2. Do Objeto
    #dados.objeto

    = 3. Da Justificativa
    #dados.necessidade

    #if dados.fundamento != "" [
      = 4. Fundamento Legal
      #dados.fundamento
    ]
  ]
)
