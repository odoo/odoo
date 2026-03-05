import { env } from "@/lib/env";
import { OdooClientError } from "@/lib/errors";
import { OdooClient } from "@/lib/odoo-client";

type GenericRecord = Record<string, unknown> & {
  id: number;
  display_name?: string;
  name?: string;
  state?: string;
  create_date?: string;
  write_date?: string;
};

type SuiteSchema = {
  highlightLabel: string;
  highlightCandidates: string[];
  detailCandidates: string[];
  fieldLabels?: Record<string, string>;
  domain?: unknown[];
  order?: string;
  filterRules?: Record<string, { field: string; operator: "=" | "ilike"; type: "string" | "number" | "boolean" }>;
};

type GovActionTone = "primary" | "warn" | "danger" | "neutral";

type GovActionSpec = {
  funcao: string;
  metodo: string;
  label: string;
  tone?: GovActionTone;
  allowedStates?: string[];
};

type ProcessWizardSelectionOption = {
  value: string;
  label: string;
};

type ProcessWizardFieldMeta = {
  string?: string;
  selection?: Array<[string, string]>;
};

type ProcessWizardTemplate = {
  id: number;
  name: string;
  docType: string;
  fase: string;
  processScope: string;
  isChecklist: boolean;
};

type ProcessWizardDefaults = {
  subject: string;
  origin_type: string;
  process_type: string;
  process_scope: string;
  ug_id: number | null;
  responsible_id: number | null;
};

type ProcessWizardMeta = {
  selections: {
    originType: ProcessWizardSelectionOption[];
    processType: ProcessWizardSelectionOption[];
    processScope: ProcessWizardSelectionOption[];
  };
  ugOptions: Array<{ id: number; name: string }>;
  responsibleOptions: Array<{ id: number; name: string }>;
  defaults: ProcessWizardDefaults;
  recommendedTemplates: ProcessWizardTemplate[];
};

type ProcessWizardInput = {
  subject?: string;
  origin_type?: string;
  process_type?: string;
  process_scope?: string;
  ug_id?: number | null;
  responsible_id?: number | null;
};

type ProcessUpdateInput = {
  subject?: string;
  origin_type?: string;
  process_type?: string;
  process_scope?: string;
  ug_id?: number | null;
  responsible_id?: number | null;
  prazo_resposta?: string | null;
  retroativo?: boolean;
  urgencia?: boolean;
};

