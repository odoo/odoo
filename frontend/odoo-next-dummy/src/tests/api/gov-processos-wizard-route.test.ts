import { beforeEach, describe, expect, it, vi } from "vitest";

const fetchProcessoWizardMetaMock = vi.fn();
const previewProcessoWizardTemplatesMock = vi.fn();

vi.mock("@/lib/server/odoo-service", () => ({
  fetchProcessoWizardMeta: (...args: unknown[]) => fetchProcessoWizardMetaMock(...args),
  previewProcessoWizardTemplates: (...args: unknown[]) => previewProcessoWizardTemplatesMock(...args)
}));

import { GET, POST } from "@/app/api/gov/processos/wizard/route";

describe("GET/POST /api/gov/processos/wizard", () => {
  beforeEach(() => {
    fetchProcessoWizardMetaMock.mockReset();
    previewProcessoWizardTemplatesMock.mockReset();
  });

  it("GET retorna metadados do wizard", async () => {
    fetchProcessoWizardMetaMock.mockResolvedValue({ record: { id: null }, recommendedTemplates: [] });

    const response = await GET(new Request("http://localhost/api/gov/processos/wizard"));
    const payload = await response.json();

    expect(response.status).toBe(200);
    expect(payload.record.id).toBeNull();
    expect(fetchProcessoWizardMetaMock).toHaveBeenCalledWith(undefined);
  });

  it("POST retorna recomendacoes dinamicas", async () => {
    previewProcessoWizardTemplatesMock.mockResolvedValue([{ id: 1, name: "Template A" }]);

    const response = await POST(
      new Request("http://localhost/api/gov/processos/wizard", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ process_type: "compras_servicos", process_scope: "compras", ug_id: 1 })
      })
    );
    const payload = await response.json();

    expect(response.status).toBe(200);
    expect(payload.recommendedTemplates).toHaveLength(1);
    expect(previewProcessoWizardTemplatesMock).toHaveBeenCalledWith({
      process_type: "compras_servicos",
      process_scope: "compras",
      ug_id: 1
    });
  });
});
