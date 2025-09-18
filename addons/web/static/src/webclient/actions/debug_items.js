// @ts-check

/** @module @web/webclient/actions/debug_items - Debug menu items for editing actions and views in the admin editor */

import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { editModelDebug } from "@web/services/debug/debug_utils";

const debugRegistry = registry.category("debug");

/**
 * Debug menu item: open the action's form view in the admin editor.
 * @param {{ action: Object, env: Object }} params
 * @returns {Object | null} debug menu item descriptor
 */
function editAction({ action, env }) {
    if (!action.id) {
        return null;
    }
    const description = _t("Action");
    return {
        type: "item",
        description,
        callback: async () => {
            await editModelDebug(env, description, action.type, action.id);
        },
        sequence: 220,
        section: "ui",
    };
}

/**
 * Debug menu item: list all fields for the action's model.
 * @param {{ action: Object, env: Object }} params
 * @returns {Object | null}
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
            const modelId = (
                await env.services.orm.search(
                    "ir.model",
                    [["model", "=", action.res_model]],
                    {
                        limit: 1,
                    },
                )
            )[0];
            await env.services.action.doAction({
                res_model: "ir.model.fields",
                name: description,
                views: [
                    [false, "list"],
                    [false, "form"],
                ],
                domain: [["model_id", "=", modelId]],
                type: "ir.actions.act_window",
                context: {
                    default_model_id: modelId,
                },
            });
        },
        sequence: 250,
        section: "ui",
    };
}

/**
 * Debug menu item: open the ir.model form for the action's model.
 * @param {{ action: Object, env: Object }} params
 * @returns {Object | null}
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
            const modelId = (
                await env.services.orm.search("ir.model", [["model", "=", modelName]], {
                    limit: 1,
                })
            )[0];
            await editModelDebug(env, modelName, "ir.model", modelId);
        },
        sequence: 210,
        section: "ui",
    };
}

/**
 * Debug menu item: list filters for the action's model.
 * @param {{ action: Object, env: Object }} params
 * @returns {Object | null}
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
            // manage_filters
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
 * Debug menu item: list access rights for the action's model.
 * @param {{ accessRights: Object, action: Object, env: Object }} params
 * @returns {Object | null}
 */
function viewAccessRights({ accessRights, action, env }) {
    if (!action.res_model || !accessRights.canSeeModelAccess) {
        return null;
    }
    const description = _t("Access Rights");
    return {
        type: "item",
        description,
        callback: async () => {
            const modelId = (
                await env.services.orm.search(
                    "ir.model",
                    [["model", "=", action.res_model]],
                    {
                        limit: 1,
                    },
                )
            )[0];
            await env.services.action.doAction({
                res_model: "ir.model.access",
                name: description,
                views: [
                    [false, "list"],
                    [false, "form"],
                ],
                domain: [["model_id", "=", modelId]],
                type: "ir.actions.act_window",
                context: {
                    default_model_id: modelId,
                },
            });
        },
        sequence: 350,
        section: "security",
    };
}

/**
 * Debug menu item: list record rules for the action's model.
 * @param {{ accessRights: Object, action: Object, env: Object }} params
 * @returns {Object | null}
 */
function viewRecordRules({ accessRights, action, env }) {
    if (!action.res_model || !accessRights.canSeeRecordRules) {
        return null;
    }
    const description = _t("Model Record Rules");
    return {
        type: "item",
        description: _t("Record Rules"),
        callback: async () => {
            const modelId = (
                await env.services.orm.search(
                    "ir.model",
                    [["model", "=", action.res_model]],
                    {
                        limit: 1,
                    },
                )
            )[0];
            await env.services.action.doAction({
                res_model: "ir.rule",
                name: description,
                views: [
                    [false, "list"],
                    [false, "form"],
                ],
                domain: [["model_id", "=", modelId]],
                type: "ir.actions.act_window",
                context: {
                    default_model_id: modelId,
                },
            });
        },
        sequence: 360,
        section: "security",
    };
}

debugRegistry
    .category("action")
    .add("editAction", /** @type {any} */ (editAction))
    .add("viewFields", /** @type {any} */ (viewFields))
    .add("ViewModel", /** @type {any} */ (ViewModel))
    .add("manageFilters", /** @type {any} */ (manageFilters))
    .add("viewAccessRights", /** @type {any} */ (viewAccessRights))
    .add("viewRecordRules", /** @type {any} */ (viewRecordRules));
