import { markRaw, markup } from "@odoo/owl";
import { Reactive } from "@web/core/utils/reactive";

function tryParseJSON(jsonString) {
    try {
        const json = JSON.parse(jsonString);
        return json && typeof json === "object" ? json : null;
    } catch {
        return null;
    }
}

async function tryFetch(input) {
    try {
        const response = await fetch(input);
        let responseJson;
        try {
            responseJson = await response.json();
        } catch (err) {
            throw new DocAPIError ({
                name: "Invalid JSON Response",
                status: response.status,
                traceback: err,
            });
        }
        if (!response.ok) {
            throw new DocAPIError ({
                name: response.status === 500
                    ? "Internal Server Error"
                    : `HTTP $(response.status)`,
                status: response.status,
                traceback: responseJson.debug,
            });
        }
        return responseJson;
    } catch(err) {
        if (err instanceof DocAPIError) throw err;
        throw new DocAPIError({
            name: "Network Error",
            status: null,
            traceback: err,
        });
    }
}

class DocAPIError extends Error {
    constructor({ name, status, traceback } = {}) {
        super(name);
        this.name = name;
        this.status = status ?? null;
        this.traceback = traceback ?? null;
    }
}

export class ModelStore extends Reactive {
    constructor() {
        super();

        this.models = [];
        this._addons = {};

        this.apiKey = null;
        this.showApiKeyModal = false;

        this.activeModel = null;
        this.activeField = null;
        this.activeMethod = null;
        this.error = null;
    }

    get addons() {
        return Object.values(this._addons);
    }

    async loadModels() {
        try {
            console.info("Loading Models...");
            const response = await tryFetch(`/doc/index.json`);

            const { models } = response;
            console.info("Models List Loaded", models);

            models.sort((a, b) => a.model.localeCompare(b.model));

            const addons = {};
            for (const model of models) {
                const addonName = model.model.split(".")[0];

                if (addons[addonName]) {
                    addons[addonName].models.push(model);
                } else {
                    addons[addonName] = {
                        name: addonName,
                        models: [model],
                    };
                }
            }

            const other = { name: "other", models: [] };
            for (const category in addons) {
                const models = addons[category].models;
                if (models.length <= 3) {
                    other.models.push(...models);
                    delete addons[category];
                }
            }
            addons["other"] = other;

            this.models = markRaw(models);
            this._addons = markRaw(addons);
        } catch (e) {
            this.error = e;
        }
    }

    async loadModel(modelId) {
        try {
            const model = await tryFetch(`/doc/${modelId}.json`);

            if (model.doc) {
                model.doc = markup(model.doc);
            }

            Object.values(model.methods).forEach((method) => {
                method.doc = method.doc ? markup(method.doc) : null;
            });

            console.info("Model Loaded: ", model);
            return model;
        } catch (e) {
            this.error = e;
        }
    }

    getBasicModelData(modelId) {
        return this.models.find((m) => m.model === modelId);
    }

    setAPIKey(apiKey) {
        if (typeof apiKey === "string" && apiKey.length > 0) {
            this.apiKey = apiKey;
        }
    }

    setActiveModel({ model, method = null, field = null }) {
        if (typeof model === "string") {
            model = this.getBasicModelData(model);
        }

        if (model) {
            this.activeModel = model;
            this.activeMethod = method;
            this.activeField = field;

            let url = `/doc/${model.model}`;
            if (method || field) {
                url += "#" + (method || field);
            }
            window.history.pushState({}, "", url);
        }
    }

    async executeRequest(url, requestBody) {
        if (!this.apiKey) {
            this.showApiKeyModal = true;
            return null;
        }

        const result = {
            status: null,
            body: null,
            error: null,
        };

        try {
            const request = {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                    Authorization: `Bearer ${this.apiKey}`,
                },
                body: requestBody,
            };

            const response = await fetch(url, request);
            result.status = response.status;

            const body = await response.text();
            const json = tryParseJSON(body);

            if (response.ok) {
                result.body = json ? JSON.stringify(json, null, 2) : body;
            } else {
                result.error = !json
                    ? body
                    : [
                        `<h3 class="mb-1">${json.message}</h3>`,
                        `<pre class="p-2">${json.debug}</pre>`,
                    ].join("\n");
            }
        } catch (error) {
            result.error = error;
        }

        return result;
    }
}
