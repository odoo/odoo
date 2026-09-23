// @ts-check
/** @odoo-module native */

import { editModelDebug } from "@web/core/debug/debug_utils";
import { registry } from "@web/core/registry";
import { _t } from "@web/core/translation";

/** @import { Action } from "./action_service.js" */
const debugRegistry = registry.category("debug");

/** @type {WeakMap<object, Map<string, Promise<number>>>} */
const modelIdCaches = new WeakMap();

/**
 * @param {import("@web/env").OdooEnv} env
 * @param {string} resModel
 * @returns {Promise<number>}
 */
function getModelId(env, resModel) {
    let cache = modelIdCaches.get(env);
    if (!cache) {
        cache = new Map();
        modelIdCaches.set(env, cache);
    }
    let modelIdProm = cache.get(resModel);
    if (!modelIdProm) {
        modelIdProm = env.services.orm
            .search("ir.model", [["model", "=", resModel]], { limit: 1 })
            .then(([modelId]) => {
                if (modelId === undefined) {
                    throw new Error(`No ir.model record found for model "${resModel}"`);
                }
                return modelId;
            });
        modelIdProm.catch(() => cache.delete(resModel));
        cache.set(resModel, modelIdProm);
    }
    return modelIdProm;
}

/**
 * @param {string} resModel
 * @param {string} name
 * @param {number} modelId
 * @returns {Record<string, any>}
 */
function modelScopedAction(resModel, name, modelId) {
    return {
        res_model: resModel,
        name,
        views: [
            [false, "list"],
            [false, "form"],
        ],
        domain: [["model_id", "=", modelId]],
        type: "ir.actions.act_window",
        context: { default_model_id: modelId },
    };
}

/**
 * @param {{ action: Action, env: import("@web/env").OdooEnv }} params
 * @returns {Record<string, any> | null}
 */
function editAction({ action, env }) {
    if (!action.id) {
        return null;
    }
    const actionId = action.id;
    const description = _t("Action");
    return {
        type: "item",
        description,
        callback: async () => {
            await editModelDebug(env, description, action.type, actionId);
        },
        sequence: 220,
        section: "ui",
    };
}

/**
 * @param {{ action: Action, env: import("@web/env").OdooEnv }} params
 * @returns {Record<string, any> | null}
 */
function viewFields({ action, env }) {
    if (!action.res_model) {
        return null;
    }
    const description = _t("Fields");
    return {
        type: "item",
        description,
        callback: async () => {
            const modelId = await getModelId(
                env,
                /** @type {string} */ (action.res_model),
            );
            await env.services.action.doAction(
                modelScopedAction("ir.model.fields", description, modelId),
            );
        },
        sequence: 250,
        section: "ui",
    };
}

/**
 * @param {{ action: Action, env: import("@web/env").OdooEnv }} params
 * @returns {Record<string, any> | null}
 */
function ViewModel({ action, env }) {
    if (!action.res_model) {
        return null;
    }
    const modelName = action.res_model;
    return {
        type: "item",
        description: _t("Model: %s", modelName),
        callback: async () => {
            const modelId = await getModelId(env, modelName);
            await editModelDebug(env, modelName, "ir.model", modelId);
        },
        sequence: 210,
        section: "ui",
    };
}

/**
 * @param {{ action: Action, env: import("@web/env").OdooEnv }} params
 * @returns {Record<string, any> | null}
 */
function manageFilters({ action, env }) {
    if (!action.res_model) {
        return null;
    }
    const description = _t("Filters");
    return {
        type: "item",
        description,
        callback: async () => {
            await env.services.action.doAction({
                res_model: "ir.filters",
                name: description,
                views: [
                    [false, "list"],
                    [false, "form"],
                ],
                type: "ir.actions.act_window",
                context: {
                    search_default_my_filters: true,
                    search_default_model_id: action.res_model,
                },
            });
        },
        sequence: 260,
        section: "ui",
    };
}

/**
 * @param {{ accessRights: Record<string, any>, action: Action, env: import("@web/env").OdooEnv }} params
 * @returns {Record<string, any> | null}
 */
function viewAccesses({ accessRights, action, env }) {
    if (!action.res_model || !accessRights.canSeeAccesses) {
        return null;
    }
    const description = _t("Accesses");
    return {
        type: "item",
        description,
        callback: async () => {
            const modelId = await getModelId(
                env,
                /** @type {string} */ (action.res_model),
            );
            await env.services.action.doAction(
                modelScopedAction("ir.access", description, modelId),
            );
        },
        sequence: 350,
        section: "security",
    };
}

debugRegistry
    .category("action")
    .add("editAction", /** @type {any} */ (editAction))
    .add("viewFields", /** @type {any} */ (viewFields))
    .add("ViewModel", /** @type {any} */ (ViewModel))
    .add("manageFilters", /** @type {any} */ (manageFilters))
    .add("viewAccesses", /** @type {any} */ (viewAccesses));
