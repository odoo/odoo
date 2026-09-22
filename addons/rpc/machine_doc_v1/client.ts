// Generated from openapi.json; do not edit.
// Regenerate: ODOO_WRITE_OPENAPI=1 odoo-bin -d <db> --test-enable \
//     --test-tags /rpc:TestOpenAPIContract.test_the_checked_in_client_is_current

// Odoo RPC 19.0

export interface OdooClientOptions {
    /** Where the server answers, without a trailing slash. */
    baseUrl: string;
    /** A res.users.apikeys key, for a door whose `x-odoo-auth` is bearer. */
    apiKey?: string;
    /** Injected in a test, or to add a proxy; defaults to global fetch. */
    fetch?: typeof fetch;
}

export class OdooApiError extends Error {
    constructor(
        readonly status: number,
        readonly body: unknown,
    ) {
        super(`Odoo answered ${status}`);
        this.name = "OdooApiError";
    }
}

export class OdooClient {
    private readonly baseUrl: string;
    private readonly apiKey?: string;
    private readonly doFetch: typeof fetch;

    constructor(options: OdooClientOptions) {
        this.baseUrl = options.baseUrl.replace(/\/$/, "");
        this.apiKey = options.apiKey;
        this.doFetch = options.fetch ?? globalThis.fetch;
    }

    private async call<T>(
        method: string,
        path: string,
        body: unknown,
        authenticated: boolean,
    ): Promise<T> {
        const headers: Record<string, string> = {};
        if (body !== undefined) {
            headers["Content-Type"] = "application/json";
        }
        if (authenticated && this.apiKey) {
            headers["Authorization"] = `Bearer ${this.apiKey}`;
        }
        const response = await this.doFetch(`${this.baseUrl}${path}`, {
            method,
            headers,
            body: body === undefined ? undefined : JSON.stringify(body),
        });
        const text = await response.text();
        const parsed: unknown = text ? JSON.parse(text) : undefined;
        if (!response.ok) {
            throw new OdooApiError(response.status, parsed);
        }
        return parsed as T;
    }

    private query(pairs: [string, unknown][]): string {
        const given = pairs.filter(([, value]) => value !== undefined);
        if (!given.length) {
            return "";
        }
        const encoded = given.map(
            ([key, value]) =>
                `${encodeURIComponent(key)}=${encodeURIComponent(String(value))}`,
        );
        return `?${encoded.join("&")}`;
    }

    /** DELETE /doc-bearer/index.json (auth: bearer) */
    async deleteDocBearerIndexJson(): Promise<unknown> {
        return this.call("DELETE", `/doc-bearer/index.json`, undefined, true);
    }

    /** GET /doc-bearer/index.json (auth: bearer) */
    async getDocBearerIndexJson(): Promise<unknown> {
        return this.call("GET", `/doc-bearer/index.json`, undefined, true);
    }

    /** PATCH /doc-bearer/index.json (auth: bearer) */
    async patchDocBearerIndexJson(): Promise<unknown> {
        return this.call("PATCH", `/doc-bearer/index.json`, undefined, true);
    }

    /** POST /doc-bearer/index.json (auth: bearer) */
    async postDocBearerIndexJson(): Promise<unknown> {
        return this.call("POST", `/doc-bearer/index.json`, undefined, true);
    }

    /** PUT /doc-bearer/index.json (auth: bearer) */
    async putDocBearerIndexJson(): Promise<unknown> {
        return this.call("PUT", `/doc-bearer/index.json`, undefined, true);
    }

    /** DELETE /doc-bearer/{model_name}.json (auth: bearer) */
    async deleteDocBearerModelNameJson(modelName: string): Promise<unknown> {
        return this.call(
            "DELETE",
            `/doc-bearer/${encodeURIComponent(String(modelName))}.json`,
            undefined,
            true,
        );
    }

    /** GET /doc-bearer/{model_name}.json (auth: bearer) */
    async getDocBearerModelNameJson(modelName: string): Promise<unknown> {
        return this.call(
            "GET",
            `/doc-bearer/${encodeURIComponent(String(modelName))}.json`,
            undefined,
            true,
        );
    }

