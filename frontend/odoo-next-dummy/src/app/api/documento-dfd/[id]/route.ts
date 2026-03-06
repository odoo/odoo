import { jsonError, jsonOk } from "@/lib/api-response";
import { OdooClientError } from "@/lib/errors";
import { fetchGovRecord } from "@/lib/server/odoo-service";

export const runtime = "nodejs";

type RouteContext = {
  params: Promise<{ id: string }>;
};

export async function GET(_request: Request, context: RouteContext) {
  try {
    const params = await context.params;
    const id = Number.parseInt(params.id, 10);
    if (Number.isNaN(id) || id <= 0) {
      return jsonError("ID invalido", 400);
    }

    const data = await fetchGovRecord("documento_dfd", id);
    if (!data) {
      return jsonError("Documento nao encontrado", 404);
    }
    return jsonOk({
      id: data.id,
      titulo: data.nome,
      criadoEm: data.criadoEm,
      atualizadoEm: data.atualizadoEm,
      resumo: data.resumo
    });
  } catch (error) {
    if (error instanceof OdooClientError) {
      return jsonError(error.message, error.status, error.payload);
    }
    return jsonError("Falha ao obter documento DFD");
  }
}
