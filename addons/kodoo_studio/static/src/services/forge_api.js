/** @odoo-module ignore **/

odoo.define("kodoo_studio.forge_api", function () {
    "use strict";

    const namespace = window.kodooStudio = window.kodooStudio || {};

    function normalizeModuleRecord(record) {
        if (!record) {
            return null;
        }
        const appValue = record.app_id;
        return Object.assign({}, record, {
            app_id: Array.isArray(appValue) ? appValue[0] : appValue || null,
            app_name: Array.isArray(appValue) ? appValue[1] : record.app_name || "",
        });
    }

    function normalizePath(path) {
        return String(path || "")
            .split("/")
            .filter(Boolean)
            .join("/");
    }

    function makeJsonRpcBody(params) {
        return {
            id: Date.now(),
            jsonrpc: "2.0",
            method: "call",
            params: params,
        };
    }

    async function parseJsonResponse(response) {
        const text = await response.text();
        if (!text) {
            return null;
        }
        try {
            return JSON.parse(text);
        } catch {
            return text;
        }
    }

    function extractError(payload, fallbackMessage) {
        if (!payload) {
            return fallbackMessage;
        }
        if (typeof payload === "string") {
            return payload;
        }
        if (payload.error && payload.error.data && payload.error.data.message) {
            return payload.error.data.message;
        }
        if (payload.error && payload.error.message) {
            return payload.error.message;
        }
        if (payload.detail && typeof payload.detail === "string") {
            return payload.detail;
        }
        if (payload.message && typeof payload.message === "string") {
            return payload.message;
        }
        return fallbackMessage;
    }

    class ForgeApiError extends Error {
        constructor(message, payload, status) {
            super(message);
            this.name = "ForgeApiError";
            this.payload = payload || null;
            this.status = status || 500;
        }
    }

    async function jsonRpc(url, params) {
        const response = await window.fetch(url, {
            method: "POST",
            credentials: "same-origin",
            headers: {
                "Content-Type": "application/json",
            },
            body: JSON.stringify(makeJsonRpcBody(params)),
        });
        const payload = await parseJsonResponse(response);
        if (!response.ok) {
            throw new ForgeApiError(
                extractError(payload, "Odoo RPC request failed"),
                payload,
                response.status
            );
        }
        if (payload && payload.error) {
            throw new ForgeApiError(
                extractError(payload, "Odoo RPC request failed"),
                payload,
                response.status
            );
        }
        return payload ? payload.result : null;
    }

    async function controllerRequest(path, options) {
        const normalized = normalizePath(path);
        const url = normalized
            ? `/kodoo/studio/api/${normalized}`
            : "/kodoo/studio/api";
        const requestOptions = Object.assign(
            {
                method: "GET",
                credentials: "same-origin",
                headers: {
                    Accept: "application/json",
                },
            },
            options || {}
        );
        const response = await window.fetch(url, requestOptions);
        const payload = await parseJsonResponse(response);
        if (!response.ok) {
            throw new ForgeApiError(
                extractError(payload, "Forge engine request failed"),
                payload,
                response.status
            );
        }
        return payload;
    }

    function callKw(model, method, args, kwargs) {
        const url = `/web/dataset/call_kw/${model}/${method}`;
        return jsonRpc(url, {
            model: model,
            method: method,
            args: args || [],
            kwargs: kwargs || {},
        });
    }

    const forgeApi = {
        async listApps() {
            return callKw("forge.app", "search_read", [[["id", "!=", 0]]], {
                fields: ["id", "name", "technical_name"],
                order: "name asc, id asc",
            });
        },

        async listModules(appId) {
            const records = await callKw("forge.module", "search_read", [[["app_id", "=", appId]]], {
                fields: ["id", "name", "technical_name", "state", "app_id", "version", "depends"],
                order: "name asc, id asc",
            });
            return (records || []).map(normalizeModuleRecord);
        },

        async getModule(id) {
            const records = await callKw("forge.module", "read", [[id]], {
                fields: ["id", "name", "technical_name", "app_id", "version", "depends", "state"],
            });
            return records && records.length ? normalizeModuleRecord(records[0]) : null;
        },

        async saveModule(id, vals) {
            await callKw("forge.module", "write", [[id], vals || {}], {});
            return this.getModule(id);
        },

        async createApp(vals) {
            const id = await callKw("forge.app", "create", [vals || {}], {});
            return id;
        },

        async createModule(vals) {
            const id = await callKw("forge.module", "create", [vals || {}], {});
            return id;
        },

        async listBuilds(moduleId) {
            return callKw("forge.build", "search_read", [[["module_id", "=", moduleId]]], {
                fields: ["id", "build_date", "state", "triggered_by", "log"],
                order: "build_date desc, id desc",
                limit: 1,
            });
        },

        async validate(moduleId) {
            return controllerRequest(`pipeline/${moduleId}/validate`, {
                method: "POST",
            });
        },

        async build(moduleId) {
            return controllerRequest(`pipeline/${moduleId}/build`, {
                method: "POST",
            });
        },

        async diff(moduleId) {
            return controllerRequest(`pipeline/${moduleId}/diff`);
        },

        async publish(moduleId, mode) {
            return controllerRequest(`pipeline/${moduleId}/publish`, {
                method: "POST",
                headers: {
                    Accept: "application/json",
                    "Content-Type": "application/json",
                },
                body: JSON.stringify({ mode: mode }),
            });
        },

        async snapshot(moduleId, name) {
            return controllerRequest(`pipeline/${moduleId}/snapshot`, {
                method: "POST",
                headers: {
                    Accept: "application/json",
                    "Content-Type": "application/json",
                },
                body: JSON.stringify({ name: name }),
            });
        },

        async listSnapshots(moduleId) {
            return controllerRequest(`pipeline/${moduleId}/snapshots`);
        },

        async rollback(moduleId, snapshotId) {
            return controllerRequest(`pipeline/${moduleId}/rollback/${snapshotId}`, {
                method: "POST",
            });
        },

        async conflicts(moduleId) {
            return controllerRequest(`pipeline/${moduleId}/conflicts`);
        },

        async getTerminalToken() {
            return controllerRequest("terminal/token", {
                method: "POST",
                headers: {
                    Accept: "application/json",
                    "Content-Type": "application/json",
                },
                body: JSON.stringify({}),
            });
        },
    };

    namespace.ForgeApiError = ForgeApiError;
    namespace.forgeApi = forgeApi;
    return forgeApi;
});
