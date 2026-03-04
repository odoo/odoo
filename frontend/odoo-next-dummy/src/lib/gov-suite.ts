import { env } from "@/lib/env";

export type GovSuiteKey =
  | "processos"
  | "dotacoes"
  | "execucoes"
  | "documento_dfd"
  | "ai_templates"
  | "ai_memory";

export type GovSuiteConfig = {
  key: GovSuiteKey;
  label: string;
  path: string;
  model: string;
  detailPath: (id: number) => string;
};

export const govSuiteConfig: Record<GovSuiteKey, GovSuiteConfig> = {
  processos: {
    key: "processos",
    label: "Processos",
    path: "/gov/processos",
    model: env.odooProcessModel,
    detailPath: (id) => `/gov/processos/${id}`
  },
  dotacoes: {
    key: "dotacoes",
    label: "Dotacoes",
    path: "/gov/dotacoes",
    model: env.odooDotacaoModel,
    detailPath: (id) => `/gov/dotacoes/${id}`
  },
  execucoes: {
    key: "execucoes",
    label: "Execucoes",
    path: "/gov/execucoes",
    model: env.odooExecucaoModel,
    detailPath: (id) => `/gov/execucoes/${id}`
  },
  documento_dfd: {
    key: "documento_dfd",
    label: "Documento DFD",
    path: "/gov/documento-dfd",
    model: env.odooDocumentModel,
    detailPath: (id) => `/gov/documento-dfd/${id}`
  },
  ai_templates: {
    key: "ai_templates",
    label: "AI Templates",
    path: "/gov/ai-templates",
    model: env.odooAiTemplateModel,
    detailPath: (id) => `/gov/ai-templates/${id}`
  },
  ai_memory: {
    key: "ai_memory",
    label: "AI Memory",
    path: "/gov/ai-memory",
    model: env.odooAiMemoryModel,
    detailPath: (id) => `/gov/ai-memory/${id}`
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
