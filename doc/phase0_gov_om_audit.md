# Fase 0: Auditoria de Fundacao Neutra vs Contextualizacao GOV

Data: 2026-03-12

Objetivo:
- fechar o corte arquitetural antes de iniciar `br_base`
- confirmar o que pode servir de fundacao neutra BR/USA
- separar com rigor o que e apenas contextualizacao GOV
- identificar portas opcionais para recursos doadores

## Regra de Norte

- `accountant` + `om_account_accountant-*` e a fundacao contabil neutra escolhida.
- `gov_*` nao e fundacao do Kodoo; e uma camada de contextualizacao para um segmento.
- `Option B` (`base_accounting_kit` / `dynamic_accounts_report`) entra apenas por portas `br_*` opcionais, nunca como base.

## 1. Auditoria `gov_*`

### 1.1 Modulos que nao devem orientar `br_*`

`gov_base`
- Evidencia: `custom_addons/public_sector/gov_base/__manifest__.py`
- Problema de fundacao: adiciona semantica publica em `res.company` e `account.account`.
- Evidencia tecnica:
  - `custom_addons/public_sector/gov_base/models/res_company.py`
  - `custom_addons/public_sector/gov_base/models/account_account.py`
- Acoplamentos encontrados:
  - `cnpj_ug`, `codigo_ug`, `codigo_siafi`, `exercicio_fiscal`
  - `natureza_pcasp`, `codigo_pcasp`
  - sincronizacao de regras para `gov.processo`
- Conclusao: e base GOV, nao base BR neutra.

`gov_processos`
- Evidencia: `custom_addons/public_sector/gov_processos/__manifest__.py`
- Evidencia tecnica:
  - `custom_addons/public_sector/gov_processos/models/gov_processo.py`
  - `custom_addons/public_sector/gov_processos/models/gov_dashboard.py`
- Motivo: carrega o dominio inteiro de processo administrativo, fases, tramites, documentos, AI e painel executivo.

`gov_compras`
- Evidencia: `custom_addons/public_sector/gov_compras/__manifest__.py`
- Evidencia tecnica:
  - `custom_addons/public_sector/gov_compras/models/gov_compras_catalog_item.py`
  - `custom_addons/public_sector/gov_compras/models/gov_compras_item_track.py`
  - `custom_addons/public_sector/gov_compras/models/gov_compras_previsao.py`
- Motivo: semantica de compras publicas, banco de precos, previsao e trilha licitatoria.

`gov_empenho`, `gov_liquidacao`, `gov_pagamento`
- Evidencia:
  - `custom_addons/public_sector/gov_empenho/__manifest__.py`
  - `custom_addons/public_sector/gov_liquidacao/__manifest__.py`
  - `custom_addons/public_sector/gov_pagamento/__manifest__.py`
- Evidencia tecnica:
  - `custom_addons/public_sector/gov_empenho/models/gov_empenho.py`
  - `custom_addons/public_sector/gov_liquidacao/models/gov_liquidacao.py`
  - `custom_addons/public_sector/gov_pagamento/models/gov_pagamento.py`
- Motivo: materializam o ciclo publico `NE -> NL -> PD/OP`, com vocabulario e regras proprias do setor.

`gov_conciliacao`
- Evidencia: `custom_addons/public_sector/gov_conciliacao/__manifest__.py`
- Evidencia tecnica: `custom_addons/public_sector/gov_conciliacao/models/gov_conciliacao_importacao.py`
- Motivo: embora tenha parsers uteis, o modulo esta acoplado ao fluxo GOV inteiro.

`gov_ai_ml`, `gov_knowledge_bridge`, `gov_suite`
- Evidencia:
  - `custom_addons/public_sector/gov_ai_ml/__manifest__.py`
  - `custom_addons/public_sector/gov_knowledge_bridge/__manifest__.py`
  - `custom_addons/public_sector/gov_suite/__manifest__.py`
- Motivo: sao camadas de composicao da suite GOV e nao servem como base neutra.

### 1.2 Blocos GOV que valem como doadores conceituais

`gov_account_fiscal_year`
- Evidencia:
  - `custom_addons/public_sector/gov_account_fiscal_year/__manifest__.py`
  - `custom_addons/public_sector/gov_account_fiscal_year/models/account_fiscal_year.py`
  - `custom_addons/public_sector/gov_account_fiscal_year/models/res_company.py`
- Valor: modelo de exercicio fiscal por empresa, busca por data e validacao de sobreposicao.
- Observacao: hoje depende de `gov_base`, mas o conceito em si e neutro.

`gov_account_journal_lock_date`
- Evidencia:
  - `custom_addons/public_sector/gov_account_journal_lock_date/__manifest__.py`
  - `custom_addons/public_sector/gov_account_journal_lock_date/models/account_journal.py`
  - `custom_addons/public_sector/gov_account_journal_lock_date/models/account_move.py`