const suiteSchemaByKey: Record<string, SuiteSchema> = {
  processos: {
    highlightLabel: "Numero",
    highlightCandidates: ["name", "display_name", "subject"],
    detailCandidates: ["subject", "origin_type", "process_type", "process_scope", "fase_atual", "state"],
    fieldLabels: {
      subject: "Assunto",
      origin_type: "Origem",
      process_type: "Tipo de Processo",
      process_scope: "Escopo",
      fase_atual: "Fase Atual",
      state: "Estado"
    },
    order: "id desc",
    filterRules: {
      q: { field: "display_name", operator: "ilike", type: "string" },
      state: { field: "state", operator: "=", type: "string" },
      process_type: { field: "process_type", operator: "=", type: "string" }
    }
  },
  dotacoes: {
    highlightLabel: "Rubrica",
    highlightCandidates: ["programa", "natureza_despesa", "fonte_recurso"],
    detailCandidates: ["programa", "acao", "natureza_despesa", "fonte_recurso", "exercicio", "reservado"],
    fieldLabels: {
      programa: "Programa",
      acao: "Acao",
      natureza_despesa: "Natureza da Despesa",
      fonte_recurso: "Fonte de Recurso",
      exercicio: "Exercicio",
      reservado: "Reservado"
    },
    order: "id desc",
    filterRules: {
      q: { field: "programa", operator: "ilike", type: "string" },
      exercicio: { field: "exercicio", operator: "=", type: "number" },
      reservado: { field: "reservado", operator: "=", type: "boolean" }
    }
  },
  execucoes: {
    highlightLabel: "Acao",
    highlightCandidates: ["action", "display_name", "note"],
    detailCandidates: ["action", "note", "prazo_dias", "duration_hours", "date"],
    fieldLabels: {
      action: "Acao",
      note: "Observacao",
      prazo_dias: "Prazo (dias)",
      duration_hours: "Duracao (horas)",
      date: "Data"
    },
    order: "id desc",
    filterRules: {
      q: { field: "note", operator: "ilike", type: "string" },
      action: { field: "action", operator: "=", type: "string" }
    }
  },
  documento_dfd: {
    highlightLabel: "Documento",
    highlightCandidates: ["name", "display_name", "doc_type"],
    detailCandidates: ["name", "doc_type", "process_type", "version", "state", "dfd_area_requisitante"],
    fieldLabels: {
      name: "Titulo",
      doc_type: "Tipo de Documento",
      process_type: "Tipo de Processo",
      version: "Versao",
      state: "Estado",
      dfd_area_requisitante: "Area Requisitante"
    },
    domain: [["doc_type", "=", "dfd"]],
    order: "id desc",
    filterRules: {
      q: { field: "name", operator: "ilike", type: "string" },
      state: { field: "state", operator: "=", type: "string" },
      process_type: { field: "process_type", operator: "=", type: "string" }
    }
  },
  compras_itens: {
    highlightLabel: "Rastreio",
    highlightCandidates: ["track_id", "name", "display_name", "status"],
    detailCandidates: [
      "track_id",
      "status",
      "catalog_item_id",
      "quantidade",
      "unidade_medida",
      "valor_etp",
      "valor_estimado_ref",
      "valor_arrematado",
      "fornecedor_arrematado",
      "data_arremate",
      "preco_referencia_conservador",
      "media_preco_historico",
      "media_preco_sazonal"
    ],
    fieldLabels: {
      track_id: "ID Rastreio",
      status: "Etapa",
      catalog_item_id: "Item Catalogo",
      quantidade: "Quantidade",
      unidade_medida: "Unidade",
      valor_etp: "Valor ETP",
      valor_estimado_ref: "Valor Referencia",
      valor_arrematado: "Valor Arrematado",
      fornecedor_arrematado: "Fornecedor",
      data_arremate: "Data Arremate",
      preco_referencia_conservador: "Preco Conservador",
      media_preco_historico: "Media Historica",
      media_preco_sazonal: "Media Sazonal"
    },
    order: "id desc",
    filterRules: {
      q: { field: "track_id", operator: "ilike", type: "string" },
      status: { field: "status", operator: "=", type: "string" },
      fornecedor_arrematado: { field: "fornecedor_arrematado", operator: "ilike", type: "string" }
    }
  },
  compras_catalogo: {
    highlightLabel: "Codigo",
    highlightCandidates: ["code", "name", "categoria"],
    detailCandidates: [
      "code",
      "name",
      "categoria",
      "natureza_despesa",
      "unidade_medida",
      "ativo_previsao",
      "active"
    ],
    fieldLabels: {
      code: "Codigo",
      name: "Item",
      categoria: "Categoria",
      natureza_despesa: "Natureza Despesa",
      unidade_medida: "Unidade",
      ativo_previsao: "Ativo Previsao",
      active: "Ativo"
    },
    order: "name asc, id desc",
    filterRules: {
      q: { field: "name", operator: "ilike", type: "string" },
      categoria: { field: "categoria", operator: "ilike", type: "string" },
      ativo_previsao: { field: "ativo_previsao", operator: "=", type: "boolean" }
    }
  },
  compras_previsoes: {
    highlightLabel: "Ano",
    highlightCandidates: ["ano", "name", "state"],
    detailCandidates: ["name", "ano", "state", "total_previsto", "ug_id", "observacao"],
    fieldLabels: {
      name: "Nome",
      ano: "Ano",
      state: "Estado",
      total_previsto: "Total Previsto",
      ug_id: "UG",
      observacao: "Observacao"
    },
    order: "ano desc, id desc",
    filterRules: {
      q: { field: "name", operator: "ilike", type: "string" },
      ano: { field: "ano", operator: "=", type: "number" },
      state: { field: "state", operator: "=", type: "string" }
    }
  },
  empenhos: {
    highlightLabel: "Numero NE",
    highlightCandidates: ["name", "processo_numero", "favorecido_nome", "state"],
    detailCandidates: [
      "name",
      "state",
      "processo_numero",
      "valor_empenho",
      "valor_anulado",
      "valor_liquido",
      "data_empenho",
      "data_vencimento"
    ],
    fieldLabels: {
      name: "Numero NE",
      state: "Estado",
      processo_numero: "Processo",
      valor_empenho: "Valor Empenhado",
      valor_anulado: "Valor Anulado",
      valor_liquido: "Valor Liquido",
      data_empenho: "Data Empenho",
      data_vencimento: "Vencimento"
    },
    order: "data_empenho desc, name desc",
    filterRules: {
      q: { field: "name", operator: "ilike", type: "string" },
      state: { field: "state", operator: "=", type: "string" }
    }
  },
  liquidacoes: {
    highlightLabel: "Numero NL",
    highlightCandidates: ["name", "empenho_name", "nf_numero", "state"],
    detailCandidates: [
      "name",
      "state",
      "empenho_name",
      "valor_liquidado",
      "valor_eventos",
      "valor_disponivel",
      "nf_numero",
      "nf_data",
      "data_liquidacao"
    ],
    fieldLabels: {
      name: "Numero NL",
      state: "Estado",
      empenho_name: "Numero NE",
      valor_liquidado: "Valor Liquidado",
      valor_eventos: "Valor Eventos",
      valor_disponivel: "Saldo Disponivel",
      nf_numero: "NF/Fatura",
      nf_data: "Data NF/Fatura",
      data_liquidacao: "Data Liquidacao"
    },
    order: "data_liquidacao desc, name desc",
    filterRules: {
      q: { field: "name", operator: "ilike", type: "string" },
      state: { field: "state", operator: "=", type: "string" }
    }
  },
  programacao_desembolso: {
    highlightLabel: "Numero PD",
    highlightCandidates: ["name", "nl_name", "state"],
    detailCandidates: [
      "name",
      "state",
      "nl_name",
      "valor",
      "saldo_disponivel_nl",
      "data_programacao",
      "op_name"
    ],
    fieldLabels: {
      name: "Numero PD",
      state: "Estado",
      nl_name: "Numero NL",
      valor: "Valor Programado",
      saldo_disponivel_nl: "Saldo Disponivel NL",
      data_programacao: "Data Programacao",
      op_name: "OP Vinculada"
    },
    order: "create_date desc, id desc",
    filterRules: {
      q: { field: "name", operator: "ilike", type: "string" },
      state: { field: "state", operator: "=", type: "string" }
    }
  },
  pagamentos: {
    highlightLabel: "Numero OP",
    highlightCandidates: ["name", "numero_doc", "pd_name", "state"],
    detailCandidates: [
      "name",
      "state",
      "pd_name",
      "valor",
      "forma_pagamento",
      "data_pagamento",
      "numero_doc"
    ],
    fieldLabels: {
      name: "Numero OP",
      state: "Estado",
      pd_name: "Numero PD",
      valor: "Valor",
      forma_pagamento: "Forma Pagamento",
      data_pagamento: "Data Pagamento",
      numero_doc: "Numero Documento"
    },
    order: "data_pagamento desc, name desc",
    filterRules: {
      q: { field: "name", operator: "ilike", type: "string" },
      state: { field: "state", operator: "=", type: "string" }
    }
  },
  conciliacao_importacoes: {
    highlightLabel: "Lote",
    highlightCandidates: ["name", "bank_name", "journal_id", "state"],
    detailCandidates: [
      "name",
      "state",
      "bank_name",
      "data_importacao",
      "total_linhas",
      "total_aceitos",
      "total_rejeitados",
      "pendencia_count"
    ],
    fieldLabels: {
      name: "Lote",
      state: "Estado",
      bank_name: "Banco",
      data_importacao: "Data Importacao",
      total_linhas: "Total Registros",
      total_aceitos: "Aceitos",
      total_rejeitados: "Rejeitados",
      pendencia_count: "Pendencias"
    },
    order: "data_importacao desc, id desc",
    filterRules: {
      q: { field: "name", operator: "ilike", type: "string" },
      state: { field: "state", operator: "=", type: "string" }
    }
  },
  conciliacao_pendencias: {
    highlightLabel: "Pendencia",
    highlightCandidates: ["name", "numero_doc", "tipo", "state"],
    detailCandidates: [
      "name",
      "state",
      "tipo",
      "numero_doc",
      "data_ocorrencia",
      "valor_banco",
      "valor_sistema",
      "diferenca"
    ],
    fieldLabels: {
      name: "Pendencia",
      state: "Estado",
      tipo: "Tipo",
      numero_doc: "Numero Documento",
      data_ocorrencia: "Data Ocorrencia",
      valor_banco: "Valor Banco",
      valor_sistema: "Valor Sistema",
      diferenca: "Diferenca"
    },
    order: "data_ocorrencia desc, id desc",
    filterRules: {
      q: { field: "name", operator: "ilike", type: "string" },
      state: { field: "state", operator: "=", type: "string" },
      tipo: { field: "tipo", operator: "=", type: "string" }
    }
  },
  gov_base_ug: {
    highlightLabel: "Codigo UG",
    highlightCandidates: ["codigo_ug", "codigo_siafi", "cnpj_ug", "name"],
    detailCandidates: ["name", "codigo_ug", "codigo_siafi", "cnpj_ug", "exercicio_fiscal"],
    fieldLabels: {
      name: "Unidade Gestora",
      codigo_ug: "Codigo UG",
      codigo_siafi: "Codigo SIAFI",
      cnpj_ug: "CNPJ UG",
      exercicio_fiscal: "Exercicio Fiscal"
    },
    order: "name asc, id asc",
    filterRules: {
      q: { field: "name", operator: "ilike", type: "string" },
      codigo_ug: { field: "codigo_ug", operator: "=", type: "string" },
      codigo_siafi: { field: "codigo_siafi", operator: "=", type: "string" }
    }
  },
  knowledge_bridge: {
    highlightLabel: "Artigo",
    highlightCandidates: ["name", "display_name", "category"],
    detailCandidates: ["name", "category", "company_id", "create_date", "write_date"],
    fieldLabels: {
      name: "Artigo",
      category: "Categoria",
      company_id: "UG/Empresa",
      create_date: "Criado em",
      write_date: "Atualizado em"
    },
    order: "write_date desc, id desc",
    filterRules: {
      q: { field: "name", operator: "ilike", type: "string" }
    }
  },
  ai_templates: {
    highlightLabel: "Template",
    highlightCandidates: ["name", "doc_type", "process_type"],
    detailCandidates: ["name", "doc_type", "process_type", "process_scope", "fase", "active"],
    fieldLabels: {
      name: "Template",
      doc_type: "Tipo de Documento",
      process_type: "Tipo de Processo",
      process_scope: "Escopo",
      fase: "Fase",
      active: "Ativo"
    },
    order: "id desc",
    filterRules: {
      q: { field: "name", operator: "ilike", type: "string" },
      doc_type: { field: "doc_type", operator: "=", type: "string" },
      active: { field: "active", operator: "=", type: "boolean" }
    }
  },
  ai_memory: {
    highlightLabel: "Memoria",
    highlightCandidates: ["name", "source_type", "source_model"],
    detailCandidates: ["name", "source_type", "source_model", "source_res_id", "use_count", "word_count", "active"],
    fieldLabels: {
      name: "Memoria",
      source_type: "Tipo de Origem",
      source_model: "Modelo de Origem",
      source_res_id: "ID de Origem",
      use_count: "Quantidade de Uso",
      word_count: "Total de Palavras",
      active: "Ativo"
    },
    order: "id desc",
    filterRules: {
      q: { field: "name", operator: "ilike", type: "string" },
      source_type: { field: "source_type", operator: "=", type: "string" },
      active: { field: "active", operator: "=", type: "boolean" }
    }
  }
};

