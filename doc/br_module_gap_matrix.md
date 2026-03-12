# Matriz BR

Data base: 2026-03-12

Escopo desta matriz:
- `br_*` e `l10n_br*` como eixo brasileiro
- `gov_*` fora do papel de base arquitetural
- presenca no checkout nao significa stack resolvida: duplicidade tecnica, dependencia ausente ou modulo de outra major version entram como risco de nivelamento

## Premissas

- A familia `br_*` sera nossa camada propria.
- `l10n_br*` upstream e community entram como base reaproveitavel, nao como destino final.
- Modulos community podem nivelar gaps de stack, desde que a gente escolha uma linha canonica e elimine duplicidades.
- O dashboard so cresce em cima do BR depois da fundacao contabil/fiscal estar fechada.

## Legenda

| Status | Significado |
| --- | --- |
| `Local` | ja existe no repositorio e pode ser aproveitado diretamente |
| `Local+Risk` | existe, mas com dependencia ausente, versao incompativel ou outra restricao relevante |
| `Local+Conflict` | existe, mas ha mais de uma origem para o mesmo modulo tecnico ou stacks concorrentes |
| `Community` | nao esta no checkout atual, mas deve ser nivelado/importado |
| `Build` | precisa ser criado por nos |
| `Later` | nao bloqueia a fundacao inicial |

## Matriz Principal

| Camada | Modulo alvo | Papel | Base atual reaproveitavel | Estado hoje | Acao recomendada | Prioridade |
| --- | --- | --- | --- | --- | --- | --- |
| Fundacao | `br_base` | CNPJ/CPF, CEP, endereco BR, certificado A1/A3, assinatura XML | `l10n_br`, `l10n_br_base (14.0, risco)`, `base_address_extended` | `Build` | criar modulo proprio e decidir uma unica base de endereco/fiscal BR | P0 |
| Fundacao | `br_account` | extensao contabil BR, campos fiscais, estrutura NBC TG | `l10n_br`, `custom_addons/accountant`, `om_account_accountant`, `base_accounting_kit`, `dynamic_accounts_report` | `Build` | escolher a stack contabil canonica antes de codar a camada BR | P0 |
| Fundacao | `br_tax_engine` | motor dual legado + CBS/IBS/IS | `l10n_br_fiscal (14.0, risco)` | `Build` | criar nucleo proprio e reaproveitar apenas taxonomia/regra onde couber | P0 |
| Fiscal eletronico | `br_nfe` | NF-e, NFS-e, XML, assinatura, SEFAZ, DANFE | `account_edi`, `l10n_latam_invoice_document`, `l10n_br_fiscal (14.0, risco)`, `report_xlsx` | `Build` | criar provider proprio e decidir o quanto do fiscal community entra como apoio | P1 |
| Regime | `br_simples` | Simples Nacional, DAS, PGDAS-D, fator R | `l10n_br_fiscal` so como referencia conceitual | `Build` | criar logo apos tax engine | P1 |
| Regime | `br_presumido` | Lucro Presumido | `br_tax_engine` | `Build` | criar apos Simples/NF-e | P2 |
| Regime | `br_real` | Lucro Real, LALUR/LACS | `br_tax_engine` | `Build` | criar por ultimo entre regimes | P3 |
| Obrigacoes | `br_sped` | ECD, ECF, EFD ICMS/IPI, EFD Contribuicoes | `report_xlsx` | `Build` | criar apos fundacao fiscal e stack contabil definida | P2 |
| RH Fiscal | `br_esocial` | eSocial + EFD-Reinf | `hr`, `hr_work_entry`, `hr_holidays`, `hr_attendance`, `hr_expense`, `hr_payroll_community` | `Build` | depende de payroll canonico e da camada BR de folha | P2 |
| RH Fiscal | `br_hr_payroll` | folha BR, INSS, IRRF, FGTS, ferias, 13o, rescisao | `hr_payroll_community`, `hr_payroll_account_community` | `Build` + `Local+Conflict` | canonicalizar a stack de folha community e depois construir a camada BR | P1 |

## Localizacao BR Ja Presente

