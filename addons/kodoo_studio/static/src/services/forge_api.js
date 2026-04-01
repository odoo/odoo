/** @odoo-module ignore **/

odoo.define("kodoo_studio.forge_api", [], function () {
    "use strict";

    const namespace = window.kodooStudio = window.kodooStudio || {};
    const ENGINE_OFFLINE_MESSAGE = "Engine offline";

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

    function stringifyDetail(detail) {
        if (detail == null) {
            return "";
        }
        if (typeof detail === "string") {
            return detail;
        }
        try {
            return JSON.stringify(detail, null, 2);
        } catch {
            return String(detail);
        }
    }

    function extractErrorParts(payload, fallbackMessage) {
        if (!payload) {
            return { message: fallbackMessage, detail: null };
        }
        if (typeof payload === "string") {
            return { message: payload, detail: payload };
        }
        if (payload.error && typeof payload.error === "string") {
            return { message: payload.error, detail: payload };
        }
        if (payload.error && payload.error.data && payload.error.data.message) {
            return { message: payload.error.data.message, detail: payload.error.data };
        }
        if (payload.error && payload.error.message) {
            return { message: payload.error.message, detail: payload.error };
        }
        if (payload.detail && typeof payload.detail === "string") {
            return { message: payload.detail, detail: payload.detail };
        }
        if (payload.detail && payload.detail.message) {
            return { message: payload.detail.message, detail: payload.detail };
        }
        if (payload.message && typeof payload.message === "string") {
            return { message: payload.message, detail: payload };
        }
        return {
            message: fallbackMessage,
            detail: payload,
        };
    }

    class ForgeApiError extends Error {
        constructor(message, status, detail, endpoint) {
            super(message);
            this.name = "ForgeApiError";
            this.status = status;
            this.detail = detail || null;
            this.endpoint = endpoint;
            this.payload = detail || null;
        }
    }

    function toForgeApiError(error, endpoint, fallbackMessage) {
        if (error instanceof ForgeApiError) {
            if (!error.endpoint) {
                error.endpoint = endpoint;
            }
            return error;
        }
        if (error instanceof TypeError) {
            return new ForgeApiError(ENGINE_OFFLINE_MESSAGE, 0, null, endpoint);
        }
        return new ForgeApiError(
            (error && error.message) || fallbackMessage,
            (error && error.status) || 500,
            (error && (error.detail || error.payload)) || null,
            endpoint
        );
    }

    async function fetchJson(endpoint, options, fallbackMessage) {
        let response;
        try {
            response = await window.fetch(endpoint, options);
        } catch (_error) {
            throw new ForgeApiError(ENGINE_OFFLINE_MESSAGE, 0, null, endpoint);
        }

        const payload = await parseJsonResponse(response);
        if (!response.ok) {
            const extracted = extractErrorParts(
                payload,
                response.status === 503 ? ENGINE_OFFLINE_MESSAGE : fallbackMessage
            );
            throw new ForgeApiError(
                extracted.message,
                response.status,
                extracted.detail,
                endpoint
            );
        }
        return payload;
    }

    async function jsonRpc(url, params) {
        const payload = await fetchJson(
            url,
            {
                method: "POST",
                credentials: "same-origin",
                headers: {
                    "Content-Type": "application/json",
                },
                body: JSON.stringify(makeJsonRpcBody(params)),
            },
            "Odoo RPC request failed"
        );
        if (payload && payload.error) {
            const extracted = extractErrorParts(payload, "Odoo RPC request failed");
            throw new ForgeApiError(extracted.message, 500, extracted.detail, url);
        }
        return payload ? payload.result : null;
    }

    async function controllerRequest(path, options, fallbackMessage) {
        const normalized = normalizePath(path);
        const endpoint = normalized
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
        return fetchJson(endpoint, requestOptions, fallbackMessage || "Forge engine request failed");
    }

    function callKw(model, method, args, kwargs) {
        const endpoint = `/web/dataset/call_kw/${model}/${method}`;
        return jsonRpc(endpoint, {
            model: model,
            method: method,
            args: args || [],
            kwargs: kwargs || {},
        });
    }

    async function wrapCall(endpoint, fallbackMessage, callback) {
        try {
            return await callback();
        } catch (error) {
            throw toForgeApiError(error, endpoint, fallbackMessage);
        }
    }

    const forgeApi = {
        ForgeApiError: ForgeApiError,
        stringifyDetail: stringifyDetail,

        async listApps() {
            return wrapCall(
                "/web/dataset/call_kw/forge.app/search_read",
                "Could not load apps.",
                async () => {
                    return callKw("forge.app", "search_read", [[["id", "!=", 0]]], {
                        fields: ["id", "name", "technical_name"],
                        order: "name asc, id asc",
                    });
                }
            );
        },

        async listModules(appId) {
            return wrapCall(
                "/web/dataset/call_kw/forge.module/search_read",
                "Could not load modules.",
                async () => {
                    const records = await callKw("forge.module", "search_read", [[["app_id", "=", appId]]], {
                        fields: ["id", "name", "technical_name", "state", "app_id", "version", "depends"],
                        order: "name asc, id asc",
                    });
                    return (records || []).map(normalizeModuleRecord);
                }
            );
        },

        async getModule(id) {
            return wrapCall(
                "/web/dataset/call_kw/forge.module/read",
                "Could not load module.",
                async () => {
                    const records = await callKw("forge.module", "read", [[id]], {
                        fields: ["id", "name", "technical_name", "app_id", "version", "depends", "state"],
                    });
                    return records && records.length ? normalizeModuleRecord(records[0]) : null;
                }
            );
        },

        async saveModule(id, vals) {
            return wrapCall(
                "/web/dataset/call_kw/forge.module/write",
                "Could not save module.",
                async () => {
                    await callKw("forge.module", "write", [[id], vals || {}], {});
                    return this.getModule(id);
                }
            );
        },

        async createApp(vals) {
            return wrapCall(
                "/web/dataset/call_kw/forge.app/create",
                "Could not create app.",
                async () => {
                    return callKw("forge.app", "create", [vals || {}], {});
                }
            );
        },

        async createModule(vals) {
            return wrapCall(
                "/web/dataset/call_kw/forge.module/create",
                "Could not create module.",
                async () => {
                    return callKw("forge.module", "create", [vals || {}], {});
                }
            );
        },

        async listBuilds(moduleId) {
            return wrapCall(
                "/web/dataset/call_kw/forge.build/search_read",
                "Could not load builds.",
                async () => {
                    return callKw("forge.build", "search_read", [[["module_id", "=", moduleId]]], {
                        fields: ["id", "build_date", "state", "triggered_by", "log"],
                        order: "build_date desc, id desc",
                        limit: 1,
                    });
                }
            );
        },

        async validate(moduleId) {
            return wrapCall(`/kodoo/studio/api/pipeline/${moduleId}/validate`, "Validation failed.", async () => {
                return controllerRequest(`pipeline/${moduleId}/validate`, {
                    method: "POST",
                }, "Validation failed.");
            });
        },

        async build(moduleId) {
            return wrapCall(`/kodoo/studio/api/pipeline/${moduleId}/build`, "Build failed.", async () => {
                return controllerRequest(`pipeline/${moduleId}/build`, {
                    method: "POST",
                }, "Build failed.");
            });
        },

        async diff(moduleId) {
            return wrapCall(`/kodoo/studio/api/pipeline/${moduleId}/diff`, "Diff failed.", async () => {
                return controllerRequest(`pipeline/${moduleId}/diff`, {
                    method: "GET",
                }, "Diff failed.");
            });
        },

        async publish(moduleId, mode) {
            return wrapCall(`/kodoo/studio/api/pipeline/${moduleId}/publish`, "Publish failed.", async () => {
                return controllerRequest(`pipeline/${moduleId}/publish`, {
                    method: "POST",
                    headers: {
                        Accept: "application/json",
                        "Content-Type": "application/json",
                    },
                    body: JSON.stringify({ mode: mode }),
                }, "Publish failed.");
            });
        },

        async snapshot(moduleId, name) {
            return wrapCall(`/kodoo/studio/api/pipeline/${moduleId}/snapshot`, "Snapshot failed.", async () => {
                return controllerRequest(`pipeline/${moduleId}/snapshot`, {
                    method: "POST",
                    headers: {
                        Accept: "application/json",
                        "Content-Type": "application/json",
                    },
                    body: JSON.stringify({ name: name }),
                }, "Snapshot failed.");
            });
        },

        async listSnapshots(moduleId) {
            return wrapCall(`/kodoo/studio/api/pipeline/${moduleId}/snapshots`, "Could not load snapshots.", async () => {
                return controllerRequest(`pipeline/${moduleId}/snapshots`, {
                    method: "GET",
                }, "Could not load snapshots.");
            });
        },

        async rollback(moduleId, snapshotId) {
            return wrapCall(`/kodoo/studio/api/pipeline/${moduleId}/rollback/${snapshotId}`, "Rollback failed.", async () => {
                return controllerRequest(`pipeline/${moduleId}/rollback/${snapshotId}`, {
                    method: "POST",
                }, "Rollback failed.");
            });
        },

        async conflicts(moduleId) {
            return wrapCall(`/kodoo/studio/api/pipeline/${moduleId}/conflicts`, "Could not load conflicts.", async () => {
                return controllerRequest(`pipeline/${moduleId}/conflicts`, {
                    method: "GET",
                }, "Could not load conflicts.");
            });
        },

        async getTerminalToken() {
            return wrapCall("/kodoo/studio/api/terminal/token", "Could not request terminal token.", async () => {
                return controllerRequest("terminal/token", {
                    method: "POST",
                    headers: {
                        Accept: "application/json",
                        "Content-Type": "application/json",
                    },
                    body: JSON.stringify({}),
                }, "Could not request terminal token.");
            });
        },

        async isOnline() {
            return wrapCall("/kodoo/studio/api/health", ENGINE_OFFLINE_MESSAGE, async () => {
                await controllerRequest("health", {
                    method: "HEAD",
                    headers: {
                        Accept: "application/json",
                    },
                }, ENGINE_OFFLINE_MESSAGE);
                return true;
            });
        },
    };

    namespace.ForgeApiError = ForgeApiError;
    namespace.forgeApi = forgeApi;
    return forgeApi;
});