const suiteActionsByKey: Record<string, GovActionSpec[]> = {
  processos: [
    {
      funcao: "atuprocreq",
      metodo: "action_compras_enviar_requisicao",
      label: "Atualiza para Requisicao",
      tone: "primary"
    },
    {
      funcao: "atuprocnad",
      metodo: "action_compras_aprovar_requisicao",
      label: "Atualiza para NAD",
      tone: "warn"
    },
    { funcao: "atuprocfase", metodo: "action_avancar_fase", label: "Atualiza Fase", tone: "neutral" }
  ],
  documento_dfd: [
    {
      funcao: "atudocapr",
      metodo: "action_aprovar",
      label: "Atualiza Documento para Aprovado",
      tone: "primary",
      allowedStates: ["rascunho", "draft"]
    },
    {
      funcao: "atudocras",
      metodo: "action_voltar_rascunho",
      label: "Atualiza Documento para Rascunho",
      tone: "warn"
    }
  ],
  compras_previsoes: [
    {
      funcao: "atuprevcat",
      metodo: "action_gerar_linhas_catalogo",
      label: "Atualiza Previsao pelo Catalogo",
      tone: "neutral"
    },
    {
      funcao: "atuprevrev",
      metodo: "action_enviar_revisao",
      label: "Atualiza Previsao para Revisao",
      tone: "primary",
      allowedStates: ["rascunho"]
    },
    {
      funcao: "atuprevapr",
      metodo: "action_aprovar",
      label: "Atualiza Previsao para Aprovado",
      tone: "primary",
      allowedStates: ["revisao"]
    },
    {
      funcao: "atuprevras",
      metodo: "action_voltar_rascunho",
      label: "Atualiza Previsao para Rascunho",
      tone: "warn"
    }
  ],
  empenhos: [
    {
      funcao: "atuneapr",
      metodo: "action_aprovar",
      label: "Atualiza NE para Aprovado",
      tone: "primary",
      allowedStates: ["rascunho"]
    },
    {
      funcao: "impne",
      metodo: "action_emitir",
      label: "Imprime/Emite NE",
      tone: "primary",
      allowedStates: ["aprovado"]
    },
    {
      funcao: "atunecan",
      metodo: "action_anular",
      label: "Atualiza NE para Anulado",
      tone: "danger",
      allowedStates: ["aprovado", "emitido"]
    }
  ],
  liquidacoes: [
    {
      funcao: "atunlat",
      metodo: "action_atestar",
      label: "Atualiza NL para Atestado",
      tone: "primary",
      allowedStates: ["rascunho"]
    },
    {
      funcao: "atunlliq",
      metodo: "action_liquidar",
      label: "Atualiza NL para Liquidado",
      tone: "primary",
      allowedStates: ["atestado"]
    },
    {
      funcao: "atunlcan",
      metodo: "action_cancelar",
      label: "Atualiza NL para Cancelado",
      tone: "danger",
      allowedStates: ["rascunho", "atestado"]
    }
  ],
  programacao_desembolso: [
    {
      funcao: "atupdcnf",
      metodo: "action_confirmar",
      label: "Atualiza PD para Confirmado",
      tone: "primary",
      allowedStates: ["rascunho"]
    },
    {
      funcao: "atupdpag",
      metodo: "action_marcar_pago",
      label: "Atualiza PD para Pago",
      tone: "warn",
      allowedStates: ["confirmado"]
    },
    {
      funcao: "atupdcan",
      metodo: "action_cancelar",
      label: "Atualiza PD para Cancelado",
      tone: "danger",
      allowedStates: ["rascunho", "confirmado"]
    }
  ],
  pagamentos: [
    {
      funcao: "atuopapr",
      metodo: "action_aprovar",
      label: "Atualiza OP para Aprovado",
      tone: "primary",
      allowedStates: ["rascunho"]
    },
    {
      funcao: "atuopenv",
      metodo: "action_enviar_banco",
      label: "Atualiza OP para Enviado",
      tone: "warn",
      allowedStates: ["aprovado"]
    },
    {
      funcao: "atuoppag",
      metodo: "action_confirmar_pagamento",
      label: "Atualiza OP para Pago",
      tone: "primary",
      allowedStates: ["aprovado", "enviado"]
    },
    { funcao: "impcnab", metodo: "action_gerar_cnab_individual", label: "Imprime/Gera CNAB", tone: "neutral" },
    {
      funcao: "atuopcan",
      metodo: "action_cancelar",
      label: "Atualiza OP para Cancelado",
      tone: "danger",
      allowedStates: ["rascunho", "aprovado", "enviado"]
    }
  ],
  conciliacao_importacoes: [
    {
      funcao: "atuconciliacao",
      metodo: "action_processar",
      label: "Atualiza Conciliacao Bancaria",
      tone: "primary",
      allowedStates: ["rascunho"]
    },
    {
      funcao: "atuconciliacaocan",
      metodo: "action_cancelar",
      label: "Atualiza Conciliacao para Cancelada",
      tone: "danger",
      allowedStates: ["processado"]
    }
  ]
};

