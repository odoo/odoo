import { _t } from "@web/core/l10n/translation";
import { editModelDebug } from "@web/core/debug/debug_utils";
import { registry } from "@web/core/registry";

const debugRegistry = registry.category("debug");

function editAction({ action, env }) {
    if (!action.id) {
        return null;
    }
    const description = _t("Action");
    return {
        type: "item",
        description,
        callback: () => {
            editModelDebug(env, description, action.type, action.id);
        },
        sequence: 220,
        section: "ui",
    };
}

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
                await env.services.orm.search("ir.model", [["model", "=", action.res_model]], {
                    limit: 1,
                })
            )[0];
            env.services.action.doAction({
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
            editModelDebug(env, modelName, "ir.model", modelId);
        },
        sequence: 210,
        section: "ui",
    };
}

function manageFilters({ action, env }) {
    if (!action.res_model) {
        return null;
    }
    const description = _t("Filters");
    return {
        type: "item",
        description,
        callback: () => {
            // manage_filters
            env.services.action.doAction({
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
                await env.services.orm.search("ir.model", [["model", "=", action.res_model]], {
                    limit: 1,
                })
            )[0];
            env.services.action.doAction({
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
                await env.services.orm.search("ir.model", [["model", "=", action.res_model]], {
                    limit: 1,
                })
            )[0];
            env.services.action.doAction({
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
    .add("editAction", editAction)
    .add("viewFields", viewFields)
    .add("ViewModel", ViewModel)
    .add("manageFilters", manageFilters)
    .add("viewAccessRights", viewAccessRights)
    .add("viewRecordRules", viewRecordRules);