    /** PATCH /doc-bearer/{model_name}.json (auth: bearer) */
    async patchDocBearerModelNameJson(modelName: string): Promise<unknown> {
        return this.call(
            "PATCH",
            `/doc-bearer/${encodeURIComponent(String(modelName))}.json`,
            undefined,
            true,
        );
    }

    /** POST /doc-bearer/{model_name}.json (auth: bearer) */
    async postDocBearerModelNameJson(modelName: string): Promise<unknown> {
        return this.call(
            "POST",
            `/doc-bearer/${encodeURIComponent(String(modelName))}.json`,
            undefined,
            true,
        );
    }

    /** PUT /doc-bearer/{model_name}.json (auth: bearer) */
    async putDocBearerModelNameJson(modelName: string): Promise<unknown> {
        return this.call(
            "PUT",
            `/doc-bearer/${encodeURIComponent(String(modelName))}.json`,
            undefined,
            true,
        );
    }

    /** DELETE /doc/index.json (auth: user) */
    async deleteDocIndexJson(): Promise<unknown> {
        return this.call("DELETE", `/doc/index.json`, undefined, false);
    }

    /** GET /doc/index.json (auth: user) */
    async getDocIndexJson(): Promise<unknown> {
        return this.call("GET", `/doc/index.json`, undefined, false);
    }

    /** PATCH /doc/index.json (auth: user) */
    async patchDocIndexJson(): Promise<unknown> {
        return this.call("PATCH", `/doc/index.json`, undefined, false);
    }

    /** POST /doc/index.json (auth: user) */
    async postDocIndexJson(): Promise<unknown> {
        return this.call("POST", `/doc/index.json`, undefined, false);
    }

    /** PUT /doc/index.json (auth: user) */
    async putDocIndexJson(): Promise<unknown> {
        return this.call("PUT", `/doc/index.json`, undefined, false);
    }

    /** DELETE /doc/{model_name}.json (auth: user) */
    async deleteDocModelNameJson(modelName: string): Promise<unknown> {
        return this.call(
            "DELETE",
            `/doc/${encodeURIComponent(String(modelName))}.json`,
            undefined,
            false,
        );
    }

    /** GET /doc/{model_name}.json (auth: user) */
    async getDocModelNameJson(modelName: string): Promise<unknown> {
        return this.call(
            "GET",
            `/doc/${encodeURIComponent(String(modelName))}.json`,
            undefined,
            false,
        );
    }

    /** PATCH /doc/{model_name}.json (auth: user) */
    async patchDocModelNameJson(modelName: string): Promise<unknown> {
        return this.call(
            "PATCH",
            `/doc/${encodeURIComponent(String(modelName))}.json`,
            undefined,
            false,
        );
    }

    /** POST /doc/{model_name}.json (auth: user) */
    async postDocModelNameJson(modelName: string): Promise<unknown> {
        return this.call(
            "POST",
            `/doc/${encodeURIComponent(String(modelName))}.json`,
            undefined,
            false,
        );
    }

    /** PUT /doc/{model_name}.json (auth: user) */
    async putDocModelNameJson(modelName: string): Promise<unknown> {
        return this.call(
            "PUT",
            `/doc/${encodeURIComponent(String(modelName))}.json`,
            undefined,
            false,
        );
    }

    /** DELETE /json/2 (auth: public) */
    async deleteJson2(body?: { subpath?: string | null }): Promise<unknown> {
        return this.call("DELETE", `/json/2`, body, false);
    }

    /** GET /json/2 (auth: public) */
    async getJson2(body?: { subpath?: string | null }): Promise<unknown> {
        return this.call("GET", `/json/2`, body, false);
    }

    /** PATCH /json/2 (auth: public) */
    async patchJson2(body?: { subpath?: string | null }): Promise<unknown> {
        return this.call("PATCH", `/json/2`, body, false);
    }

    /** POST /json/2 (auth: public) */
    async postJson2(body?: { subpath?: string | null }): Promise<unknown> {
        return this.call("POST", `/json/2`, body, false);
    }

