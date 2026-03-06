import { describe, expect, it, vi } from "vitest";
import { OdooClient } from "@/lib/odoo-client";

describe("OdooClient", () => {
  it("autentica e faz call_kw com cookie de sessao", async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce({
        ok: true,
        status: 200,
        headers: new Headers({ "set-cookie": "session_id=abc123; Path=/" }),
        json: async () => ({ jsonrpc: "2.0", id: 1, result: { uid: 1 } })
      })
      .mockResolvedValueOnce({
        ok: true,
        status: 200,
        headers: new Headers(),
        json: async () => ({ jsonrpc: "2.0", id: 2, result: [{ id: 10 }] })
      });

    vi.stubGlobal("fetch", fetchMock);

    const client = new OdooClient({
      baseUrl: "http://odoo.local",
      db: "atlas",
      user: "admin",
      password: "admin",
      timeoutMs: 5000
    });

    const result = await client.callKw<Array<{ id: number }>>({
      model: "gov.processo",
      method: "search_read",
      args: [[]]
    });

    expect(result[0].id).toBe(10);
    expect(fetchMock).toHaveBeenCalledTimes(2);
    const secondCall = fetchMock.mock.calls[1];
    expect(secondCall?.[1]?.headers).toMatchObject({ Cookie: "session_id=abc123" });

    vi.unstubAllGlobals();
  });
});
