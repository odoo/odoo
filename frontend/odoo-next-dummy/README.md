# GRP (App Router + TypeScript)

Frontend Next.js separado, estilo visual inspirado no Odoo, usando Odoo como backend via BFF (`app/api/*`) para nao expor credenciais no browser.

## Arquitetura

- `src/lib/odoo-client/*`: autenticacao de sessao + helper JSON-RPC com timeout/erros.
- `src/app/api/gov/[suite]/*`: rotas proxy/BFF genericas por modulo da suite gov.
- `src/app/api/*`: rotas legacy de compatibilidade.
- `src/components/*`: UI reutilizavel (topbar, sidebar, cards, tabela, estados e abas).
- `src/lib/gov-suite.ts`: registro central dos modulos da Gov Suite.
- `src/lib/server/odoo-service.ts`: schema server-side por modulo (campos candidatos + mapeamento de destaque/detalhe).
- `src/app/*`: paginas App Router (Dashboard + Gov Suite por rotas dinamicas).

## Requisitos

- Node.js 20+
- npm 10+
- Odoo acessivel por URL

## Setup local

1. Instale dependencias:

```bash
npm install
```

2. Copie variaveis:

```bash
cp .env.example .env.local
```

3. Ajuste `.env.local` para seu backend Odoo:

```env
ODOO_BASE_URL=http://localhost:8069
ODOO_DB=kodoo
ODOO_USER=admin
ODOO_PASSWORD=admin
ODOO_TIMEOUT_MS=15000
ODOO_PROCESS_MODEL=gov.processo
ODOO_DOCUMENT_MODEL=gov.processo.doc
ODOO_DOTACAO_MODEL=gov.processo.dotacao
ODOO_EXECUCAO_MODEL=gov.processo.tramite
ODOO_COMPRAS_ITEM_MODEL=gov.compras.item.track
ODOO_COMPRAS_CATALOGO_MODEL=gov.compras.catalog.item
ODOO_COMPRAS_PREVISAO_MODEL=gov.compras.previsao
ODOO_EMPENHO_MODEL=gov.empenho
ODOO_LIQUIDACAO_MODEL=gov.liquidacao
ODOO_PD_MODEL=gov.pd
ODOO_PAGAMENTO_MODEL=gov.pagamento
ODOO_CONCILIACAO_IMPORTACAO_MODEL=gov.conciliacao.importacao
ODOO_CONCILIACAO_PENDENCIA_MODEL=gov.conciliacao.pendencia
ODOO_GOV_BASE_MODEL=res.company
ODOO_KNOWLEDGE_BRIDGE_MODEL=knowledge.article
ODOO_AI_TEMPLATE_MODEL=gov.ai.template
ODOO_AI_MEMORY_MODEL=gov.ai.memory
```

Esses defaults foram alinhados com os modelos encontrados em `custom_addons/public_sector/gov_processos`.
Se `.env.local` nao existir, o GRP usa fallback local: `http://localhost:8069`, DB `kodoo`, user `admin`, password `admin`.

4. Rode em dev:

```bash
npm run dev
```

Se ocorrer erro de chunk faltante (`Cannot find module './xxx.js'`), use modo limpo:

```bash
npm run dev:fresh
```

## Como o app aponta para seu Odoo

- Toda chamada do browser vai para `app/api/*`.
- As rotas API usam `src/lib/server/odoo-service.ts`.
- O service usa `src/lib/odoo-client` para:
  - autenticar em `/web/session/authenticate`;
  - chamar `/web/dataset/call_kw/...`;
  - aplicar timeout e mapear erros.

Credenciais ficam apenas no servidor (env vars), nunca no frontend.

## Paginas implementadas (Gov Suite)

- `/` Dashboard: cards + resumo + tabela de ultimos processos.
- `/gov`: hub da Gov Suite.
- `/gov/[suite]`: listagem paginada da suite.
- `/gov/[suite]/[id]`: detalhe com abas fake.

Suites configuradas inicialmente:
- `processos`
- `dotacoes`
- `execucoes`
- `documento-dfd`
- `compras-itens`
- `compras-catalogo`
- `compras-previsoes`
- `empenhos`
- `liquidacoes`
- `programacao-desembolso`
- `pagamentos`
- `conciliacao-importacoes`
- `conciliacao-pendencias`
- `gov-base-ug`
- `knowledge-bridge`
- `ai-templates`
- `ai-memory`

Cada modulo usa schema proprio no backend para:
- escolher campo de destaque da listagem;
- tentar metadados de detalhe por candidatos;
- evitar erro de campo inexistente com `fields_get` + filtro de campos.
- aplicar filtros por query params na API (`q`, `state`, `process_type`, `active`, etc.).