- Valor: lock date por diario com validacao em `account.move`.
- Observacao: candidato a porta neutra de fechamento controlado.

`gov_account_lock_date_update`
- Evidencia:
  - `custom_addons/public_sector/gov_account_lock_date_update/__manifest__.py`
  - `custom_addons/public_sector/gov_account_lock_date_update/models/account_lock_date_log.py`
  - `custom_addons/public_sector/gov_account_lock_date_update/models/res_company.py`
- Valor: workflow de atualizacao de lock date com trilha auditavel.
- Observacao: bom material para governanca contabil, sem precisar carregar a suite GOV.

`gov_account_move_template`
- Evidencia:
  - `custom_addons/public_sector/gov_account_move_template/__manifest__.py`
  - `custom_addons/public_sector/gov_account_move_template/models/account_move_template.py`
  - `custom_addons/public_sector/gov_account_move_template/models/account_move_template_line.py`
  - `custom_addons/public_sector/gov_account_move_template/wizard/account_move_template_run_wizard.py`
- Valor: templates de lancamentos recorrentes para fechamento.
- Observacao: o nucleo e limpo, mas o empacotamento atual ainda puxa `gov_base` e `mail`.

`gov_account_spread_cost_revenue`
- Evidencia:
  - `custom_addons/public_sector/gov_account_spread_cost_revenue/__manifest__.py`
  - `custom_addons/public_sector/gov_account_spread_cost_revenue/models/account_spread.py`
  - `custom_addons/public_sector/gov_account_spread_cost_revenue/models/account_spread_line.py`
  - `custom_addons/public_sector/gov_account_spread_cost_revenue/models/account_move.py`
  - `custom_addons/public_sector/gov_account_spread_cost_revenue/models/account_move_line.py`
- Valor: apropriacao diferida de custo/receita por periodos.
- Observacao: o dominio e neutro, mas hoje esta ligado ao `gov_account_fiscal_year`.

### 1.3 Doadores bancarios vindos de GOV

Parsers e servicos que valem extracao futura:
- `custom_addons/public_sector/gov_conciliacao/parsers/gov_ofx_parser.py`
- `custom_addons/public_sector/gov_conciliacao/parsers/gov_cnab240_retorno.py`
- `custom_addons/public_sector/gov_pagamento/models/gov_cnab_service.py`

Direcao recomendada:
- levar isso para portas neutras futuras como `br_bank_import`, sem depender de `gov_conciliacao` ou `gov_pagamento`.

## 2. Auditoria `accountant` + `om_account_accountant-*`

### 2.1 Estrutura e dependencias reais

`accountant`
- Evidencia: `custom_addons/accountant/__manifest__.py`
- Dependencias: `account`, `om_account_accountant`
- Papel: wrapper de compatibilidade com nome tecnico neutro.

`om_account_accountant`
- Evidencia:
  - `custom_addons/om_account_accountant-19.0.1.0.3/om_account_accountant/__manifest__.py`
  - `custom_addons/om_account_accountant-19.0.1.0.3/om_account_accountant/models/account_move.py`
  - `custom_addons/om_account_accountant-19.0.1.0.3/om_account_accountant/models/settings.py`
- Papel: meta-modulo agregador.
- Leitura tecnica: os overrides encontrados sao pequenos e cirurgicos.

`om_fiscal_year`
- Evidencia:
  - `custom_addons/om_account_accountant-19.0.1.0.3/om_fiscal_year/__manifest__.py`
  - `custom_addons/om_account_accountant-19.0.1.0.3/om_fiscal_year/models/account_fiscal_year.py`
  - `custom_addons/om_account_accountant-19.0.1.0.3/om_fiscal_year/models/res_company.py`
  - `custom_addons/om_account_accountant-19.0.1.0.3/om_fiscal_year/wizard/change_lock_date.py`
- Dependencia declarada: `account`
- Valor: exercicio fiscal, lock dates e validacoes de fechamento.
- Leitura: e o melhor doador-base dentro da linha A.

`accounting_pdf_reports`
- Evidencia:
  - `custom_addons/om_account_accountant-19.0.1.0.3/accounting_pdf_reports/__manifest__.py`
  - `custom_addons/om_account_accountant-19.0.1.0.3/accounting_pdf_reports/models/account_financial_report.py`
  - `custom_addons/om_account_accountant-19.0.1.0.3/accounting_pdf_reports/wizard/account_report.py`
- Dependencia declarada: `account`
- Valor: engine de relatorios PDF classicos.
- Leitura: util, mas nao fundacao de `br_account`.

