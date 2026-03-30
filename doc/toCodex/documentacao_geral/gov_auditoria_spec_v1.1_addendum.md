# gov_auditoria Spec v1.1 Addendum

Data: 2026-03-26
Base: `doc/toCodex/gov_auditoria_spec_v1.1.pdf`
Objetivo: registrar ajustes finais antes da implementação, já que a fonte editável do PDF não está versionada no repositório.

## Ajustes obrigatórios

### 1. Uniformização do modelo de exercício fiscal

O texto da v1.1 ainda alterna entre `gov.fiscal.year`, `gov.account.fiscal.year` e a referência ao arquivo real.

Regra definitiva para implementação:

- O modelo real a ser usado em Python, XML, segurança, testes e comentários é `account.fiscal.year`.
- A dependência permanece no módulo `gov_account_fiscal_year`.
- Não usar `gov.fiscal.year` nem `gov.account.fiscal.year` em código novo.

Substituições semânticas a considerar no spec:

- Onde constar `Many2one (gov.fiscal.year)`, ler como `Many2one (account.fiscal.year)`.
- Onde constar “fechamento no gov.fiscal.year”, ler como “fechamento suportado por `account.fiscal.year` em conjunto com lock dates contábeis”.

### 2. Reescrita do requisito de fechamento do exercício

O item da Onda 1 que diz que `gov_account_fiscal_year` deve impedir lançamentos após lock date simplifica demais a arquitetura atual.

Regra definitiva para implementação:

- O fechamento do exercício será tratado como capacidade conjunta dos módulos:
  - `gov_account_fiscal_year`
  - `gov_account_lock_date_update`
  - `gov_account_journal_lock_date`
  - `gov_public_accounting`
- O critério operacional do `gov_auditoria` será:
  - exercício selecionado existente em `account.fiscal.year`
  - lock date fiscal e, quando aplicável, lock date por diário coerentes com a data final do exercício
  - validações contábeis do bundle público ativas para a empresa

Texto recomendado para substituir o item da Onda 1:

> Verificar consistência do fechamento do exercício: integrar `account.fiscal.year`, lock dates fiscais e lock dates por diário, garantindo que o exercício usado pelo ciclo esteja formalmente encerrado para fins de geração anual.

### 3. Escopo de `gov.auditoria.orgao`

O spec v1.1 deixa ambíguo se `gov.auditoria.orgao` é cadastro global ou segregado por empresa.

Decisão arquitetural:

- `gov.auditoria.orgao` será cadastro global de parametrização.
- O modelo não terá `company_id` obrigatório.
- O isolamento multi-UG não se aplica ao órgão em si, mas aos ciclos e demais registros operacionais.
- Apenas `group_auditoria_admin` pode criar/editar/desativar órgãos.
- `gov.auditoria.ciclo` referencia um órgão global e carrega o `company_id` da UG responsável.

Justificativa:

- o mesmo TCE/TCM/TCU/CGE atende múltiplas UGs
- duplicar órgão por empresa introduziria redundância e risco de divergência regulatória
- o controle de acesso ao cadastro parametrizador deve ser por grupo, não por empresa

## Efeito prático no backlog

Esses ajustes alteram diretamente:

- modelagem de `gov.auditoria.ciclo`
- regras `ir.rule`
- validações de fechamento na Onda 1
- seeds e telas de configuração de `gov.auditoria.orgao`
- testes de integração entre exercício fiscal e geração de anexos

## Observação

Se a fonte LaTeX/Typst da especificação for adicionada ao repositório depois, este adendo deve ser incorporado ao documento principal e a versão resultante publicada como v1.2.