## Acoes operacionais (detalhe)

No detalhe (`/gov/[suite]/[id]`), o GRP ja suporta acoes de fluxo via API `POST /api/gov/[suite]/[id]` com whitelist por suite.
Payload padrao:

```json
{ "funcao": "impne" }
```

Compatibilidade: `acao` e `action` continuam aceitos.

Exemplos de suites com acoes habilitadas:
- `processos` (requisicao/NAD compras, avancar fase)
- `compras-previsoes` (catalogo, revisao, aprovacao)
- `empenhos`, `liquidacoes`, `programacao-desembolso`, `pagamentos`
- `conciliacao-importacoes`
- `documento-dfd`

### Convencao mnemônica de funcoes (GRP)

As funcoes no frontend seguem padrao mnemônico curto:
- `atu*`: atualizar estado/fluxo
- `lis*`: listar/consultar
- `imp*`: imprimir/emitir/gerar arquivo

Exemplos:
- `lispd`: consulta PDs
- `impne`: emite NE
- `atuconciliacao`: atualiza processamento da conciliacao bancaria
- `lisevento`: consulta eventos

Helpers server-side disponiveis em `src/lib/server/odoo-service.ts`:
- `lisgov`, `detgov`, `atugov`
- `lispd`, `lisevento`

Rotas legadas (compatibilidade):
- `/processos`
- `/documento-dfd/[id]`

Todas possuem estados de `loading`, `erro` e `empty`.

## Testes

- Unit: `src/tests/unit/odoo-client.test.ts`
- API route: `src/tests/api/processos-route.test.ts`
- Componente: `src/tests/components/card.test.tsx`

Rodar:

```bash
npm run test
```

## Cloudflare Pages/Workers

Este projeto esta preparado com `@opennextjs/cloudflare`.

### Build

```bash
npm run build:cf
```

### Deploy

1. Login no Cloudflare:

```bash
npx wrangler login
```

2. Configure variaveis (Pages/Workers):
- `ODOO_BASE_URL`
- `ODOO_DB`
- `ODOO_USER`
- `ODOO_PASSWORD`
- opcionais:
  - `ODOO_TIMEOUT_MS`
  - `ODOO_PROCESS_MODEL`
  - `ODOO_DOCUMENT_MODEL`
  - `ODOO_DOTACAO_MODEL`
  - `ODOO_EXECUCAO_MODEL`
  - `ODOO_COMPRAS_ITEM_MODEL`
  - `ODOO_COMPRAS_CATALOGO_MODEL`
  - `ODOO_COMPRAS_PREVISAO_MODEL`
  - `ODOO_EMPENHO_MODEL`
  - `ODOO_LIQUIDACAO_MODEL`
  - `ODOO_PD_MODEL`
  - `ODOO_PAGAMENTO_MODEL`
  - `ODOO_CONCILIACAO_IMPORTACAO_MODEL`
  - `ODOO_CONCILIACAO_PENDENCIA_MODEL`
  - `ODOO_GOV_BASE_MODEL`
  - `ODOO_KNOWLEDGE_BRIDGE_MODEL`
  - `ODOO_AI_TEMPLATE_MODEL`
  - `ODOO_AI_MEMORY_MODEL`

3. Deploy:

```bash
npm run deploy:cf
```

## Scripts

- `npm run dev`
- `npm run build`
- `npm run start`
- `npm run test`
- `npm run build:cf`
- `npm run deploy:cf`

## Como estender um modulo GOV

1. Adicione/ajuste o modulo em `src/lib/gov-suite.ts` (label/path).
2. No `src/lib/server/odoo-service.ts`, ajuste `suiteSchemaByKey`:
   - `highlightLabel`
   - `highlightCandidates`
   - `detailCandidates`
3. Se for novo model, mapeie no `resolveModel` com env var correspondente.
4. Inclua a env no `.env.example` e no ambiente Cloudflare.

## Checklist de validacao final

- [ ] `.env.local` configurado com backend Odoo real.
- [ ] Dashboard retornando registros reais.
- [ ] Processos paginados funcionando.
- [ ] Documento DFD abrindo por ID valido.
- [ ] Suites GOV (`dotacoes`, `execucoes`, `ai-*`) com retorno do Odoo.
- [ ] Nenhuma credencial exposta no browser.
- [ ] Testes passando (`npm run test`).
- [ ] Build Cloudflare gerado (`npm run build:cf`).
- [ ] Deploy concluido (`npm run deploy:cf`).
