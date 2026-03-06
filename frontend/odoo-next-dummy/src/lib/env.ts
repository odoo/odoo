function toInt(value: string | undefined, fallback: number): number {
  if (!value) {
    return fallback;
  }
  const parsed = Number.parseInt(value, 10);
  return Number.isNaN(parsed) ? fallback : parsed;
}

function withDefault(name: string, fallback: string): string {
  const value = process.env[name];
  if (!value || !value.trim()) {
    return fallback;
  }
  return value.trim();
}

export const env = {
  // Defaults keep o GRP funcional em ambiente local mesmo sem .env.local.
  odooBaseUrl: withDefault("ODOO_BASE_URL", "http://localhost:8069"),
  odooDb: withDefault("ODOO_DB", "kore"),
  odooUser: withDefault("ODOO_USER", "admin"),
  odooPassword: withDefault("ODOO_PASSWORD", "admin"),
  odooTimeoutMs: toInt(process.env.ODOO_TIMEOUT_MS, 15000),
  odooProcessModel: process.env.ODOO_PROCESS_MODEL ?? "gov.processo",
  odooDocumentModel: process.env.ODOO_DOCUMENT_MODEL ?? "gov.processo.doc",
  odooDotacaoModel: process.env.ODOO_DOTACAO_MODEL ?? "gov.processo.dotacao",
  odooExecucaoModel: process.env.ODOO_EXECUCAO_MODEL ?? "gov.processo.tramite",
  odooComprasItemModel: process.env.ODOO_COMPRAS_ITEM_MODEL ?? "gov.compras.item.track",
  odooComprasCatalogoModel: process.env.ODOO_COMPRAS_CATALOGO_MODEL ?? "gov.compras.catalog.item",
  odooComprasPrevisaoModel: process.env.ODOO_COMPRAS_PREVISAO_MODEL ?? "gov.compras.previsao",
  odooEmpenhoModel: process.env.ODOO_EMPENHO_MODEL ?? "gov.empenho",
  odooLiquidacaoModel: process.env.ODOO_LIQUIDACAO_MODEL ?? "gov.liquidacao",
  odooPdModel: process.env.ODOO_PD_MODEL ?? "gov.pd",
  odooPagamentoModel: process.env.ODOO_PAGAMENTO_MODEL ?? "gov.pagamento",
  odooConciliacaoImportacaoModel:
    process.env.ODOO_CONCILIACAO_IMPORTACAO_MODEL ?? "gov.conciliacao.importacao",
  odooConciliacaoPendenciaModel:
    process.env.ODOO_CONCILIACAO_PENDENCIA_MODEL ?? "gov.conciliacao.pendencia",
  odooGovBaseModel: process.env.ODOO_GOV_BASE_MODEL ?? "res.company",
  odooKnowledgeBridgeModel: process.env.ODOO_KNOWLEDGE_BRIDGE_MODEL ?? "knowledge.article",
  odooAiTemplateModel: process.env.ODOO_AI_TEMPLATE_MODEL ?? "gov.ai.template",
  odooAiMemoryModel: process.env.ODOO_AI_MEMORY_MODEL ?? "gov.ai.memory"
};