let client: OdooClient | null = null;
const modelFieldCache = new Map<string, Set<string>>();
const PROCESS_WIZARD_MODEL = "gov.processo.wizard";
const PROCESS_WIZARD_FIELDS = ["subject", "origin_type", "process_type", "process_scope", "ug_id", "responsible_id"];
const PROCESS_FORM_FIELDS = [
  "subject",
  "origin_type",
  "process_type",
  "process_scope",
  "ug_id",
  "responsible_id",
  "prazo_resposta",
  "retroativo",
  "urgencia"
];

function getClient() {
  if (!client) {
    client = new OdooClient({
      baseUrl: env.odooBaseUrl,
      db: env.odooDb,
      user: env.odooUser,
      password: env.odooPassword,
      timeoutMs: env.odooTimeoutMs
    });
  }
  return client;
}

function resolveModel(suiteSlug: string): string | null {
  const normalized = suiteSlug.replaceAll("-", "_");
  if (normalized === "processos") {
    return env.odooProcessModel;
  }
  if (normalized === "dotacoes") {
    return env.odooDotacaoModel;
  }
  if (normalized === "execucoes") {
    return env.odooExecucaoModel;
  }
  if (normalized === "documento_dfd") {
    return env.odooDocumentModel;
  }
  if (normalized === "compras_itens") {
    return env.odooComprasItemModel;
  }
  if (normalized === "compras_catalogo") {
    return env.odooComprasCatalogoModel;
  }
  if (normalized === "compras_previsoes") {
    return env.odooComprasPrevisaoModel;
  }
  if (normalized === "empenhos") {
    return env.odooEmpenhoModel;
  }
  if (normalized === "liquidacoes") {
    return env.odooLiquidacaoModel;
  }
  if (normalized === "programacao_desembolso") {
    return env.odooPdModel;
  }
  if (normalized === "pagamentos") {
    return env.odooPagamentoModel;
  }
  if (normalized === "conciliacao_importacoes") {
    return env.odooConciliacaoImportacaoModel;
  }
  if (normalized === "conciliacao_pendencias") {
    return env.odooConciliacaoPendenciaModel;
  }
  if (normalized === "gov_base_ug") {
    return env.odooGovBaseModel;
  }
  if (normalized === "knowledge_bridge") {
    return env.odooKnowledgeBridgeModel;
  }
  if (normalized === "ai_templates") {
    return env.odooAiTemplateModel;
  }
  if (normalized === "ai_memory") {
    return env.odooAiMemoryModel;
  }
  return null;
}

function normalizeSuiteKey(suiteSlug: string) {
  return suiteSlug.replaceAll("-", "_");
}

function getSuiteSchema(suiteSlug: string): SuiteSchema {
  return suiteSchemaByKey[normalizeSuiteKey(suiteSlug)] ?? suiteSchemaByKey.processos;
}

function getSuiteActionSpecs(suiteSlug: string, rowState?: string) {
  const normalized = normalizeSuiteKey(suiteSlug);
  const specs = suiteActionsByKey[normalized] ?? [];
  const state = (rowState || "").toLowerCase();
  return specs.filter((spec) => {
    if (!spec.allowedStates || spec.allowedStates.length === 0) {
      return true;
    }
    return spec.allowedStates.map((item) => item.toLowerCase()).includes(state);
  });
}

