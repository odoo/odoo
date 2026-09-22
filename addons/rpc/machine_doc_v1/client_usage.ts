// What a caller writes against the generated client. It is checked in so the
// compile has something to compile: a client nobody calls type-checks
// vacuously, and this file is what makes a missing argument or a renamed door
// a compile error rather than a runtime 404.

import { OdooApiError, OdooClient } from "./client";

export async function readPartners(apiKey: string): Promise<unknown> {
    const client = new OdooClient({ baseUrl: "http://localhost:8069", apiKey });
    try {
        // The universal door: a bearer key, the model and the method in the
        // path, which is what `/json/2` serves.
        return await client.postJson2ModelMethod("res.partner", "search_read");
    } catch (error) {
        if (error instanceof OdooApiError && error.status === 401) {
            return undefined;
        }
        throw error;
    }
}

export async function serverVersion(): Promise<void> {
    // An open door takes no key, and the document says so: the method is
    // generated without an argument and the client sends no Authorization.
    await new OdooClient({ baseUrl: "http://localhost:8069" }).getWebVersion();
}
