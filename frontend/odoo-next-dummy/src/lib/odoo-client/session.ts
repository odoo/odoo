import { OdooClientError } from "@/lib/errors";
import { jsonRpcRequest } from "@/lib/odoo-client/jsonrpc";
import { OdooCredentials } from "@/lib/odoo-client/types";

type SessionAuthResult = {
  session_id?: string;
  uid?: number;
};

function parseSessionCookie(rawSetCookie: string | null): string | null {
  if (!rawSetCookie) {
    return null;
  }
  const match = rawSetCookie.match(/session_id=([^;]+)/);
  if (!match) {
    return null;
  }
  return `session_id=${match[1]}`;
}

export async function authenticate(credentials: OdooCredentials): Promise<string> {
  const response = await jsonRpcRequest<SessionAuthResult>({
    baseUrl: credentials.baseUrl,
    path: "/web/session/authenticate",
    params: {
      db: credentials.db,
      login: credentials.user,
      password: credentials.password
    },
    timeoutMs: credentials.timeoutMs
  });

  const cookie = parseSessionCookie(response.setCookie);
  if (cookie) {
    return cookie;
  }
  if (response.result.session_id) {
    return `session_id=${response.result.session_id}`;
  }

  throw new OdooClientError("Unable to authenticate with Odoo session", 401, response.result);
}
