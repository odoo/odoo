import { beforeEach, describe, expect, it, vi } from "vitest";

const detgovMock = vi.fn();
const atugovMock = vi.fn();
const updateProcessoRecordMock = vi.fn();

vi.mock("@/lib/server/odoo-service", () => ({
  detgov: (...args: unknown[]) => detgovMock(...args),
  atugov: (...args: unknown[]) => atugovMock(...args),
  updateProcessoRecord: (...args: unknown[]) => updateProcessoRecordMock(...args)
}));

import { GET, PATCH, POST } from "@/app/api/gov/[suite]/[id]/route";

describe("GET/POST /api/gov/[suite]/[id]", () => {
  beforeEach(() => {
    detgovMock.mockReset();
    atugovMock.mockReset();
    updateProcessoRecordMock.mockReset();
  });

  it("GET retorna detalhe do registro", async () => {
    detgovMock.mockResolvedValue({
      id: 10,
      nome: "PROC-2026-00010",
      estado: "rascunho"
    });

    const response = await GET(
      new Request("http://localhost/api/gov/processos/10"),
      { params: Promise.resolve({ suite: "processos", id: "10" }) }
    );
    const payload = await response.json();

    expect(response.status).toBe(200);
    expect(payload.id).toBe(10);
    expect(detgovMock).toHaveBeenCalledWith("processos", 10);
  });

  it("POST executa acao e retorna registro atualizado", async () => {
    atugovMock.mockResolvedValue({ ok: true });
    detgovMock.mockResolvedValue({
      id: 22,
      nome: "NE-00022",
      estado: "emitido"
    });

    const response = await POST(
      new Request("http://localhost/api/gov/empenhos/22", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ funcao: "impne" })
      }),
      { params: Promise.resolve({ suite: "empenhos", id: "22" }) }
    );
    const payload = await response.json();

    expect(response.status).toBe(200);
    expect(payload.ok).toBe(true);
    expect(payload.record.estado).toBe("emitido");
    expect(atugovMock).toHaveBeenCalledWith("empenhos", 22, "impne");
    expect(detgovMock).toHaveBeenCalledWith("empenhos", 22);
  });

  it("POST aceita campo legado action", async () => {
    atugovMock.mockResolvedValue({ ok: true });
    detgovMock.mockResolvedValue({
      id: 31,
      nome: "OP-00031",
      estado: "enviado"
    });

    const response = await POST(
      new Request("http://localhost/api/gov/pagamentos/31", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ action: "impcnab" })
      }),
      { params: Promise.resolve({ suite: "pagamentos", id: "31" }) }
    );
    const payload = await response.json();

    expect(response.status).toBe(200);
    expect(payload.ok).toBe(true);
    expect(atugovMock).toHaveBeenCalledWith("pagamentos", 31, "impcnab");
  });

  it("PATCH atualiza processo", async () => {
    updateProcessoRecordMock.mockResolvedValue({
      id: 44,
      record: { id: 44, estado: "instrucao" },
      form: { record: { id: 44 } }
    });

    const response = await PATCH(
      new Request("http://localhost/api/gov/processos/44", {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ subject: "Novo assunto" })
      }),
      { params: Promise.resolve({ suite: "processos", id: "44" }) }
    );
    const payload = await response.json();

    expect(response.status).toBe(200);
    expect(payload.ok).toBe(true);
    expect(updateProcessoRecordMock).toHaveBeenCalledWith(44, { subject: "Novo assunto" });
  });
});
