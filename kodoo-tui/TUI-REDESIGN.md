# TUI Redesign Blueprint

## Objetivo
Transformar `make tui` / `make tui-live` em um cockpit operacional para o Kodoo, orientado por estado, contexto e ações úteis, em vez de uma UI redundante em torno de targets do Makefile.

## Diagnóstico do estado atual

### Problemas principais
1. **Redundância de fluxo**
   - Launchpad inicial
   - Aba Actions
   - Hotkeys no Dashboard
   - Overlays de confirmação
   Todos convergem para quase o mesmo backend (`make <target>`), mas por superfícies concorrentes.

2. **Modelo mental ruim**
   A UI está organizada por mecanismos técnicos (`Dashboard`, `Logs`, `Actions`, `Config`) em vez de intenções operacionais:
   - o que está rodando?
   - está saudável?
   - em qual modo quero operar?
   - qual banco estou usando?
   - o que quebrou?
   - qual ação devo tomar agora?

3. **Dashboard pouco decisivo**
   Mostra telemetria, mas não prioriza:
   - modo atual
   - banco ativo
   - URL local/pública
   - incidente principal
   - próxima ação sugerida

4. **Actions como parede de comandos**
   A lista de ações é correta tecnicamente, mas ruim para operação humana.

5. **Excesso de overlay/modal**
   A experiência é fragmentada demais para tarefas simples.

## Referências de produto

### LazyDocker
Usar como referência para:
- foco operacional
- ações contextuais
- leitura rápida de estado
- sensação de controle ao vivo

### k9s
Usar como referência para:
- navegação por contexto
- drill-down limpo
- estado -> detalhe -> ação
- atalhos consistentes

### tview
Usar como referência conceitual para:
- formulários claros
- tabelas diretas
- modais curtos
- layout mais utilitário e menos ornamental

### Bubble Tea
**Manter o framework atual por enquanto.**
O problema principal não é o framework, e sim o desenho da experiência.

## Nova arquitetura de navegação

### Abas principais
1. `Overview`
2. `Runtime`
3. `Databases`
4. `Logs`
5. `Config`

### Comando global
- `p`: Command Palette / Quick Switcher
- `?`: ajuda contextual
- `r`: refresh global
- `q`: sair
- `esc`: voltar/fechar modal
- `/`: buscar/filtrar
- `tab`: alternar panes
- `enter`: ação principal contextual

## 1. Overview

### Objetivo
Responder instantaneamente:
- qual modo está ativo?
- qual banco está ativo?
- local está acessível?
- público está acessível?
- quais serviços estão saudáveis?
- qual incidente atual mais importante?
- qual a próxima ação sugerida?

### Layout proposto

#### Cabeçalho
- modo atual
- banco atual
- URL local
- URL pública
- arquivo de config ativo (`.env`)
- timestamp do último refresh

#### Painel esquerdo: Health
- db
- odoo
- nginx
- tunnel
- ollama
- PID local
- status resumido com cores e texto curto

#### Painel central: Runtime summary
- backend atual (docker/local)
- portas
- DB backend
- config gerada ou pendente
- smoke status
- warnings

#### Painel direito: Incidents / Next step
- erro/incidente principal
- últimas falhas relevantes
- ação sugerida
  - ex.: "Preencha CLOUDFLARED_TOKEN e rode Start Tunnel"
  - ex.: "DB local indisponível; abra Databases ou valide PostgreSQL"

### Ações rápidas
- `s`: start/stop contextual
- `w`: switch mode
- `d`: abrir Databases
- `l`: abrir Logs
- `t`: run troubleshoot
- `c`: abrir Config

## 2. Runtime

### Objetivo
Controlar o modo operacional do sistema.

### Modos esperados
- Stable Docker
- Stable Tunnel
- Dev Host
- Dev Project
- Local diagnostic / manager
- Stopped

### Para cada modo mostrar
- descrição
- backend esperado
- pré-requisitos
- portas
- risco/impacto
- ação principal
- ações secundárias

### Ações contextuais por modo
- iniciar
- parar
- validar
- ver logs
- abrir databases compatíveis

### Regra de UX
Essa tela substitui a maior parte da antiga aba `Actions`.
Ela deve ser uma lista curta de modos, não uma árvore gigante de targets.

## 3. Databases

### Objetivo
Dar visibilidade operacional ao banco, que hoje está subdimensionado.

### Lista principal
Colunas mínimas:
- nome
- backend
- owner
- tamanho
- tags (`prod`, `ktest`, `dev`, `local`, `docker`)
- status de conectividade

### Painel lateral de detalhes
- em quais modos esse DB pode ser usado
- comando/ação que será disparada
- alertas
- data/hora de uso recente (se disponível depois)

### Ações
- usar neste modo
- abrir manager
- backup
- restore
- validar conexão
- clonar (fase posterior)

