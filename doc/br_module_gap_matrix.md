# Matriz BR

Data base: 2026-03-10

Escopo desta matriz:
- `br_*` e `l10n_br*` como eixo brasileiro
- `gov_*` fora do papel de base arquitetural
- quando um módulo não existe no checkout atual, mas pode ser nivelado pela comunidade, isso aparece como `Community`

## Premissas

- A família `br_*` será nossa camada própria.
- `l10n_br*` upstream é base reaproveitável, não destino final.
- Módulos de compatibilidade/community podem ser trazidos para nivelar gaps de stack.
- O dashboard só cresce em cima do BR depois da fundação contábil/fiscal estar fechada.

## Legenda

| Status | Significado |
| --- | --- |
| `Local` | já existe no repositório |
| `Community` | não está no checkout atual, mas deve ser nivelado/importado |
| `Build` | precisa ser criado por nós |
| `Later` | não bloqueia a fundação inicial |

## Matriz Principal

| Camada | Módulo alvo | Papel | Base atual reaproveitável | Estado hoje | Ação recomendada | Prioridade |
| --- | --- | --- | --- | --- | --- | --- |
| Fundação | `br_base` | CNPJ/CPF, CEP, endereço BR, certificado A1/A3, assinatura XML | `l10n_br`, `base_address_extended` | `Build` | criar módulo base próprio | P0 |
| Fundação | `br_account` | extensão contábil BR, campos fiscais, estrutura NBC TG | `l10n_br`, `custom_addons/accountant` | `Build` | criar sobre `l10n_br` + wrapper `accountant` | P0 |
| Fundação | `br_tax_engine` | motor dual legado + CBS/IBS/IS | nenhuma base equivalente local | `Build` | criar como núcleo temporal de regras | P0 |
| Fiscal eletrônico | `br_nfe` | NF-e, NFS-e, XML, assinatura, SEFAZ, DANFE | `account_edi`, `l10n_br`, `l10n_latam_invoice_document` | `Build` | criar módulo próprio com providers | P1 |
| Regime | `br_simples` | Simples Nacional, DAS, PGDAS-D, fator R | nenhuma base local pronta | `Build` | criar logo após tax engine | P1 |
| Regime | `br_presumido` | Lucro Presumido | `br_tax_engine` | `Build` | criar após Simples/NF-e | P2 |
| Regime | `br_real` | Lucro Real, LALUR/LACS | `br_tax_engine` | `Build` | criar por último entre regimes | P3 |
| Obrigações | `br_sped` | ECD, ECF, EFD ICMS/IPI, EFD Contribuições | nenhuma base local pronta | `Build` | criar após fundação fiscal | P2 |
| RH Fiscal | `br_esocial` | eSocial + EFD-Reinf | `hr`, `hr_work_entry`, `hr_holidays`, `hr_attendance`, `hr_expense` | `Build` | depende de base de folha | P2 |
| RH Fiscal | `br_hr_payroll` | folha BR, INSS, IRRF, FGTS, férias, 13º, rescisão | stack HR atual sem folha | `Build` + `Community` | nivelar payroll primeiro, depois construir BR | P1 |

## Localização BR Já Presente

| Módulo | Papel | Estado |
| --- | --- | --- |
| `addons/l10n_br` | base fiscal/contábil BR upstream | `Local` |
| `addons/l10n_br_sales` | ponte BR para vendas | `Local` |
| `addons/l10n_br_website_sale` | ponte BR para website sale | `Local` |
| `custom_addons/accountant` | wrapper de compatibilidade do stack contábil | `Local` |

## Gaps de Stack que Precisam Ser Nivelados

| Gap | Por que importa | Estado hoje | Ação |
| --- | --- | --- | --- |
| `payroll` / equivalente | bloqueia `br_hr_payroll` e parte de `br_esocial` | ausente | trazer da comunidade primeiro |
| `account_reports` / equivalente | importante para fechamento, DRE, BP, relatórios fiscais | ausente | nivelar antes de `br_sped` maduro |
| `documents` | útil para ciclo fiscal documental e anexos operacionais | ausente | nivelar, mas não bloqueia P0 |
| `sign` | útil para assinatura de fluxos, não para assinatura XML NF-e | ausente | nivelar depois, não bloqueia P0 |
| `l10n_br_reports` | relatórios BR citados pelo próprio `l10n_br` | ausente | trazer cedo |
| `l10n_br_edi` | ponte EDI BR indicada pelo upstream | ausente | decidir se entra como base ou se `br_nfe` substitui |
| `l10n_br_avatax` | cálculo fiscal terceirizado | ausente | opcional, não é base do MVP |
| `l10n_br_avatax_sale` | extensão comercial Avatax BR | ausente | opcional |

## Cobertura Funcional por Domínio

| Domínio | O que temos hoje | O que falta para o plano |
| --- | --- | --- |
| Contabilidade | `account`, `l10n_br`, `accountant` wrapper | `br_account`, `br_tax_engine`, relatórios BR e regimes |
| Fiscal eletrônico | `account_edi`, `l10n_latam_invoice_document` | `br_nfe`, provider NFS-e, contingência, SEFAZ |
| Comercial BR | `sale_management`, `website_sale`, `l10n_br_sales`, `l10n_br_website_sale` | fiscal BR de ponta a ponta em venda |
| Compras/estoque/POS BR | `purchase`, `stock`, `point_of_sale` | camadas BR específicas ainda inexistentes |
| RH base | `hr_attendance`, `hr_holidays`, `hr_expense`, `hr_work_entry` | payroll BR, eSocial, Reinf |
| Obrigações acessórias | nada dedicado | `br_sped`, ECF, ECD, EFDs |
| Bancário BR | nada identificado | boleto, CNAB, Pix |

## Ordem Recomendada de Execução

| Etapa | Entrega | Dependência |
| --- | --- | --- |
| 1 | nivelar `payroll` e `account_reports` community | nenhuma |
| 2 | criar `br_base` | stack atual |
| 3 | criar `br_account` | `br_base`, `l10n_br`, `accountant` |
| 4 | criar `br_tax_engine` | `br_account` |
| 5 | decidir trilha fiscal: `l10n_br_edi` vs `br_nfe` puro | `br_base`, `br_account` |
| 6 | criar `br_simples` | `br_tax_engine` |
| 7 | criar `br_hr_payroll` | payroll nivelado |
| 8 | criar `br_esocial` | `br_hr_payroll`, HR base |
| 9 | criar `br_sped` | `br_account`, `br_nfe` |
| 10 | expandir `br_presumido` e `br_real` | tax engine maduro |

## Decisões Arquiteturais Já Fixadas

- `gov_*` não é base conceitual do BR.
- `br_*` é família própria e independente.
- `l10n_br*` entra como base técnica reaproveitável.
- wrappers/community entram para nivelar stack, não para redefinir a arquitetura.
- dashboard BR só entra depois que `br_base`, `br_account` e `br_tax_engine` estiverem sólidos.

## Backlog Imediato

| Ordem | Item | Tipo |
| --- | --- | --- |
| 1 | inventariar quais módulos community serão trazidos para `payroll` e `account_reports` | decisão de stack |
| 2 | scaffold de `custom_addons/br_base` | implementação |
| 3 | scaffold de `custom_addons/br_account` | implementação |
| 4 | scaffold de `custom_addons/br_tax_engine` | implementação |
| 5 | ADR curta decidindo `l10n_br_edi` vs `br_nfe` | arquitetura |