`om_account_asset`
- Evidencia:
  - `custom_addons/om_account_accountant-19.0.1.0.3/om_account_asset/__manifest__.py`
  - `custom_addons/om_account_accountant-19.0.1.0.3/om_account_asset/models/account_asset.py`
  - `custom_addons/om_account_accountant-19.0.1.0.3/om_account_asset/models/account_move.py`
  - `custom_addons/om_account_accountant-19.0.1.0.3/om_account_asset/models/account.py`
- Dependencia declarada: `account`
- Valor: ativos e deferimento via fatura.
- Leitura: modulo valioso, mas interfere no fluxo de `account.move` e deve ficar opcional.

`om_account_budget`
- Evidencia:
  - `custom_addons/om_account_accountant-19.0.1.0.3/om_account_budget/__manifest__.py`
  - `custom_addons/om_account_accountant-19.0.1.0.3/om_account_budget/models/account_budget.py`
  - `custom_addons/om_account_accountant-19.0.1.0.3/om_account_budget/models/account_analytic_account.py`
- Dependencia declarada: `account`
- Valor: budget + agregacoes.
- Leitura: entra em analitico, `read_group`, SQL manual e merece modulo opcional proprio.

`om_account_followup`
- Evidencia:
  - `custom_addons/om_account_accountant-19.0.1.0.3/om_account_followup/__manifest__.py`
  - `custom_addons/om_account_accountant-19.0.1.0.3/om_account_followup/models/followup.py`
  - `custom_addons/om_account_accountant-19.0.1.0.3/om_account_followup/models/partner.py`
  - `custom_addons/om_account_accountant-19.0.1.0.3/om_account_followup/models/account_move.py`
- Dependencias declaradas: `account`, `mail`
- Valor: cobranca e follow-up de recebiveis.
- Leitura: util, mas nao deve contaminar a fundacao.

`om_account_daily_reports`
- Evidencia:
  - `custom_addons/om_account_accountant-19.0.1.0.3/om_account_daily_reports/__manifest__.py`
  - `custom_addons/om_account_accountant-19.0.1.0.3/om_account_daily_reports/wizard/account_daybook_report.py`
  - `custom_addons/om_account_accountant-19.0.1.0.3/om_account_daily_reports/wizard/account_cashbook_report.py`
  - `custom_addons/om_account_accountant-19.0.1.0.3/om_account_daily_reports/wizard/account_bankbook_report.py`
- Dependencias declaradas: `account`, `accounting_pdf_reports`
- Valor: relatorios operacionais de caixa/banco/day book.
- Leitura: opcional de reporting operacional.

`om_recurring_payments`
- Evidencia:
  - `custom_addons/om_account_accountant-19.0.1.0.3/om_recurring_payments/__manifest__.py`
  - `custom_addons/om_account_accountant-19.0.1.0.3/om_recurring_payments/models/recurring_payment.py`
  - `custom_addons/om_account_accountant-19.0.1.0.3/om_recurring_payments/models/recurring_template.py`
- Dependencia declarada: `account`
- Valor: automacao de pagamentos recorrentes.
- Leitura: deve permanecer opcional.

### 2.2 O que isso prova sobre `br_account`

- `br_account` pode herdar `account.*` com cirurgia limpa sobre a fundacao A.
- O wrapper `accountant` e um bom ponto de entrada tecnico porque nao impoe dominio proprio.
- O meta-modulo central `om_account_accountant` quase nao agride o core contabil.
- Os recursos mais invasivos ja estao separados em addons especificos.

### 2.3 Portas opcionais recomendadas

Com base na auditoria, a linha correta e:
- `br_account`
  - sobre `account`, `accountant`, `l10n_br`
  - sem depender de `gov_*`
  - sem depender de `Option B`
- `br_reports`
  - doador principal: `accounting_pdf_reports`
  - doador secundario futuro: `dynamic_accounts_report`
- `br_bank_import`
  - doador futuro: componentes OFX/CNAB de `Option B` e parsers bancarios neutros extraidos de `gov_*`
- `br_assets`
  - se quisermos encapsular o comportamento de ativos sem fundir tudo em `br_account`
- `br_budget`
  - para manter orcamento fora do nucleo contabil
- `br_collections`
  - para follow-up e cobranca
- `br_recurring_payments`
  - para automacao financeira

## 3. Checkpoint de implementacao antes de `br_base`

Conclusoes fechadas:
- nao usar `gov_*` como referencia primaria de base
- nao usar `Option B` como segunda fundacao escondida
- iniciar `br_base` e `br_account` em cima da linha:
  - `account`
  - `accountant`
  - `l10n_br`
  - `l10n_br_sales`
  - `l10n_br_website_sale`

Backlog imediato da proxima fase:
1. manter a fundacao neutra documentada e travada
2. desenhar o esqueleto de `br_base`
3. desenhar o esqueleto de `br_account`
4. separar backlog das portas opcionais:
   - `br_reports`
   - `br_bank_import`
   - `br_assets`
   - `br_budget`
   - `br_collections`
   - `br_recurring_payments`