async function getModelFields(model: string): Promise<Set<string>> {
  const cached = modelFieldCache.get(model);
  if (cached) {
    return cached;
  }

  const odoo = getClient();
  try {
    const fields = await odoo.callKw<Record<string, unknown>>({
      model,
      method: "fields_get",
      args: [[], ["string"]]
    });
    const fieldSet = new Set(Object.keys(fields));
    modelFieldCache.set(model, fieldSet);
    return fieldSet;
  } catch {
    const fallback = new Set<string>();
    modelFieldCache.set(model, fallback);
    return fallback;
  }
}

function parseMany2oneId(rawValue: unknown): number | null {
  if (typeof rawValue === "number" && Number.isFinite(rawValue) && rawValue > 0) {
    return rawValue;
  }
  if (Array.isArray(rawValue) && rawValue.length > 0) {
    const candidate = rawValue[0];
    if (typeof candidate === "number" && Number.isFinite(candidate) && candidate > 0) {
      return candidate;
    }
  }
  return null;
}

function parseMany2oneName(rawValue: unknown): string {
  if (Array.isArray(rawValue) && rawValue.length > 1 && typeof rawValue[1] === "string") {
    return rawValue[1];
  }
  return "";
}

function parseSelectionOptions(rawValue: unknown): ProcessWizardSelectionOption[] {
  if (!Array.isArray(rawValue)) {
    return [];
  }
  return rawValue
    .map((item) => {
      if (!Array.isArray(item) || item.length < 2) {
        return null;
      }
      const [value, label] = item;
      if (typeof value !== "string" || typeof label !== "string") {
        return null;
      }
      return { value, label };
    })
    .filter((item): item is ProcessWizardSelectionOption => Boolean(item));
}

function parseOptionRows(rows: GenericRecord[]): Array<{ id: number; name: string }> {
  return rows
    .map((row) => {
      const id = row.id;
      const displayName = row.display_name ?? row.name;
      if (typeof id !== "number" || !Number.isFinite(id)) {
        return null;
      }
      if (typeof displayName !== "string" || !displayName.trim()) {
        return null;
      }
      return {
        id,
        name: displayName
      };
    })
    .filter((item): item is { id: number; name: string } => Boolean(item));
}

async function fetchProcessWizardFieldMeta() {
  const odoo = getClient();
  const fields = await odoo.callKw<Record<string, ProcessWizardFieldMeta>>({
    model: PROCESS_WIZARD_MODEL,
    method: "fields_get",
    args: [
      ["origin_type", "process_type", "process_scope"],
      ["string", "selection"]
    ]
  });
  return fields;
}

async function fetchProcessWizardDefaults() {
  const odoo = getClient();
  const defaults = await odoo.callKw<Record<string, unknown>>({
    model: PROCESS_WIZARD_MODEL,
    method: "default_get",
    args: [PROCESS_WIZARD_FIELDS]
  });
  return defaults;
}

async function fetchUgOptions() {
  const odoo = getClient();
  const rows = await odoo.callKw<GenericRecord[]>({
    model: env.odooGovBaseModel,
    method: "search_read",
    args: [[], ["display_name", "name"]],
    kwargs: { limit: 200, order: "display_name asc, id asc" }
  });
  return parseOptionRows(rows);
}

async function fetchResponsibleOptions() {
  const odoo = getClient();
  const rows = await odoo.callKw<GenericRecord[]>({
    model: "res.users",
    method: "search_read",
    args: [[["active", "=", true], ["share", "=", false]], ["display_name", "name"]],
    kwargs: { limit: 200, order: "display_name asc, id asc" }
  });
  return parseOptionRows(rows);
}

function buildProcessWizardDefaults(
  defaults: Record<string, unknown>,
  selections: {
    originType: ProcessWizardSelectionOption[];
    processType: ProcessWizardSelectionOption[];
    processScope: ProcessWizardSelectionOption[];
  }
): ProcessWizardDefaults {
  const originType = (typeof defaults.origin_type === "string" && defaults.origin_type) || "";
  const processType = (typeof defaults.process_type === "string" && defaults.process_type) || "";
  const processScope = (typeof defaults.process_scope === "string" && defaults.process_scope) || "";
  return {
    subject: "Novo Processo Administrativo",
    origin_type: originType || selections.originType[0]?.value || "dfd",
    process_type: processType || selections.processType[0]?.value || "compras_servicos",
    process_scope: processScope || selections.processScope[0]?.value || "compras",
    ug_id: parseMany2oneId(defaults.ug_id),
    responsible_id: parseMany2oneId(defaults.responsible_id)
  };
}

function sanitizeProcessWizardInput(input: ProcessWizardInput, defaults: ProcessWizardDefaults) {
  const subject = (input.subject ?? defaults.subject).trim();
  if (!subject) {
    throw new OdooClientError("Assunto (subject) obrigatorio", 400);
  }

  const originType = (input.origin_type ?? defaults.origin_type).trim();
  const processType = (input.process_type ?? defaults.process_type).trim();
  const processScope = (input.process_scope ?? defaults.process_scope).trim();
  const ugId = parseMany2oneId(input.ug_id) ?? defaults.ug_id;
  const responsibleId = parseMany2oneId(input.responsible_id) ?? defaults.responsible_id;

  if (!originType) {
    throw new OdooClientError("Origem obrigatoria", 400);
  }
  if (!processType) {
    throw new OdooClientError("Tipo de processo obrigatorio", 400);
  }
  if (!processScope) {
    throw new OdooClientError("Escopo obrigatorio", 400);
  }
  if (!ugId) {
    throw new OdooClientError("UG obrigatoria", 400);
  }

  const values: Record<string, unknown> = {
    subject,
    origin_type: originType,
    process_type: processType,
    process_scope: processScope,
    ug_id: ugId
  };

  if (responsibleId) {
    values.responsible_id = responsibleId;
  }

  return values;
}

function parseTemplateIds(rawValue: unknown): number[] {
  if (!Array.isArray(rawValue)) {
    return [];
  }
  return rawValue.filter((item): item is number => typeof item === "number" && Number.isFinite(item) && item > 0);
}

