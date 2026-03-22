# Phase 0 Audit

## gov_modules_sectoral

- `gov_empenho`, `gov_liquidacao`, `gov_pagamento`, `gov_public_accounting`: contextualizacao de contabilidade publica, com regras MCASP e fluxo orcamentario setorial.
- `gov_compras`, `gov_processos`, `gov_knowledge_bridge`: processos administrativos e compras governamentais, sem utilidade como base de localizacao fiscal privada.
- `gov_ai_ml`: camada opcional de IA e ingestao documental, fora do escopo fiscal neutro.

## gov_modules_donor

- `custom_addons/public_sector/gov_account_fiscal_year/models/account_fiscal_year.py`: conceito neutro de exercicio fiscal por empresa e regra de nao sobreposicao.
- `custom_addons/public_sector/gov_account_lock_date_update/models/account_lock_date_log.py`: trilha de auditoria para alteracao de lock date.
- `custom_addons/public_sector/gov_conciliacao/parsers/gov_ofx_parser.py`: parser OFX potencialmente portavel para um futuro `br_bank_import`.
- `custom_addons/public_sector/gov_conciliacao/parsers/gov_cnab240_retorno.py`: parser CNAB240 de retorno com potencial de extracao futura.

## om_account_modules

- `om_account_accountant`: stack de compatibilidade e UX contabil, sem regra fiscal BR proprietaria.
- `om_fiscal_year`: donor alternativo para fiscal year/lock date, mas com acoplamento funcional inferior ao stack `gov_account_*`.
- `om_account_asset`, `om_account_daily_reports`, `accounting_pdf_reports`: candidatos a portas opcionais como `br_assets` e `br_reports`, nunca dependencia estrutural.
- `om_account_budget`, `om_account_followup`, `om_recurring_payments`: funcionalidades acessorias, nao base para `br_base`, `br_account` ou `br_tax_engine`.

## recommended_optional_ports

- `br_reports`: relatorios financeiros e fiscais desacoplados dos donors Option B.
- `br_bank_import`: importadores CNAB240/OFX reimplementados sem dependencias publicas.
- `br_assets`: camada opcional de ativos com naming e fluxos aderentes ao stack `br_*`.
- `br_followup`: cobranca/follow-up desacoplado de `om_account_followup`.
