# gov_auditoria Execution Backlog

Data: 2026-03-26
Base funcional: `doc/toCodex/gov_auditoria_spec_v1.1.pdf`
Complemento arquitetural: `doc/toCodex/gov_auditoria_spec_v1.1_addendum.md`

## Objetivo

Transformar a especificação do módulo `gov_auditoria` em um backlog técnico executável, preservando a estratégia em 3 frentes:

- fortalecer a base
- entregar o MVP do módulo
- evoluir para o motor anual completo

## Onda 1: Fortalecimento da Base

### Epic 1.1: Segurança multi-UG em `gov_processos`

Resultado esperado:

- registros de processo, documento, tramitação e vínculos isolados corretamente por UG

Entregas:

- revisar `gov_base/models/res_company.py`
- decidir entre ativar regras dinâmicas já geradas ou substituí-las por regras estáticas no domínio de `gov_processos`
- revisar permissões amplas em `gov_processos/security/ir.model.access.csv`
- validar leitura/escrita por `group_gov_operador`, `group_gov_gestor` e `group_gov_admin`

Arquivos-alvo:

- `/home/green/odoo/custom_addons/public_sector/gov_base/models/res_company.py`
- `/home/green/odoo/custom_addons/public_sector/gov_processos/security/ir.model.access.csv`
- possível novo arquivo de regras em `/home/green/odoo/custom_addons/public_sector/gov_processos/security/`

Critérios de aceite:

- operador vê apenas registros da sua `company_id`
- gestor/admin seguem a política definida sem vazamento cross-company
- testes cobrindo acesso por grupo

### Epic 1.2: Fechamento de exercício e consistência contábil

Resultado esperado:

- o exercício usado por auditoria pode ser tratado como formalmente encerrado

Entregas:

- revisar integração entre `account.fiscal.year`, lock date fiscal e lock date por diário
- definir critério programático “exercício apto para geração anual”
- endurecer validações quando `gov_public_accounting_enabled = True`
- documentar a dependência operacional entre exercício e geração de anexos

Arquivos-alvo:

- `/home/green/odoo/custom_addons/public_sector/gov_account_fiscal_year/models/account_fiscal_year.py`
- `/home/green/odoo/custom_addons/public_sector/gov_account_lock_date_update/wizard/account_lock_date_update_wizard.py`
- `/home/green/odoo/custom_addons/public_sector/gov_account_journal_lock_date/models/account_journal.py`
- `/home/green/odoo/custom_addons/public_sector/gov_public_accounting/models/account_move.py`

Critérios de aceite:

- exercício fechado não aceita movimentação indevida segundo a política pública adotada
- há método claro para validar se o ciclo anual pode gerar anexos

### Epic 1.3: Cobertura de testes do ciclo financeiro

Resultado esperado:

- maior confiança em regressão para empenho, liquidação, pagamento e fechamento

Entregas:

- criar testes de NE, NL e OP por exercício e empresa
- criar testes de vínculo com processo quando aplicável
- criar testes de lock date e exercício encerrado

Arquivos-alvo:

- `/home/green/odoo/custom_addons/public_sector/gov_empenho/tests/`
- `/home/green/odoo/custom_addons/public_sector/gov_liquidacao/tests/`
- `/home/green/odoo/custom_addons/public_sector/gov_pagamento/tests/`
- `/home/green/odoo/custom_addons/public_sector/gov_public_accounting/tests/`

Critérios de aceite:

- suíte mínima cobrindo criação, transição de estado e restrições essenciais

## Onda 2: MVP `gov_auditoria`

### Epic 2.1: Scaffold e segurança do módulo

Resultado esperado:

- módulo instalável com grupos, menus e regras básicas

Entregas:

- criar addon `custom_addons/public_sector/gov_auditoria`
- criar `__manifest__.py`
- criar grupos:
  - `group_auditoria_user`
  - `group_auditoria_manager`
  - `group_auditoria_auditor`
  - `group_auditoria_admin`
- criar `ir.model.access.csv`
- criar `gov_auditoria_rules.xml`

Arquivos-alvo:

- `/home/green/odoo/custom_addons/public_sector/gov_auditoria/__manifest__.py`
- `/home/green/odoo/custom_addons/public_sector/gov_auditoria/security/ir.model.access.csv`
- `/home/green/odoo/custom_addons/public_sector/gov_auditoria/security/gov_auditoria_groups.xml`
- `/home/green/odoo/custom_addons/public_sector/gov_auditoria/security/gov_auditoria_rules.xml`

Critérios de aceite:

- módulo instala
- isolamento por `company_id` nos modelos operacionais
- cadastro global de `gov.auditoria.orgao` controlado por grupo admin

### Epic 2.2: Modelos centrais do domínio

Resultado esperado:

- ciclo anual funcional com dossiê, prazo, evento, apontamento, decisão e espelho

Entregas:

- implementar modelos:
  - `gov.auditoria.ciclo`
  - `gov.auditoria.orgao`
  - `gov.auditoria.evento`
  - `gov.auditoria.prazo`
  - `gov.auditoria.prazo.suspensao`
  - `gov.auditoria.documento`
  - `gov.auditoria.apontamento`
  - `gov.auditoria.decisao`
  - `gov.auditoria.determinacao`
  - `gov.auditoria.espelho`
  - `gov.auditoria.checklist`
  - `gov.auditoria.checklist.item`
- aplicar constraint de unicidade do ciclo
- garantir `company_id` em todos os modelos operacionais

Arquivos-alvo:

- `/home/green/odoo/custom_addons/public_sector/gov_auditoria/models/`

Critérios de aceite:

- CRUD completo
- constraint única funcionando
- `processo_id` opcional e manual
- `orgao` global e reutilizável

### Epic 2.3: Workflow do ciclo

Resultado esperado:

- transições de estado implementadas com validações e efeitos colaterais mínimos

Entregas:

- botões de ação para estados do ciclo
- bloqueios por perfil
- geração de checklist e prazos padrão na remessa
- criação de determinações ao registrar acórdão

Arquivos-alvo:

- `/home/green/odoo/custom_addons/public_sector/gov_auditoria/models/gov_auditoria_ciclo.py`
- `/home/green/odoo/custom_addons/public_sector/gov_auditoria/models/gov_auditoria_decisao.py`

Critérios de aceite:

- fluxo principal até `encerrado`
- `arquivado` disponível como exceção administrativa

### Epic 2.4: Dossiê documental

Resultado esperado:

- documentos de auditoria com versão, hash, protocolo e origem próprios

Entregas:

- implementar `gov.auditoria.documento` como repositório oficial
- permitir referência opcional a `gov.processo.doc` apenas como contexto de leitura
- suportar versões e substituição sem deleção

Arquivos-alvo:

- `/home/green/odoo/custom_addons/public_sector/gov_auditoria/models/gov_auditoria_documento.py`
- `/home/green/odoo/custom_addons/public_sector/gov_auditoria/views/gov_auditoria_documento_views.xml`

Critérios de aceite:

- hash persistido
- histórico de versões preservado
- sem acoplamento autoritativo com `gov.processo.doc`

### Epic 2.5: Espelho histórico

Resultado esperado:

- importação e lançamento manual com rastreabilidade e validação

Entregas:

- implementar `gov.auditoria.espelho`
- implementar wizard de importação CSV/XLSX
- persistir arquivo-fonte como `ir.attachment`
- bloquear importados sem evidência
- indicador `cobertura_espelho_pct`

Arquivos-alvo:

- `/home/green/odoo/custom_addons/public_sector/gov_auditoria/models/gov_auditoria_espelho.py`
- `/home/green/odoo/custom_addons/public_sector/gov_auditoria/wizard/gov_auditoria_espelho_import_wizard.py`
- `/home/green/odoo/custom_addons/public_sector/gov_auditoria/views/gov_auditoria_espelho_views.xml`

Critérios de aceite:

- preview com erros
- confirmação cria registros não validados
- `documento_fonte_id` obrigatório para importados

### Epic 2.6: Anexos 4.320 MVP

Resultado esperado:

- geração dos anexos 12, 13, 14 e 15 em modo nativo, com base mínima validada

Entregas:

- criar motor `gov.auditoria.anexo.generator.*`
- validar pré-requisitos:
  - exercício encerrado
  - mapeamento contábil mínimo validado
  - cobertura 100% quando houver espelho
- gerar documentos oficiais do ciclo
- render via Typst com fallback QWeb

Arquivos-alvo:

- `/home/green/odoo/custom_addons/public_sector/gov_auditoria/models/`
- `/home/green/odoo/custom_addons/public_sector/gov_auditoria/report/`

Critérios de aceite:

- anexo gerado vira `gov.auditoria.documento`
- re-geração versiona e substitui sem apagar histórico

### Epic 2.7: Interface e dashboard

Resultado esperado:

- navegação operacional para o time de auditoria

Entregas:

- menus raiz e secundários
- views list/form/calendar
- indicadores:
  - progresso do checklist
  - cobertura do espelho
  - prazos próximos e vencidos

Arquivos-alvo:

- `/home/green/odoo/custom_addons/public_sector/gov_auditoria/views/`

Critérios de aceite:

- fluxo utilizável sem depender de backend técnico

### Epic 2.8: Testes do MVP

Resultado esperado:

- cobertura mínima do novo domínio

Entregas:

- testes para:
  - criação de ciclo
  - constraint de unicidade
  - transições de estado
  - criação de prazo/checklist na remessa
  - importação de espelho
  - bloqueio de importado sem evidência
  - geração dos anexos MVP

Arquivos-alvo:

- `/home/green/odoo/custom_addons/public_sector/gov_auditoria/tests/`

## Onda 3: Motor Anual Completo

### Epic 3.1: Expansão dos anexos da 4.320

Entregas:

- anexos 1, 2, 6 e 8
- validações adicionais por plano de contas e classificações

### Epic 3.2: Parametrização avançada por órgão

Entregas:

- estados obrigatórios por órgão
- checklists por órgão
- fluxos específicos TCE/TCM/TCU/CGE

### Epic 3.3: Reconstrução avançada e conciliação

Entregas:

- reconciliação entre espelho e base Odoo
- alertas de divergência
- relatórios de cobertura e inconsistência

### Epic 3.4: Automação e portal externo

Entregas:

- notificações automáticas de prazo
- portal read-only para auditor externo
- integração com APIs de tribunais quando viável

## Ordem prática de implementação

1. Onda 1 completa ou suficientemente estabilizada.
2. Scaffold e segurança do `gov_auditoria`.
3. Modelos centrais e workflow.
4. Dossiê documental e espelho.
5. Gerador dos anexos MVP.
6. Dashboard e testes.
7. Expansão da Onda 3.

## Dependências de arquitetura a respeitar

- `processo_id` no ciclo é opcional e manual
- `gov.auditoria.documento` é o dossiê oficial
- `gov.auditoria.orgao` é global e administrado por perfil
- `account.fiscal.year` é o modelo real de exercício
- espelho nunca alimenta `account.move`
- nenhum documento é apagado em re-geração, apenas versionado