| Modulo | Papel | Estado |
| --- | --- | --- |
| `addons/l10n_br` | base fiscal/contabil BR upstream do Odoo 19 | `Local` |
| `addons/l10n_br_sales` | ponte BR para vendas | `Local` |
| `addons/l10n_br_website_sale` | ponte BR para website sale | `Local` |
| `custom_addons/accountant` | wrapper de compatibilidade do stack contabil atual | `Local` |
| `custom_addons/l10n_br_fiscal-14.0.28.1.0/l10n_br_base` | base OCA BR mais rica em endereco/cadastro | `Local+Risk` |
| `custom_addons/l10n_br_fiscal-14.0.28.1.0/l10n_br_fiscal` | modulo fiscal OCA BR | `Local+Risk` |

## Stack Community Ja Adicionada

| Modulo | Papel | Estado |
| --- | --- | --- |
| `custom_addons/base_accounting_kit-19.0.2.2.0/base_account_budget` | budget community | `Local+Conflict` |
| `custom_addons/base_accounting_kit-19.0.2.2.0/base_accounting_kit` | accounting/reporting community | `Local+Conflict` |
| `custom_addons/dynamic_accounts_report-19.0.1.0.0/dynamic_accounts_report` | relatorios dinamicos community | `Local` |
| `custom_addons/dynamic_accounts_report-19.0.1.0.0/base_account_budget` | copia de `base_account_budget` dentro de outro pacote | `Local+Conflict` |
| `custom_addons/dynamic_accounts_report-19.0.1.0.0/base_accounting_kit` | copia de `base_accounting_kit` dentro de outro pacote | `Local+Conflict` |
| `custom_addons/hr_payroll_community-19.0.1.0.1/hr_payroll_community` | payroll community standalone | `Local+Conflict` |
| `custom_addons/ohrms_core-19.0.1.0.0/hr_payroll_community` | segunda origem do mesmo modulo tecnico | `Local+Conflict` |
| `custom_addons/ohrms_core-19.0.1.0.0/hr_payroll_account_community` | ponte contabil para payroll community | `Local` |
| `custom_addons/report_xlsx-19.0.1.0.2/report_xlsx` | base OCA para exportacao XLSX | `Local` |

## Gaps de Stack que Precisam Ser Nivelados

| Gap | Por que importa | Estado hoje | Acao |
| --- | --- | --- | --- |
| Stack contabil/reporting canonica | hoje coexistem `om_account_accountant`, `base_accounting_kit` e `dynamic_accounts_report` | `Local+Conflict` | escolher uma linha oficial e remover/modularizar o excedente |
| Stack de payroll canonica | `hr_payroll_community` existe em duas origens | `Local+Conflict` | escolher uma fonte oficial antes de instalar/atualizar em massa |
| `base_address_city` | dependencia direta de `l10n_br_base` | ausente | trazer ou abandonar a trilha OCA 14 |
| `documents` | util para ciclo fiscal documental e anexos operacionais | ausente | nivelar depois da fundacao P0 |
| `sign` | util para fluxos de assinatura interna | ausente | nivelar depois; nao bloqueia P0 |
| `l10n_br_reports` | relatorios BR complementares | ausente | avaliar apos definir stack contabil |
| `l10n_br_edi` | ponte EDI BR indicada por parte do ecossistema | ausente | decidir se entra como base ou se `br_nfe` cobre tudo |
| `l10n_br_avatax` | calculo fiscal terceirizado | ausente | opcional, nao e base do MVP |
| `l10n_br_avatax_sale` | extensao comercial Avatax BR | ausente | opcional |
| Localizacao BR para compras/estoque/POS | fecha o fluxo operacional BR ponta a ponta | ausente | avaliar como familia `br_*` ou community complementar |
| Bancario BR (`boleto`, `CNAB`, `Pix`) | necessario para cobranca, remessa, conciliacao e pagamento | ausente | mapear como trilha propria apos `br_account` |

## Riscos de Nivelamento Hoje

| Risco | Evidencia | Impacto |
| --- | --- | --- |
| Duplicidade tecnica em contabilidade | `base_account_budget` e `base_accounting_kit` aparecem em dois pacotes diferentes | comportamento imprevisivel no addons path, upgrade e debug |
| Duplicidade tecnica em payroll | `hr_payroll_community` aparece em duas pastas diferentes | risco de instalar uma origem e atualizar outra sem perceber |
| Linha fiscal BR em major version diferente | `l10n_br_base` e `l10n_br_fiscal` estao em `14.0` | nao contam como gap resolvido em Odoo 19 sem prova de compatibilidade |
| Dependencia faltando na linha OCA BR | `l10n_br_base` depende de `base_address_city`, que nao esta no checkout | a trilha OCA BR nao instala limpa no estado atual |
| Stack contabil concorrente | `accountant` aponta para `om_account_accountant`, enquanto outra linha traz `base_accounting_kit` | precisamos escolher o norte contabil antes de construir `br_account` |

