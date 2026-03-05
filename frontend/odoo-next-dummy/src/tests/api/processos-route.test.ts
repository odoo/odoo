import { beforeEach, describe, expect, it, vi } from "vitest";

const lisgovMock = vi.fn();

vi.mock("@/lib/server/odoo-service", () => ({
  lisgov: (...args: unknown[]) => lisgovMock(...args)
}));

import { GET } from "@/app/api/processos/route";

describe("GET /api/processos", () => {
  beforeEach(() => {
    lisgovMock.mockReset();
  });

  it("retorna payload paginado", async () => {
    lisgovMock.mockResolvedValue({
      page: 2,
      pageSize: 5,
      total: 11,
      totalPages: 3,
      items: [{ id: 1, nome: "Proc A", criadoEm: "-", atualizadoEm: "-" }]
    });

    const response = await GET(new Request("http://localhost/api/processos?page=2&pageSize=5"));
    const payload = await response.json();

    expect(response.status).toBe(200);
    expect(payload.totalPages).toBe(3);
    expect(lisgovMock).toHaveBeenCalledWith("processos", 2, 5);
  });
});
