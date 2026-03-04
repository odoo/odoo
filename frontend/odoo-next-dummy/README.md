# Odoo Next Dummy (App Router + TypeScript)

Frontend Next.js separado, estilo visual inspirado no Odoo, usando Odoo como backend via BFF (`app/api/*`) para nao expor credenciais no browser.

## Arquitetura

- `src/lib/odoo-client/*`: autenticacao de sessao + helper JSON-RPC com timeout/erros.
- `src/app/api/*`: rotas proxy/BFF que falam com o Odoo no servidor.
- `src/components/*`: UI reutilizavel (topbar, sidebar, cards, tabela, estados e abas).
- `src/app/*`: paginas App Router (Dashboard, Processos, Documento DFD).

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
ODOO_DB=atlas
ODOO_USER=admin
ODOO_PASSWORD=admin
ODOO_TIMEOUT_MS=15000
ODOO_PROCESS_MODEL=gov.processo
ODOO_DOCUMENT_MODEL=gov.documento.dfd
```

4. Rode em dev:

```bash
npm run dev
```

## Como o app aponta para seu Odoo

- Toda chamada do browser vai para `app/api/*`.
- As rotas API usam `src/lib/server/odoo-service.ts`.
- O service usa `src/lib/odoo-client` para:
  - autenticar em `/web/session/authenticate`;
  - chamar `/web/dataset/call_kw/...`;
  - aplicar timeout e mapear erros.

Credenciais ficam apenas no servidor (env vars), nunca no frontend.

## Paginas implementadas

- `/` Dashboard: cards + resumo + tabela de ultimos processos.
- `/processos`: listagem paginada.
- `/documento-dfd/[id]`: detalhe do documento com abas fake.

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

## Checklist de validacao final

- [ ] `.env.local` configurado com backend Odoo real.
- [ ] Dashboard retornando registros reais.
- [ ] Processos paginados funcionando.
- [ ] Documento DFD abrindo por ID valido.
- [ ] Nenhuma credencial exposta no browser.
- [ ] Testes passando (`npm run test`).
- [ ] Build Cloudflare gerado (`npm run build:cf`).
- [ ] Deploy concluido (`npm run deploy:cf`).
