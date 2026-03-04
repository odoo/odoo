import { env } from "@/lib/env";
import { getGovSuiteBySlug } from "@/lib/gov-suite";
import { OdooClient } from "@/lib/odoo-client";

type GenericRecord = {
  id: number;
  display_name?: string;
  name?: string;
  state?: string;
  create_date?: string;
  write_date?: string;
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

function resolveModel(suiteSlug: string): string | null {
  const suite = getGovSuiteBySlug(suiteSlug);
  return suite?.model ?? null;
}

function mapRow(row: GenericRecord) {
  return {
    id: row.id,
    nome: row.display_name ?? row.name ?? `Registro #${row.id}`,
    estado: row.state ?? "-",
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

  return {
    totalProcessos,
    latest: latest.map(mapRow)
  };
}

export async function fetchGovList(suiteSlug: string, page: number, pageSize: number) {
  const model = resolveModel(suiteSlug);
  if (!model) {
    return null;
  }

  const odoo = getClient();
  const offset = (page - 1) * pageSize;
  const total = await odoo.callKw<number>({
    model,
    method: "search_count",
    args: [[]]
  });

  const rows = await odoo.callKw<GenericRecord[]>({
    model,
    method: "search_read",
    args: [[], ["display_name", "name", "state", "create_date", "write_date"]],
    kwargs: { offset, limit: pageSize, order: "id desc" }
  });

  return {
    page,
    pageSize,
    total,
    totalPages: Math.max(1, Math.ceil(total / pageSize)),
    items: rows.map(mapRow)
  };
}

export async function fetchGovRecord(suiteSlug: string, id: number) {
  const model = resolveModel(suiteSlug);
  if (!model) {
    return null;
  }

  const odoo = getClient();
  const rows = await odoo.callKw<GenericRecord[]>({
    model,
    method: "read",
    args: [[id], ["display_name", "name", "state", "create_date", "write_date"]]
  });
  const row = rows[0];
  if (!row) {
    return null;
  }

  return {
    ...mapRow(row),
    resumo: "Detalhe dummy para aceleracao do frontend. Campos reais podem ser mapeados por modulo."
  };
}