    /** PUT /json/2 (auth: public) */
    async putJson2(body?: { subpath?: string | null }): Promise<unknown> {
        return this.call("PUT", `/json/2`, body, false);
    }

    /** POST /json/2/{__model__}/{__method__} (auth: bearer) */
    async postJson2ModelMethod(model: string, method: string): Promise<unknown> {
        return this.call(
            "POST",
            `/json/2/${encodeURIComponent(String(model))}/${encodeURIComponent(String(method))}`,
            undefined,
            true,
        );
    }

    /** DELETE /json/2/{subpath} (auth: public) */
    async deleteJson2Subpath(subpath: string): Promise<unknown> {
        return this.call(
            "DELETE",
            `/json/2/${encodeURIComponent(String(subpath))}`,
            undefined,
            false,
        );
    }

    /** GET /json/2/{subpath} (auth: public) */
    async getJson2Subpath(subpath: string): Promise<unknown> {
        return this.call(
            "GET",
            `/json/2/${encodeURIComponent(String(subpath))}`,
            undefined,
            false,
        );
    }

    /** PATCH /json/2/{subpath} (auth: public) */
    async patchJson2Subpath(subpath: string): Promise<unknown> {
        return this.call(
            "PATCH",
            `/json/2/${encodeURIComponent(String(subpath))}`,
            undefined,
            false,
        );
    }

    /** POST /json/2/{subpath} (auth: public) */
    async postJson2Subpath(subpath: string): Promise<unknown> {
        return this.call(
            "POST",
            `/json/2/${encodeURIComponent(String(subpath))}`,
            undefined,
            false,
        );
    }

    /** PUT /json/2/{subpath} (auth: public) */
    async putJson2Subpath(subpath: string): Promise<unknown> {
        return this.call(
            "PUT",
            `/json/2/${encodeURIComponent(String(subpath))}`,
            undefined,
            false,
        );
    }

    /** DELETE /json/version (auth: none) */
    async deleteJsonVersion(): Promise<void> {
        return this.call("DELETE", `/json/version`, undefined, false);
    }

    /** GET /json/version (auth: none) */
    async getJsonVersion(): Promise<void> {
        return this.call("GET", `/json/version`, undefined, false);
    }

    /** PATCH /json/version (auth: none) */
    async patchJsonVersion(): Promise<void> {
        return this.call("PATCH", `/json/version`, undefined, false);
    }

    /** POST /json/version (auth: none) */
    async postJsonVersion(): Promise<void> {
        return this.call("POST", `/json/version`, undefined, false);
    }

    /** PUT /json/version (auth: none) */
    async putJsonVersion(): Promise<void> {
        return this.call("PUT", `/json/version`, undefined, false);
    }

    /** DELETE /web/version (auth: none) */
    async deleteWebVersion(): Promise<void> {
        return this.call("DELETE", `/web/version`, undefined, false);
    }

    /** GET /web/version (auth: none) */
    async getWebVersion(): Promise<void> {
        return this.call("GET", `/web/version`, undefined, false);
    }

    /** PATCH /web/version (auth: none) */
    async patchWebVersion(): Promise<void> {
        return this.call("PATCH", `/web/version`, undefined, false);
    }

    /** POST /web/version (auth: none) */
    async postWebVersion(): Promise<void> {
        return this.call("POST", `/web/version`, undefined, false);
    }

    /** PUT /web/version (auth: none) */
    async putWebVersion(): Promise<void> {
        return this.call("PUT", `/web/version`, undefined, false);
    }

    /** POST /xmlrpc/2/{service} (auth: none) */
    async postXmlrpc2Service(service: string): Promise<void> {
        return this.call(
            "POST",
            `/xmlrpc/2/${encodeURIComponent(String(service))}`,
            undefined,
            false,
        );
    }

    /** POST /xmlrpc/{service} (auth: none) */
    async postXmlrpcService(service: string): Promise<void> {
        return this.call(
            "POST",
            `/xmlrpc/${encodeURIComponent(String(service))}`,
            undefined,
            false,
        );
    }
}
