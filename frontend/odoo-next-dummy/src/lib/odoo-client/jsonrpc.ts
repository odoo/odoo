import { OdooClientError } from "@/lib/errors";
import { JsonRpcResponse } from "@/lib/odoo-client/types";

type JsonRpcRequestInput = {
  baseUrl: string;
  path: string;
  params: Record<string, unknown>;
  cookie?: string;
  timeoutMs: number;
};

type JsonRpcRequestOutput<T> = {
  result: T;
  setCookie: string | null;
};

export async function jsonRpcRequest<T>(input: JsonRpcRequestInput): Promise<JsonRpcRequestOutput<T>> {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), input.timeoutMs);

  try {
    const url = new URL(input.path, input.baseUrl).toString();
    const response = await fetch(url, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        ...(input.cookie ? { Cookie: input.cookie } : {})
      },
      body: JSON.stringify({
        jsonrpc: "2.0",
        method: "call",
        params: input.params,
        id: Date.now()
      }),
      signal: controller.signal
    });

    const payload = (await response.json()) as JsonRpcResponse<T>;

    if (!response.ok) {
      throw new OdooClientError(`Odoo HTTP ${response.status}`, response.status, payload);
    }
    if (payload.error) {
      throw new OdooClientError(payload.error.message, 502, payload.error);
    }
    if (payload.result === undefined) {
      throw new OdooClientError("Invalid JSON-RPC payload: missing result", 502, payload);
    }

    return {
      result: payload.result,
      setCookie: response.headers.get("set-cookie")
    };
  } catch (error) {
    if (error instanceof OdooClientError) {
      throw error;
    }
    if (error instanceof Error && error.name === "AbortError") {
      throw new OdooClientError(`Odoo request timeout after ${input.timeoutMs}ms`, 504);
    }
    throw new OdooClientError("Unexpected Odoo request error", 500, error);
  } finally {
    clearTimeout(timeout);
  }
}
