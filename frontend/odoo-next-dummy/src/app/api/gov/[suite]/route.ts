import { jsonError, jsonOk } from "@/lib/api-response";
import { OdooClientError } from "@/lib/errors";
import { lisgov } from "@/lib/server/odoo-service";

export const runtime = "nodejs";

type RouteContext = {
  params: Promise<{ suite: string }>;
};

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

export async function GET(request: Request, context: RouteContext) {
  try {
    const params = await context.params;
    const url = new URL(request.url);
    const page = parsePositiveInt(url.searchParams.get("page"), 1);
    const pageSize = parsePositiveInt(url.searchParams.get("pageSize"), 10);
    const filters = Object.fromEntries(
      [...url.searchParams.entries()].filter(([key, value]) => key !== "page" && key !== "pageSize" && value !== "")
    );
    const data = await lisgov(params.suite, page, Math.min(pageSize, 100), filters);

    if (!data) {
      return jsonError(`Suite gov/${params.suite} nao encontrada`, 404);
    }
    return jsonOk(data);
  } catch (error) {
    if (error instanceof OdooClientError) {
      return jsonError(error.message, error.status, error.payload);
    }
    return jsonError("Falha ao obter lista da suite gov");
  }
}
