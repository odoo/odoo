export class OdooClientError extends Error {
  status: number;
  payload?: unknown;

  constructor(message: string, status = 500, payload?: unknown) {
    super(message);
    this.name = "OdooClientError";
    this.status = status;
    this.payload = payload;
  }
}
