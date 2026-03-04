export type JsonRpcResponse<T> = {
  jsonrpc: "2.0";
  id: number | string | null;
  result?: T;
  error?: {
    code: number;
    message: string;
    data?: unknown;
  };
};

export type OdooCredentials = {
  baseUrl: string;
  db: string;
  user: string;
  password: string;
  timeoutMs: number;
};

export type CallKwInput = {
  model: string;
  method: string;
  args?: unknown[];
  kwargs?: Record<string, unknown>;
  context?: Record<string, unknown>;
};