async function fetchTemplateDetails(templateIds: number[]): Promise<ProcessWizardTemplate[]> {
  if (templateIds.length === 0) {
    return [];
  }
  const odoo = getClient();
  const rows = await odoo.callKw<GenericRecord[]>({
    model: env.odooAiTemplateModel,
    method: "read",
    args: [templateIds, ["name", "doc_type", "fase", "process_scope", "is_checklist"]]
  });
  return rows
    .map((row) => {
      if (typeof row.id !== "number") {
        return null;
      }
      return {
        id: row.id,
        name: typeof row.name === "string" ? row.name : `Template #${row.id}`,
        docType: typeof row.doc_type === "string" ? row.doc_type : "-",
        fase: typeof row.fase === "string" ? row.fase : "-",
        processScope: typeof row.process_scope === "string" ? row.process_scope : "-",
        isChecklist: Boolean(row.is_checklist)
      };
    })
    .filter((item): item is ProcessWizardTemplate => Boolean(item));
}

async function computeProcessWizardRecommendations(input: ProcessWizardInput, defaults: ProcessWizardDefaults) {
  const odoo = getClient();
  const values = sanitizeProcessWizardInput(input, defaults);
  const wizardId = await odoo.callKw<number>({
    model: PROCESS_WIZARD_MODEL,
    method: "create",
    args: [values]
  });
  try {
    const rows = await odoo.callKw<Array<Record<string, unknown>>>({
      model: PROCESS_WIZARD_MODEL,
      method: "read",
      args: [[wizardId], ["recommended_template_ids"]]
    });
    const templateIds = parseTemplateIds(rows[0]?.recommended_template_ids);
    return fetchTemplateDetails(templateIds);
  } finally {
    await odoo.callKw<boolean>({
      model: PROCESS_WIZARD_MODEL,
      method: "unlink",
      args: [[wizardId]]
    });
  }
}

function parseProcessWriteValues(input: ProcessUpdateInput) {
  const values: Record<string, unknown> = {};

  if (typeof input.subject === "string") {
    const subject = input.subject.trim();
    if (!subject) {
      throw new OdooClientError("Assunto (subject) nao pode ser vazio", 400);
    }
    values.subject = subject;
  }
  if (typeof input.origin_type === "string" && input.origin_type.trim()) {
    values.origin_type = input.origin_type.trim();
  }
  if (typeof input.process_type === "string" && input.process_type.trim()) {
    values.process_type = input.process_type.trim();
  }
  if (typeof input.process_scope === "string" && input.process_scope.trim()) {
    values.process_scope = input.process_scope.trim();
  }

  const ugId = parseMany2oneId(input.ug_id);
  if (ugId) {
    values.ug_id = ugId;
  }
  const responsibleId = parseMany2oneId(input.responsible_id);
  if (responsibleId) {
    values.responsible_id = responsibleId;
  }

  if (input.prazo_resposta === null) {
    values.prazo_resposta = false;
  } else if (typeof input.prazo_resposta === "string") {
    const rawDate = input.prazo_resposta.trim();
    if (!/^\d{4}-\d{2}-\d{2}$/.test(rawDate)) {
      throw new OdooClientError("prazo_resposta deve estar no formato YYYY-MM-DD", 400);
    }
    values.prazo_resposta = rawDate;
  }

  if (typeof input.retroativo === "boolean") {
    values.retroativo = input.retroativo;
  }
  if (typeof input.urgencia === "boolean") {
    values.urgencia = input.urgencia;
  }

  if (Object.keys(values).length === 0) {
    throw new OdooClientError("Nenhum campo valido para atualizar", 400);
  }

  return values;
}

function firstAvailableValue(row: GenericRecord, candidates: string[]) {
  for (const candidate of candidates) {
    const rawValue = row[candidate];
    if (rawValue === undefined || rawValue === null) {
      continue;
    }
    if (typeof rawValue === "string" && rawValue.trim()) {
      return rawValue;
    }
    if (typeof rawValue === "number" || typeof rawValue === "boolean") {
      return String(rawValue);
    }
    if (Array.isArray(rawValue) && rawValue.length >= 2 && typeof rawValue[1] === "string") {
      return rawValue[1];
    }
  }
  return "-";
}

function rowMatchesDomain(row: GenericRecord, domain: unknown[] | undefined) {
  if (!domain || domain.length === 0) {
    return true;
  }
  // Suporte minimo para filtros do tipo: [["field", "=", value]]
  return domain.every((token) => {
    if (!Array.isArray(token) || token.length < 3) {
      return true;
    }
    const [fieldName, operator, value] = token as [string, string, unknown];
    if (operator !== "=") {
      return true;
    }
    return row[fieldName] === value;
  });
}

function parseFilterValue(
  rawValue: string,
  valueType: "string" | "number" | "boolean"
): string | number | boolean | null {
  if (valueType === "string") {
    return rawValue.trim() ? rawValue.trim() : null;
  }
  if (valueType === "number") {
    const parsed = Number(rawValue);
    return Number.isFinite(parsed) ? parsed : null;
  }
  const normalized = rawValue.toLowerCase();
  if (normalized === "true" || normalized === "1") {
    return true;
  }
  if (normalized === "false" || normalized === "0") {
    return false;
  }
  return null;
}

function buildDomainFromFilters(
  schema: SuiteSchema,
  modelFields: Set<string>,
  filters: Record<string, string>
): unknown[] {
  const domain: unknown[] = [...(schema.domain ?? [])];
  if (!schema.filterRules) {
    return domain;
  }

  for (const [param, rawValue] of Object.entries(filters)) {
    if (!rawValue) {
      continue;
    }
    const rule = schema.filterRules[param];
    if (!rule) {
      continue;
    }
    if (modelFields.size > 0 && !modelFields.has(rule.field) && rule.field !== "display_name") {
      continue;
    }
    const parsed = parseFilterValue(rawValue, rule.type);
    if (parsed === null) {
      continue;
    }
    domain.push([rule.field, rule.operator, parsed]);
  }
  return domain;
}

