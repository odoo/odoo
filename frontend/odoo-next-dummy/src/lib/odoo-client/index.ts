import { jsonRpcRequest } from "@/lib/odoo-client/jsonrpc";
import { authenticate } from "@/lib/odoo-client/session";
import { CallKwInput, OdooCredentials } from "@/lib/odoo-client/types";

export class OdooClient {
  private sessionCookie: string | null = null;

  constructor(private readonly credentials: OdooCredentials) {}

  private async ensureSession() {
    if (!this.sessionCookie) {
      this.sessionCookie = await authenticate(this.credentials);
    }
    return this.sessionCookie;
  }

  async jsonRpc<T>(path: string, params: Record<string, unknown>): Promise<T> {
    const cookie = await this.ensureSession();
    const response = await jsonRpcRequest<T>({
      baseUrl: this.credentials.baseUrl,
      path,
      params,
      cookie,
      timeoutMs: this.credentials.timeoutMs
    });
    return response.result;
  }

  async callKw<T>(input: CallKwInput): Promise<T> {
    const kwargs = { ...(input.kwargs ?? {}) };
    if (!("context" in kwargs)) {
      kwargs.context = input.context ?? {};
    }

    return this.jsonRpc<T>(
      `/web/dataset/call_kw/${encodeURIComponent(input.model)}/${encodeURIComponent(input.method)}`,
      {
        model: input.model,
        method: input.method,
        args: input.args ?? [],
        kwargs
      }
    );
  }
}
