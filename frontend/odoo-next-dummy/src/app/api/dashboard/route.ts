import { jsonError, jsonOk } from "@/lib/api-response";
import { OdooClientError } from "@/lib/errors";
import { fetchDashboard } from "@/lib/server/odoo-service";

export const runtime = "nodejs";

export async function GET() {
  try {
    const data = await fetchDashboard();
    return jsonOk(data);
  } catch (error) {
    if (error instanceof OdooClientError) {
      return jsonError(error.message, error.status, error.payload);
    }
    return jsonError("Falha ao obter dashboard do Odoo");
  }
}