function mapRow(row: GenericRecord, schema: SuiteSchema) {
  return {
    id: row.id,
    nome: row.display_name ?? row.name ?? `Registro #${row.id}`,
    estado: row.state ?? "-",
    destaqueLabel: schema.highlightLabel,
    destaque: firstAvailableValue(row, schema.highlightCandidates),
    criadoEm: row.create_date ?? "-",
    atualizadoEm: row.write_date ?? "-"
  };
}

export async function fetchDashboard() {
  const odoo = getClient();
  const totalProcessos = await odoo.callKw<number>({
    model: env.odooProcessModel,
    method: "search_count",
    args: [[]]
  });

  const latest = await odoo.callKw<GenericRecord[]>({
    model: env.odooProcessModel,
    method: "search_read",
    args: [[], ["display_name", "state", "create_date", "write_date"]],
    kwargs: { limit: 5, order: "id desc" }
  });

  let byState: Array<{ state: string; state_count: number }> = [];
  try {
    byState = await odoo.callKw<Array<{ state: string; state_count: number }>>({
      model: env.odooProcessModel,
      method: "read_group",
      args: [[], ["state"], ["state"]],
      kwargs: { lazy: false }
    });
  } catch {
    byState = [];
  }

  return {
    totalProcessos,
    latest: latest.map((row) => mapRow(row, suiteSchemaByKey.processos)),
    byState: byState.map((row) => ({
      state: row.state || "sem_estado",
      total: row.state_count
    }))
  };
}

export async function fetchGovList(
  suiteSlug: string,
  page: number,
  pageSize: number,
  filters: Record<string, string> = {}
) {
  const schema = getSuiteSchema(suiteSlug);
  const model = resolveModel(suiteSlug);
  if (!model) {
    return null;
  }

  const odoo = getClient();
  const modelFields = await getModelFields(model);
  const baseFields = ["display_name", "name", "state", "create_date", "write_date"];
  const requestedFields = [...baseFields, ...schema.highlightCandidates];
  const readFields = requestedFields.filter((field, index) => {
    if (index < baseFields.length) {
      return true;
    }
    return modelFields.size === 0 || modelFields.has(field);
  });

  const domain = buildDomainFromFilters(schema, modelFields, filters);
  const offset = (page - 1) * pageSize;
  const total = await odoo.callKw<number>({
    model,
    method: "search_count",
    args: [domain]
  });

  const rows = await odoo.callKw<GenericRecord[]>({
    model,
    method: "search_read",
    args: [domain, readFields],
    kwargs: { offset, limit: pageSize, order: schema.order ?? "id desc" }
  });

  return {
    page,
    pageSize,
    total,
    totalPages: Math.max(1, Math.ceil(total / pageSize)),
    items: rows.map((row) => mapRow(row, schema))
  };
}

export async function fetchGovRecord(suiteSlug: string, id: number) {
  const schema = getSuiteSchema(suiteSlug);
  const model = resolveModel(suiteSlug);
  if (!model) {
    return null;
  }

  const odoo = getClient();
  const modelFields = await getModelFields(model);
  const baseFields = ["display_name", "name", "state", "create_date", "write_date"];
  const requestedFields = [...baseFields, ...schema.highlightCandidates, ...schema.detailCandidates];
  const readFields = requestedFields.filter((field, index) => {
    if (index < baseFields.length) {
      return true;
    }
    return modelFields.size === 0 || modelFields.has(field);
  });

  const rows = await odoo.callKw<GenericRecord[]>({
    model,
    method: "read",
    args: [[id], readFields]
  });
  const row = rows[0];
  if (!row) {
    return null;
  }
  if (!rowMatchesDomain(row, schema.domain)) {
    return null;
  }

  return {
    ...mapRow(row, schema),
    resumo: "Detalhe GRP para aceleracao do frontend. Campos reais podem ser mapeados por modulo.",
    actions: getSuiteActionSpecs(suiteSlug, row.state).map((action) => ({
      funcao: action.funcao,
      label: `${action.funcao} - ${action.label}`,
      tone: action.tone ?? "neutral"
    })),
    detalhes: schema.detailCandidates
      .map((fieldName) => ({
        label: schema.fieldLabels?.[fieldName] ?? fieldName,
        value: firstAvailableValue(row, [fieldName])
      }))
      .filter((item) => item.value !== "-")
  };
}

export async function executeGovAction(suiteSlug: string, id: number, actionKey: string) {
  const model = resolveModel(suiteSlug);
  if (!model) {
    throw new OdooClientError(`Suite gov/${suiteSlug} nao encontrada`, 404);
  }

  const normalized = normalizeSuiteKey(suiteSlug);
  const actionSpec = (suiteActionsByKey[normalized] ?? []).find(
    (item) => item.funcao === actionKey || item.metodo === actionKey
  );
  if (!actionSpec) {
    throw new OdooClientError(`Acao ${actionKey} nao permitida para a suite ${normalized}`, 400);
  }

  const odoo = getClient();
  return odoo.callKw<unknown>({
    model,
    method: actionSpec.metodo,
    args: [[id]]
  });
}

async function fetchProcessoWizardBaseMeta() {
  const [fieldMeta, defaultValues, ugOptions, responsibleOptions] = await Promise.all([
    fetchProcessWizardFieldMeta(),
    fetchProcessWizardDefaults(),
    fetchUgOptions(),
    fetchResponsibleOptions()
  ]);

  const selections = {
    originType: parseSelectionOptions(fieldMeta.origin_type?.selection),
    processType: parseSelectionOptions(fieldMeta.process_type?.selection),
    processScope: parseSelectionOptions(fieldMeta.process_scope?.selection)
  };
  const defaults = buildProcessWizardDefaults(defaultValues, selections);
  if (!defaults.ug_id) {
    defaults.ug_id = ugOptions[0]?.id ?? null;
  }
  if (!defaults.responsible_id) {
    defaults.responsible_id = responsibleOptions[0]?.id ?? null;
  }

  return {
    selections,
    defaults,
    ugOptions,
    responsibleOptions
  };
}

