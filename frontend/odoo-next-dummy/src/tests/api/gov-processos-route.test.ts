import { beforeEach, describe, expect, it, vi } from "vitest";

const lisgovMock = vi.fn();
const createProcessoViaWizardMock = vi.fn();

vi.mock("@/lib/server/odoo-service", () => ({
  lisgov: (...args: unknown[]) => lisgovMock(...args),
  createProcessoViaWizard: (...args: unknown[]) => createProcessoViaWizardMock(...args)
}));

import { GET, POST } from "@/app/api/gov/processos/route";

describe("GET/POST /api/gov/processos", () => {
  beforeEach(() => {
    lisgovMock.mockReset();
    createProcessoViaWizardMock.mockReset();
  });

  it("GET retorna lista de processos", async () => {
    lisgovMock.mockResolvedValue({
      page: 1,
      pageSize: 10,
      total: 1,
      totalPages: 1,
      items: [{ id: 10, nome: "PROC-10", estado: "demanda" }]
    });

    const response = await GET(new Request("http://localhost/api/gov/processos?page=1&pageSize=10"));
    const payload = await response.json();

    expect(response.status).toBe(200);
    expect(payload.total).toBe(1);
    expect(lisgovMock).toHaveBeenCalledWith("processos", 1, 10, {});
  });

  it("POST cria processo via wizard", async () => {
    createProcessoViaWizardMock.mockResolvedValue({
      id: 99,
      record: { id: 99, nome: "PROC-99" },
      recommendedTemplates: []
    });

    const response = await POST(
      new Request("http://localhost/api/gov/processos", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ subject: "Aquisicao de material" })
      })
    );
    const payload = await response.json();

    expect(response.status).toBe(201);
    expect(payload.id).toBe(99);
    expect(createProcessoViaWizardMock).toHaveBeenCalledWith({ subject: "Aquisicao de material" });
  });
});
