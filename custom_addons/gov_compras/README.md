# GRP Compras (`gov_compras`)

Modulo de compras integrado ao `gov_processo` para rastreio de itens, previsao e controle do valor empenhado.

## Fluxo base

1. Cadastre itens no menu `Compras > Catalogo da UG`.
2. No processo, aba `Compras`, adicione itens (gera `track_id` automatico).
3. Clique `Gerar Requisicao` para mover itens de `rascunho` para `requisitado` e criar documento no processo.
4. Clique `Aprovar Requisicao (NAD)` para mover itens para `nad` e criar documento NAD no processo.
5. Na NE (`gov.empenho`), vincule `Item de Compra (Rastreio)`.
6. O sistema bloqueia `valor_empenho` maior que `valor_arrematado`.

## Previsao orcamentaria

1. Abra `Compras > Previsao Orcamentaria`.
2. Crie uma previsao por `ano + UG`.
3. Use `Atualizar pelo Catalogo` para preencher linhas com metricas dinamicas:
   - media historica,
   - media sazonal,
   - preco conservador (maximo entre media, mediana e sazonal).

## Observacoes

- `gov.processo` e a fonte de verdade: cada etapa gera documento no processo.
- O rastreio (`track_id`) deve acompanhar os documentos ate o empenho.
