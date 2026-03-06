export type GovSuiteKey =
  | "processos"
  | "dotacoes"
  | "execucoes"
  | "documento_dfd"
  | "compras_itens"
  | "compras_catalogo"
  | "compras_previsoes"
  | "empenhos"
  | "liquidacoes"
  | "programacao_desembolso"
  | "pagamentos"
  | "conciliacao_importacoes"
  | "conciliacao_pendencias"
  | "gov_base_ug"
  | "knowledge_bridge"
  | "ai_templates"
  | "ai_memory";

export type GovSuiteConfig = {
  key: GovSuiteKey;
  label: string;
  path: string;
  detailPath: (id: number) => string;
  filters?: Array<{
    param: string;
    label: string;
    kind: "text" | "number" | "select";
    options?: Array<{ value: string; label: string }>;
  }>;
};

export const govSuiteConfig: Record<GovSuiteKey, GovSuiteConfig> = {
  processos: {
    key: "processos",
    label: "Processos",
    path: "/gov/processos",
    detailPath: (id) => `/gov/processos/${id}`,
    filters: [
      { param: "q", label: "Busca", kind: "text" },
      { param: "state", label: "Estado", kind: "text" },
      { param: "process_type", label: "Tipo", kind: "text" }
    ]
  },
  dotacoes: {
    key: "dotacoes",
    label: "Dotacoes",
    path: "/gov/dotacoes",
    detailPath: (id) => `/gov/dotacoes/${id}`,
    filters: [
      { param: "q", label: "Busca", kind: "text" },
      { param: "exercicio", label: "Exercicio", kind: "number" },
      {
        param: "reservado",
        label: "Reservado",
        kind: "select",
        options: [
          { value: "", label: "Todos" },
          { value: "true", label: "Sim" },
          { value: "false", label: "Nao" }
        ]
      }
    ]
  },
  execucoes: {
    key: "execucoes",
    label: "Execucoes",
    path: "/gov/execucoes",
    detailPath: (id) => `/gov/execucoes/${id}`,
    filters: [
      { param: "q", label: "Busca", kind: "text" },
      { param: "action", label: "Acao", kind: "text" }
    ]
  },
  documento_dfd: {
    key: "documento_dfd",
    label: "Documento DFD",
    path: "/gov/documento-dfd",
    detailPath: (id) => `/gov/documento-dfd/${id}`,
    filters: [
      { param: "q", label: "Busca", kind: "text" },
      { param: "state", label: "Estado", kind: "text" },
      { param: "process_type", label: "Tipo", kind: "text" }
    ]
  },
  compras_itens: {
    key: "compras_itens",
    label: "Compras - Itens",
    path: "/gov/compras-itens",
    detailPath: (id) => `/gov/compras-itens/${id}`,
    filters: [
      { param: "q", label: "Busca", kind: "text" },
      { param: "status", label: "Etapa", kind: "text" },
      { param: "fornecedor_arrematado", label: "Fornecedor", kind: "text" }
    ]
  },
  compras_catalogo: {
    key: "compras_catalogo",
    label: "Compras - Catalogo",
    path: "/gov/compras-catalogo",
    detailPath: (id) => `/gov/compras-catalogo/${id}`,
    filters: [
      { param: "q", label: "Busca", kind: "text" },
      { param: "categoria", label: "Categoria", kind: "text" },
      {
        param: "ativo_previsao",
        label: "Ativo Previsao",
        kind: "select",
        options: [
          { value: "", label: "Todos" },
          { value: "true", label: "Sim" },
          { value: "false", label: "Nao" }
        ]
      }
    ]
  },
  compras_previsoes: {
    key: "compras_previsoes",
    label: "Compras - Previsoes",
    path: "/gov/compras-previsoes",
    detailPath: (id) => `/gov/compras-previsoes/${id}`,
    filters: [
      { param: "q", label: "Busca", kind: "text" },
      { param: "ano", label: "Ano", kind: "number" },
      { param: "state", label: "Estado", kind: "text" }
    ]
  },
  empenhos: {
    key: "empenhos",
    label: "Empenhos",
    path: "/gov/empenhos",
    detailPath: (id) => `/gov/empenhos/${id}`,
    filters: [
      { param: "q", label: "Busca", kind: "text" },
      { param: "state", label: "Estado", kind: "text" }
    ]
  },
  liquidacoes: {
    key: "liquidacoes",
    label: "Liquidacoes",
    path: "/gov/liquidacoes",
    detailPath: (id) => `/gov/liquidacoes/${id}`,
    filters: [
      { param: "q", label: "Busca", kind: "text" },
      { param: "state", label: "Estado", kind: "text" }
    ]
  },
  programacao_desembolso: {
    key: "programacao_desembolso",
    label: "Programacao de Desembolso",
    path: "/gov/programacao-desembolso",
    detailPath: (id) => `/gov/programacao-desembolso/${id}`,
    filters: [
      { param: "q", label: "Busca", kind: "text" },
      { param: "state", label: "Estado", kind: "text" }
    ]
  },
  pagamentos: {
    key: "pagamentos",
    label: "Pagamentos",
    path: "/gov/pagamentos",
    detailPath: (id) => `/gov/pagamentos/${id}`,
    filters: [
      { param: "q", label: "Busca", kind: "text" },
      { param: "state", label: "Estado", kind: "text" }
    ]
  },
  conciliacao_importacoes: {
    key: "conciliacao_importacoes",
    label: "Conciliacao - Importacoes",
    path: "/gov/conciliacao-importacoes",
    detailPath: (id) => `/gov/conciliacao-importacoes/${id}`,
    filters: [
      { param: "q", label: "Busca", kind: "text" },
      { param: "state", label: "Estado", kind: "text" }
    ]
  },
  conciliacao_pendencias: {
    key: "conciliacao_pendencias",
    label: "Conciliacao - Pendencias",
    path: "/gov/conciliacao-pendencias",
    detailPath: (id) => `/gov/conciliacao-pendencias/${id}`,
    filters: [
      { param: "q", label: "Busca", kind: "text" },
      { param: "state", label: "Estado", kind: "text" },
      { param: "tipo", label: "Tipo", kind: "text" }
    ]
  },
  gov_base_ug: {
    key: "gov_base_ug",
    label: "Gov Base - UGs",
    path: "/gov/gov-base-ug",
    detailPath: (id) => `/gov/gov-base-ug/${id}`,
    filters: [
      { param: "q", label: "Busca", kind: "text" },
      { param: "codigo_ug", label: "Codigo UG", kind: "text" },
      { param: "codigo_siafi", label: "Codigo SIAFI", kind: "text" }
    ]
  },
  knowledge_bridge: {
    key: "knowledge_bridge",
    label: "Knowledge Bridge",
    path: "/gov/knowledge-bridge",
    detailPath: (id) => `/gov/knowledge-bridge/${id}`,
    filters: [{ param: "q", label: "Busca", kind: "text" }]
  },
  ai_templates: {
    key: "ai_templates",
    label: "AI Templates",
    path: "/gov/ai-templates",
    detailPath: (id) => `/gov/ai-templates/${id}`,
    filters: [
      { param: "q", label: "Busca", kind: "text" },
      { param: "doc_type", label: "Tipo Doc", kind: "text" },
      {
        param: "active",
        label: "Ativo",
        kind: "select",
        options: [
          { value: "", label: "Todos" },
          { value: "true", label: "Sim" },
          { value: "false", label: "Nao" }
        ]
      }
    ]
  },
  ai_memory: {
    key: "ai_memory",
    label: "AI Memory",
    path: "/gov/ai-memory",
    detailPath: (id) => `/gov/ai-memory/${id}`,
    filters: [
      { param: "q", label: "Busca", kind: "text" },
      { param: "source_type", label: "Tipo Origem", kind: "text" },
      {
        param: "active",
        label: "Ativo",
        kind: "select",
        options: [
          { value: "", label: "Todos" },
          { value: "true", label: "Sim" },
          { value: "false", label: "Nao" }
        ]
      }
    ]
  }
};

export const govSuiteList = Object.values(govSuiteConfig);

export function getGovSuiteByPath(pathname: string): GovSuiteConfig | null {
  return govSuiteList.find((entry) => pathname.startsWith(entry.path)) ?? null;
}

export function getGovSuiteBySlug(slug: string): GovSuiteConfig | null {
  const normalized = slug.replaceAll("-", "_");
  return govSuiteList.find((entry) => entry.key === normalized) ?? null;
}
