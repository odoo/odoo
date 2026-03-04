import { jsonError, jsonOk } from "@/lib/api-response";
import { OdooClientError } from "@/lib/errors";
import { fetchGovRecord } from "@/lib/server/odoo-service";

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

    const data = await fetchGovRecord(params.suite, id);
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
