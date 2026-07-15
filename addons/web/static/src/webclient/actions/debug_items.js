import { _t } from "@web/core/l10n/translation";
import { editModelDebug } from "@web/core/debug/debug_utils";
import { registry } from "@web/core/registry";
import { plugin } from "@odoo/owl";
import { ORM } from "@web/core/orm_plugin";
import { useService } from "@web/core/utils/hooks";

const debugRegistry = registry.category("debug");

function editAction({ action }) {
    const actionService = useService("action");
    if (!action.id) {
        return null;
    }
    const description = _t("Action");
    return {
        type: "item",
        description,
        callback: () => {
            editModelDebug(actionService, description, action.type, action.id);
        },
        sequence: 220,
        section: "ui",
    };
}

function viewFields({ action }) {
    const actionService = useService("action");
    const orm = plugin(ORM);

    if (!action.res_model) {
        return null;
    }
    const description = _t("Fields");
    return {
        type: "item",
        description,
        callback: async () => {
            const modelId = (
                await orm.search("ir.model", [["model", "=", action.res_model]], {
                    limit: 1,
                })
            )[0];
            actionService.doAction({
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

function ViewModel({ action }) {
    const actionService = useService("action");
    const orm = plugin(ORM);

    if (!action.res_model) {
        return null;
    }
    const modelName = action.res_model;
    return {
        type: "item",
        description: _t("Model: %s", modelName),
        callback: async () => {
            const modelId = (
                await orm.search("ir.model", [["model", "=", modelName]], {
                    limit: 1,
                })
            )[0];
            editModelDebug(actionService, modelName, "ir.model", modelId);
        },
        sequence: 210,
        section: "ui",
    };
}

function manageFilters({ action }) {
    const actionService = useService("action");
    if (!action.res_model) {
        return null;
    }
    const description = _t("Filters");
    return {
        type: "item",
        description,
        callback: () => {
            // manage_filters
            actionService.doAction({
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

function viewAccessRights({ accessRights, action }) {
    const actionService = useService("action");
    const orm = plugin(ORM);

    if (!action.res_model || !accessRights.canSeeAccess) {
        return null;
    }
    const description = _t("Access Rights");
    return {
        type: "item",
        description,
        callback: async () => {
            const modelId = (
                await orm.search("ir.model", [["model", "=", action.res_model]], {
                    limit: 1,
                })
            )[0];
            actionService.doAction({
                res_model: "ir.access",
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

debugRegistry
    .category("action")
    .add("editAction", editAction)
    .add("viewFields", viewFields)
    .add("ViewModel", ViewModel)
    .add("manageFilters", manageFilters)
    .add("viewAccessRights", viewAccessRights);
