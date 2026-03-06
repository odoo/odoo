import { jsonError, jsonOk } from "@/lib/api-response";
import { OdooClientError } from "@/lib/errors";
import { fetchProcessoWizardMeta, previewProcessoWizardTemplates } from "@/lib/server/odoo-service";

export const runtime = "nodejs";

type PreviewBody = {
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
    const recordIdRaw = url.searchParams.get("recordId");
    const recordId = recordIdRaw ? Number.parseInt(recordIdRaw, 10) : undefined;
    if (recordIdRaw && (Number.isNaN(recordId) || (recordId ?? 0) <= 0)) {
      return jsonError("recordId invalido", 400);
    }

    const meta = await fetchProcessoWizardMeta(recordId);
    return jsonOk(meta);
  } catch (error) {
    if (error instanceof OdooClientError) {
      return jsonError(error.message, error.status, error.payload);
    }
    return jsonError("Falha ao carregar metadados do wizard de processos");
  }
}

export async function POST(request: Request) {
  try {
    let payload: PreviewBody | null = null;
    try {
      payload = (await request.json()) as PreviewBody;
    } catch {
      return jsonError("Body JSON invalido", 400);
    }

    const recommendedTemplates = await previewProcessoWizardTemplates(payload ?? {});
    return jsonOk({ recommendedTemplates });
  } catch (error) {
    if (error instanceof OdooClientError) {
      return jsonError(error.message, error.status, error.payload);
    }
    return jsonError("Falha ao gerar recomendacoes do wizard");
  }
}
