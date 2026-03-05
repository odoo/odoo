import { jsonError, jsonOk } from "@/lib/api-response";
import { OdooClientError } from "@/lib/errors";
import { createProcessoViaWizard, lisgov } from "@/lib/server/odoo-service";

export const runtime = "nodejs";

function parsePositiveInt(value: string | null, fallback: number) {
  if (!value) {
    return fallback;
  }
  const parsed = Number.parseInt(value, 10);
  if (Number.isNaN(parsed) || parsed <= 0) {
    return fallback;
  }
  return parsed;
}

type CreateProcessoBody = {
  subject?: string;
  origin_type?: string;
  process_type?: string;
  process_scope?: string;
  ug_id?: number | null;
  responsible_id?: number | null;
};

export async function GET(request: Request) {
  try {
    const url = new URL(request.url);
    const page = parsePositiveInt(url.searchParams.get("page"), 1);
    const pageSize = parsePositiveInt(url.searchParams.get("pageSize"), 10);
    const filters = Object.fromEntries(
      [...url.searchParams.entries()].filter(([key, value]) => key !== "page" && key !== "pageSize" && value !== "")
    );

    const data = await lisgov("processos", page, Math.min(pageSize, 100), filters);
    if (!data) {
      return jsonError("Suite gov/processos nao configurada", 404);
    }
    return jsonOk(data);
  } catch (error) {
    if (error instanceof OdooClientError) {
      return jsonError(error.message, error.status, error.payload);
    }
    return jsonError("Falha ao obter lista de processos");
  }
}

export async function POST(request: Request) {
  try {
    let payload: CreateProcessoBody | null = null;
    try {
      payload = (await request.json()) as CreateProcessoBody;
    } catch {
      return jsonError("Body JSON invalido", 400);
    }

    const created = await createProcessoViaWizard(payload ?? {});
    return jsonOk(
      {
        ok: true,
        id: created.id,
        record: created.record,
        recommendedTemplates: created.recommendedTemplates
      },
      201
    );
  } catch (error) {
    if (error instanceof OdooClientError) {
      return jsonError(error.message, error.status, error.payload);
    }
    return jsonError("Falha ao criar processo via wizard");
  }
}
