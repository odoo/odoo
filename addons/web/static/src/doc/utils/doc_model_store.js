import { reactive, useState } from "@odoo/owl";

async function http(url, params) {
    const data = new FormData();
    data.append("csrf_token", odoo.csrf_token);

    for (const key in params) {
        const value = params[key];
        if (Array.isArray(value) && value.length) {
            for (const val of value) {
                data.append(key, val);
            }
        } else {
            data.append(key, value);
        }
    }

    try {
        const response = await fetch(url, {
            method: "POST",
            body: data,
        });
        const json = await response.text();
        return JSON.parse(json);
    } catch (error) {
        console.error(error);
        return {
            type: "http-error",
            error: error,
        };
    }
}

function cleanStr(str) {
    return (
        str
            ?.trim()
            .toLowerCase()
            .replace(/[^a-zA-Z\d]/g, "") ?? ""
    );
}

function stringMatch(query, str) {
    if (cleanStr(str).includes(query)) {
        return query.length / str.length;
    } else {
        return 0;
    }
}

export class ModelStore {
    constructor() {
        this.models = [];
        this._addons = {};

        this.showApiKeyModal = false;
        this.setAPIKey(localStorage.getItem("doc/apiKey"));
    }

    get addons() {
        return Object.values(this._addons);
    }

    async loadModels() {
        console.info("Loading Models...");
        const { models } = await http("/doc/index.json", {}, false);
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

        this.models = models;
        this._addons = addons;
    }

    async loadModel(modelId) {
        const sessionItemKey = `odoo-doc/models/${modelId}`;
        const sessionItem = sessionStorage.getItem(sessionItemKey);
        if (sessionItem) {
            const model = JSON.parse(sessionItem);
            return new Promise((resolve) => resolve(model));
        } else {
            const prom = http(`/doc/${modelId}.json`, {}, false);
            prom.then((model) => {
                console.info("Model Loaded: ", model);
                sessionStorage.setItem(sessionItemKey, JSON.stringify(model));
            });
            return prom;
        }
    }

    getBasicModelData(modelId) {
        return this.models.find((m) => m.model === modelId);
    }

    search(query) {
        query = cleanStr(query);

        const results = [];
        for (const model of this.models) {
            const modelMatch = stringMatch(query, model.model);
            const modelNameMatch = stringMatch(query, model.name);
            if (modelMatch > 0 || modelNameMatch > 0) {
                results.push({
                    priority: 10 * Math.max(modelMatch, modelNameMatch),
                    model,
                    type: "model",
                    label: model.name,
                    path: model.model,
                });
            }

            for (const field in model.fields) {
                const path = `${model.model}/${field}`;
                const pathMatch = stringMatch(query, path);
                const fieldMatch = stringMatch(query, field);
                const labelMatch = stringMatch(query, model.fields[field].string);
                if (pathMatch > 0 || fieldMatch > 0 || labelMatch > 0) {
                    results.push({
                        priority: 5 * Math.max(pathMatch, fieldMatch, labelMatch),
                        model,
                        field,
                        type: "field",
                        label: model.fields[field].string,
                        path,
                    });
                }
            }

            for (const method of model.methods) {
                const path = `${model.model}/${method}`;
                const pathMatch = stringMatch(query, path);
                const methodMatch = stringMatch(query, method);
                if (pathMatch > 0 || methodMatch > 0) {
                    results.push({
                        priority: 5 * Math.max(pathMatch, methodMatch),
                        model,
                        method,
                        type: "method",
                        label: method,
                        path: path,
                    });
                }
            }
        }

        results.sort((a, b) => {
            if (a.priority === b.priority) {
                return a.label.localeCompare(b.label);
            } else {
                return b.priority - a.priority;
            }
        });

        return results;
    }

    setAPIKey(apiKey) {
        if (typeof apiKey === "string" && apiKey.length > 0) {
            localStorage.setItem("doc/apiKey", apiKey);
            this.apiKey = apiKey;
        }
    }
}

export const modelStore = reactive(new ModelStore());

/**
 * @returns {ModelStore}
 */
export function useModelStore() {
    return useState(modelStore);
}