## Cobertura Funcional por Dominio

| Dominio | O que temos hoje | O que falta para o plano |
| --- | --- | --- |
| Contabilidade | `account`, `l10n_br`, `accountant`, `om_account_accountant`, `base_accounting_kit`, `dynamic_accounts_report`, `report_xlsx` | stack contabil canonica, `br_account`, `br_tax_engine`, regimes e consolidacao BR |
| Fiscal eletronico | `account_edi`, `l10n_latam_invoice_document`, `l10n_br_fiscal` com risco | `br_nfe`, provider NFS-e, contingencia, assinatura e integracao SEFAZ em Odoo 19 |
| Comercial BR | `sale_management`, `website_sale`, `l10n_br_sales`, `l10n_br_website_sale` | fiscal BR de ponta a ponta em venda |
| Compras/estoque/POS BR | `purchase`, `stock`, `point_of_sale` | camadas BR especificas ainda inexistentes |
| RH base | `hr_attendance`, `hr_holidays`, `hr_expense`, `hr_work_entry`, `hr_payroll_community`, `hr_payroll_account_community` | folha BR, eventos fiscais BR, eSocial, Reinf |
| Obrigacoes acessorias | `report_xlsx` como infraestrutura | `br_sped`, ECF, ECD, EFDs |
| Bancario BR | nada identificado | boleto, CNAB, Pix |

## Ordem Recomendada de Execucao

| Etapa | Entrega | Dependencia |
| --- | --- | --- |
| 1 | eliminar duplicidade de modulos tecnicos e escolher stack contabil canonica | nenhuma |
| 2 | escolher a origem oficial de `hr_payroll_community` | etapa 1 |
| 3 | decidir se a trilha OCA 14 sera aproveitada ou descartada em Odoo 19 | etapas 1 e 2 |
| 4 | se a trilha OCA ficar, trazer `base_address_city` e provar install em Odoo 19; se nao ficar, consolidar em cima de `l10n_br` nativo | etapa 3 |
| 5 | criar `br_base` | etapa 4 |
| 6 | criar `br_account` | `br_base` + stack contabil definida |
| 7 | criar `br_tax_engine` | `br_account` |
| 8 | decidir trilha fiscal: `l10n_br_edi` vs `br_nfe` puro | `br_base`, `br_account` |
| 9 | criar `br_simples` | `br_tax_engine` |
| 10 | criar `br_hr_payroll` | payroll canonico nivelado |
| 11 | criar `br_esocial` | `br_hr_payroll`, HR base |
| 12 | criar `br_sped` | `br_account`, `br_nfe` |
| 13 | expandir `br_presumido` e `br_real` | tax engine maduro |

## Decisoes Arquiteturais Ja Fixadas

- `gov_*` nao e base conceitual do BR.
- `br_*` e familia propria e independente.
- `l10n_br*` entra como base tecnica reaproveitavel, sem virar o norte do produto.
- wrappers/community entram para nivelar stack, nao para redefinir a arquitetura.
- dashboard BR so entra depois que `br_base`, `br_account` e `br_tax_engine` estiverem solidos.

## Backlog Imediato

| Ordem | Item | Tipo |
| --- | --- | --- |
| 1 | decidir a stack contabil oficial entre `om_account_accountant` e `base_accounting_kit`/`dynamic_accounts_report` | decisao de stack |
| 2 | decidir a origem oficial de `hr_payroll_community` | decisao de stack |
| 3 | validar ou descartar a trilha `l10n_br_base` + `l10n_br_fiscal` em Odoo 19 | arquitetura |
| 4 | scaffold de `custom_addons/br_base` | implementacao |
| 5 | scaffold de `custom_addons/br_account` | implementacao |
| 6 | scaffold de `custom_addons/br_tax_engine` | implementacao |
| 7 | ADR curta decidindo `l10n_br_edi` vs `br_nfe` | arquitetura |
