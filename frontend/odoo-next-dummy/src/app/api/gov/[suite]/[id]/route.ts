import { jsonError, jsonOk } from "@/lib/api-response";
import { OdooClientError } from "@/lib/errors";
import { atugov, detgov, updateProcessoRecord } from "@/lib/server/odoo-service";

export const runtime = "nodejs";

type RouteContext = {
  params: Promise<{ suite: string; id: string }>;
};

export async function GET(_request: Request, context: RouteContext) {
  try {
    const params = await context.params;
    const id = Number.parseInt(params.id, 10);
    if (Number.isNaN(id) || id <= 0) {
      return jsonError("ID invalido", 400);
    }

    const data = await detgov(params.suite, id);
    if (!data) {
      return jsonError(`Registro gov/${params.suite}/${id} nao encontrado`, 404);
    }
    return jsonOk(data);
  } catch (error) {
    if (error instanceof OdooClientError) {
      return jsonError(error.message, error.status, error.payload);
    }
    return jsonError("Falha ao obter detalhe da suite gov");
  }
}

export async function POST(request: Request, context: RouteContext) {
  try {
    const params = await context.params;
    const id = Number.parseInt(params.id, 10);
    if (Number.isNaN(id) || id <= 0) {
      return jsonError("ID invalido", 400);
    }

    let payload: { action?: string; funcao?: string; acao?: string } | null = null;
    try {
      payload = (await request.json()) as { action?: string; funcao?: string; acao?: string } | null;
    } catch {
      return jsonError("Body JSON invalido", 400);
    }
    const funcao = payload?.funcao?.trim() || payload?.acao?.trim() || payload?.action?.trim();
    if (!funcao) {
      return jsonError("Funcao obrigatoria", 400);
    }

    const result = await atugov(params.suite, id, funcao);
    const record = await detgov(params.suite, id);
    return jsonOk({
      ok: true,
      funcao,
      result,
      record
    });
  } catch (error) {
    if (error instanceof OdooClientError) {
      return jsonError(error.message, error.status, error.payload);
    }
    return jsonError("Falha ao executar acao da suite gov");
  }
}

type UpdateProcessPayload = {
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

export async function PATCH(request: Request, context: RouteContext) {
  try {
    const params = await context.params;
    const suite = params.suite.replaceAll("-", "_");
    if (suite !== "processos") {
      return jsonError("Edicao disponivel apenas para gov/processos", 405);
    }

    const id = Number.parseInt(params.id, 10);
    if (Number.isNaN(id) || id <= 0) {
      return jsonError("ID invalido", 400);
    }

    let payload: UpdateProcessPayload | null = null;
    try {
      payload = (await request.json()) as UpdateProcessPayload | null;
    } catch {
      return jsonError("Body JSON invalido", 400);
    }

    const updated = await updateProcessoRecord(id, payload ?? {});
    return jsonOk({
      ok: true,
      id,
      record: updated.record,
      form: updated.form
    });
  } catch (error) {
    if (error instanceof OdooClientError) {
      return jsonError(error.message, error.status, error.payload);
    }
    return jsonError("Falha ao atualizar processo");
  }
}
