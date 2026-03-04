function required(name: string): string {
  const value = process.env[name];
  if (!value) {
    throw new Error(`Missing required env var: ${name}`);
  }
  return value;
}

function toInt(value: string | undefined, fallback: number): number {
  if (!value) {
    return fallback;
  }
  const parsed = Number.parseInt(value, 10);
  return Number.isNaN(parsed) ? fallback : parsed;
}

export const env = {
  odooBaseUrl: required("ODOO_BASE_URL"),
  odooDb: required("ODOO_DB"),
  odooUser: required("ODOO_USER"),
  odooPassword: required("ODOO_PASSWORD"),
  odooTimeoutMs: toInt(process.env.ODOO_TIMEOUT_MS, 15000),
  odooProcessModel: process.env.ODOO_PROCESS_MODEL ?? "gov.processo",
  odooDocumentModel: process.env.ODOO_DOCUMENT_MODEL ?? "gov.documento.dfd"
};