## 4. Logs

### Subvisões
1. `Incidents`
2. `Raw Logs`

### Incidents
Lista priorizada de problemas operacionais:
- conf faltando
- tunnel sem token
- db inacessível
- odoo caiu no startup
- smoke falhou
- domínio público com erro

### Raw Logs
- filtro por serviço
- busca
- pausa de scroll
- navegação por linhas
- copiar trecho/último erro (fase posterior)

### Regra
O operador chega primeiro em incidente, não em stream bruto.

## 5. Config

### Subáreas
1. Setup Wizard
2. Config Values
3. Generate
4. Validate

### Setup Wizard
Fluxo didático para criar `.env`:
1. domínio
2. email
3. PostgreSQL local
4. PostgreSQL produção
5. admin Odoo
6. Cloudflare token
7. portas principais
8. salvar `.env`

### Config Values
Tabela com:
- chave
- valor mascarado
- origem
- obrigatória?
- usada por quais modos?

### Generate
Ações:
- gerar `kodoo.prod.local.conf`
- gerar `kodoo.dev-host.local.conf`
- gerar `kodoo.dev-project.local.conf`

### Validate
Checklist:
- `.env` existe
- segredos mínimos preenchidos
- portas coerentes
- DB local acessível
- configs renderizáveis
- túnel pronto quando aplicável

## Command Palette

### Objetivo
Substituir o launchpad como entrada rápida.

### Ações possíveis
- trocar para tela
- escolher modo
- rodar ação contextual
- selecionar DB
- abrir config
- disparar smoke/troubleshoot

### Regra
- não é a home obrigatória
- é um acelerador
- abre com `p`

## Modelo de estado central

### Criar um `AppState` agregado

#### Blocos sugeridos
- `RuntimeState`
- `ServiceHealth`
- `DatabaseState`
- `ConfigState`
- `IncidentState`
- `TaskState`

### Fontes de verdade
- docker ps/stats
- pid files
- smoke/troubleshoot results
- arquivos `.env` / configs geradas
- checagens de conectividade local/publica
- lista de databases

### Regra
As telas não devem recomputar tudo isoladamente. Elas devem renderizar snapshots normalizados.

## Incidents engine

### Incidentes mínimos detectáveis
- `.env` ausente
- config gerada ausente
- PostgreSQL local inacessível
- Docker DB parado
- Odoo local morto com PID stale
- smoke local falhou
- smoke público falhou
- Cloudflare token ausente quando modo tunnel é solicitado
- tunnel parado enquanto domínio parece depender dele

### Severidade
- `critical`
- `warning`
- `info`

### Saída esperada
Cada incidente deve oferecer:
- resumo curto
- causa provável
- ação sugerida

## Roadmap de implementação

## Fase 1 — reestruturação sem trocar backend

### Meta
Melhorar drasticamente a UX sem reescrever o backend operacional.

### Entregas
- trocar tabs para `Overview`, `Runtime`, `Databases`, `Logs`, `Config`
- remover `Actions` como eixo principal
- transformar launchpad em palette ou tela secundária
- criar overview com resumo real
- criar tela `Runtime`
- criar tela `Databases`
- mover `Incidents` para primeira classe dentro de `Logs`/Overview

## Fase 2 — estado agregado

### Meta
Adicionar `AppState` para reduzir acoplamento e duplicação.

### Entregas
- snapshot central
- incident detector
- next action suggestion
- refresh parcial coerente

## Fase 3 — polimento operacional

### Entregas
- forms melhores
- filtros melhores
- copy/export de diagnóstico
- histórico curto de ações
- UX de validação/config melhor

## Ordem recomendada de refactor no código atual

1. Criar novas labels e estrutura de navegação principal
2. Introduzir `AppState` central com adaptadores mínimos
3. Reimplementar `Overview` usando estado agregado
4. Reimplementar `Runtime` a partir dos antigos actions groups
5. Extrair `Databases` para uma tela dedicada
6. Separar `Logs` em `Incidents` + `Raw Logs`
7. Rebaixar/remover redundâncias do dashboard antigo
8. Transformar launchpad em palette
9. Ajustar docs (`doc/tui.md`)

## Critérios de sucesso

A nova TUI será considerada boa quando:
- um operador novato entender o modo atual em menos de 5 segundos
- o caminho para subir o ambiente certo exigir no máximo 1 tela + 1 confirmação
- o caminho para diagnosticar falha local ou pública exigir no máximo 2 passos
- databases sejam visíveis e acionáveis sem caça ao target
- a UI deixe de parecer um catálogo de comandos do Makefile

## Decisões explícitas
- manter Bubble Tea por agora
- manter Makefile como backend operacional
- abandonar a centralidade da aba `Actions`
- priorizar Overview/Runtime/Databases
- `.env` é o arquivo principal; `.env.make` é legado compatível