export async function fetchProcessoWizardMeta(recordId?: number): Promise<ProcessWizardMeta & {
  record: {
    id: number | null;
    subject: string;
    origin_type: string;
    process_type: string;
    process_scope: string;
    ug_id: number | null;
    ug_name: string;
    responsible_id: number | null;
    responsible_name: string;
    prazo_resposta: string;
    retroativo: boolean;
    urgencia: boolean;
  };
}> {
  const { selections, defaults, ugOptions, responsibleOptions } = await fetchProcessoWizardBaseMeta();

  const record: {
    id: number | null;
    subject: string;
    origin_type: string;
    process_type: string;
    process_scope: string;
    ug_id: number | null;
    ug_name: string;
    responsible_id: number | null;
    responsible_name: string;
    prazo_resposta: string;
    retroativo: boolean;
    urgencia: boolean;
  } = {
    id: null,
    subject: defaults.subject,
    origin_type: defaults.origin_type,
    process_type: defaults.process_type,
    process_scope: defaults.process_scope,
    ug_id: defaults.ug_id,
    ug_name: "",
    responsible_id: defaults.responsible_id,
    responsible_name: "",
    prazo_resposta: "",
    retroativo: false,
    urgencia: false
  };

  if (record.ug_id) {
    record.ug_name = ugOptions.find((item) => item.id === record.ug_id)?.name ?? "";
  }
  if (record.responsible_id) {
    record.responsible_name = responsibleOptions.find((item) => item.id === record.responsible_id)?.name ?? "";
  }

  if (recordId && recordId > 0) {
    const odoo = getClient();
    const rows = await odoo.callKw<Array<Record<string, unknown>>>({
      model: env.odooProcessModel,
      method: "read",
      args: [[recordId], PROCESS_FORM_FIELDS]
    });
    const source = rows[0];
    if (!source) {
      throw new OdooClientError(`Processo ${recordId} nao encontrado`, 404);
    }
    record.id = recordId;
    record.subject = typeof source.subject === "string" && source.subject.trim() ? source.subject : defaults.subject;
    record.origin_type =
      (typeof source.origin_type === "string" && source.origin_type.trim()) || defaults.origin_type;
    record.process_type =
      (typeof source.process_type === "string" && source.process_type.trim()) || defaults.process_type;
    record.process_scope =
      (typeof source.process_scope === "string" && source.process_scope.trim()) || defaults.process_scope;
    record.ug_id = parseMany2oneId(source.ug_id);
    record.ug_name = parseMany2oneName(source.ug_id);
    record.responsible_id = parseMany2oneId(source.responsible_id);
    record.responsible_name = parseMany2oneName(source.responsible_id);
    record.prazo_resposta = typeof source.prazo_resposta === "string" ? source.prazo_resposta : "";
    record.retroativo = Boolean(source.retroativo);
    record.urgencia = Boolean(source.urgencia);
  }

  let recommendedTemplates: ProcessWizardTemplate[] = [];
  try {
    recommendedTemplates = await computeProcessWizardRecommendations(
      {
        subject: record.subject,
        origin_type: record.origin_type,
        process_type: record.process_type,
        process_scope: record.process_scope,
        ug_id: record.ug_id,
        responsible_id: record.responsible_id
      },
      defaults
    );
  } catch {
    recommendedTemplates = [];
  }

  return {
    selections,
    ugOptions,
    responsibleOptions,
    defaults,
    recommendedTemplates,
    record
  };
}

export async function previewProcessoWizardTemplates(input: ProcessWizardInput) {
  const meta = await fetchProcessoWizardBaseMeta();
  return computeProcessWizardRecommendations(input, meta.defaults);
}

export async function createProcessoViaWizard(input: ProcessWizardInput) {
  const meta = await fetchProcessoWizardBaseMeta();
  const values = sanitizeProcessWizardInput(input, meta.defaults);
  const odoo = getClient();
  const wizardId = await odoo.callKw<number>({
    model: PROCESS_WIZARD_MODEL,
    method: "create",
    args: [values]
  });

  try {
    const action = await odoo.callKw<Record<string, unknown>>({
      model: PROCESS_WIZARD_MODEL,
      method: "action_criar_processo",
      args: [[wizardId]]
    });
    const processId = typeof action.res_id === "number" ? action.res_id : null;
    if (!processId) {
      throw new OdooClientError("Nao foi possivel identificar o processo criado", 500);
    }
    const record = await detgov("processos", processId);
    const wizardRows = await odoo.callKw<Array<Record<string, unknown>>>({
      model: PROCESS_WIZARD_MODEL,
      method: "read",
      args: [[wizardId], ["recommended_template_ids"]]
    });
    const recommendedTemplates = await fetchTemplateDetails(parseTemplateIds(wizardRows[0]?.recommended_template_ids));
    return {
      id: processId,
      record,
      recommendedTemplates
    };
  } finally {
    await odoo.callKw<boolean>({
      model: PROCESS_WIZARD_MODEL,
      method: "unlink",
      args: [[wizardId]]
    });
  }
}

export async function updateProcessoRecord(id: number, input: ProcessUpdateInput) {
  if (!Number.isFinite(id) || id <= 0) {
    throw new OdooClientError("ID invalido", 400);
  }
  const values = parseProcessWriteValues(input);
  const odoo = getClient();
  await odoo.callKw<boolean>({
    model: env.odooProcessModel,
    method: "write",
    args: [[id], values]
  });
  const record = await detgov("processos", id);
  const form = await fetchProcessoWizardMeta(id);
  return {
    id,
    record,
    form
  };
}

// Convencoes mnemônicas GRP
export async function lisgov(
  suiteSlug: string,
  page: number,
  pageSize: number,
  filters: Record<string, string> = {}
) {
  return fetchGovList(suiteSlug, page, pageSize, filters);
}

export async function detgov(suiteSlug: string, id: number) {
  return fetchGovRecord(suiteSlug, id);
}

export async function atugov(suiteSlug: string, id: number, funcao: string) {
  return executeGovAction(suiteSlug, id, funcao);
}

export async function lispd(page: number, pageSize: number, filters: Record<string, string> = {}) {
  return fetchGovList("programacao-desembolso", page, pageSize, filters);
}

export async function lisevento(page: number, pageSize: number, filters: Record<string, string> = {}) {
  return fetchGovList("conciliacao-pendencias", page, pageSize, filters);
}
