import { env } from "@/lib/env";
import { OdooClient } from "@/lib/odoo-client";

type ProcessoRecord = {
  id: number;
  display_name?: string;
  create_date?: string;
  write_date?: string;
};

type DocumentoRecord = ProcessoRecord & {
  name?: string;
};

let client: OdooClient | null = null;

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

export async function fetchDashboard() {
  const odoo = getClient();
  const totalProcessos = await odoo.callKw<number>({
    model: env.odooProcessModel,
    method: "search_count",
    args: [[]]
  });

  const latest = await odoo.callKw<ProcessoRecord[]>({
    model: env.odooProcessModel,
    method: "search_read",
    args: [[], ["display_name", "create_date", "write_date"]],
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
    latest: latest.map((row) => ({
      id: row.id,
      nome: row.display_name ?? `Registro #${row.id}`,
      atualizadoEm: row.write_date ?? row.create_date ?? "-"
    })),
    byState: byState.map((row) => ({
      state: row.state || "sem_estado",
      total: row.state_count
    }))
  };
}

export async function fetchProcessos(page: number, pageSize: number) {
  const odoo = getClient();
  const offset = (page - 1) * pageSize;
  const total = await odoo.callKw<number>({
    model: env.odooProcessModel,
    method: "search_count",
    args: [[]]
  });

  const rows = await odoo.callKw<ProcessoRecord[]>({
    model: env.odooProcessModel,
    method: "search_read",
    args: [[], ["display_name", "create_date", "write_date"]],
    kwargs: { offset, limit: pageSize, order: "id desc" }
  });

  return {
    page,
    pageSize,
    total,
    totalPages: Math.max(1, Math.ceil(total / pageSize)),
    items: rows.map((row) => ({
      id: row.id,
      nome: row.display_name ?? `Registro #${row.id}`,
      criadoEm: row.create_date ?? "-",
      atualizadoEm: row.write_date ?? "-"
    }))
  };
}

export async function fetchDocumentoDfd(id: number) {
  const odoo = getClient();
  const rows = await odoo.callKw<DocumentoRecord[]>({
    model: env.odooDocumentModel,
    method: "read",
    args: [[id], ["display_name", "create_date", "write_date", "name"]]
  });
  const record = rows[0];
  if (!record) {
    return null;
  }

  return {
    id: record.id,
    titulo: record.display_name ?? record.name ?? `Documento #${id}`,
    criadoEm: record.create_date ?? "-",
    atualizadoEm: record.write_date ?? "-",
    resumo: "Documento carregado via API do Odoo. Abas abaixo sao de demonstracao."
  };
}
