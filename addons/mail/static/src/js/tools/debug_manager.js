/** @odoo-module **/

import { registry } from "@web/core/registry";

export function manageMessages({ component, env }) {
    const resId = component.model.root.resId;
    if (!resId) {
        return null; // No record
    }
    const description = env._t("Manage Messages");
    return {
        type: "item",
        description,
        callback: () => {
            env.services.action.doAction({
                res_model: "mail.message",
                name: description,
                views: [
                    [false, "list"],
                    [false, "form"],
                ],
                type: "ir.actions.act_window",
                domain: [
                    ["res_id", "=", resId],
                    ["model", "=", component.props.resModel],
                ],
                context: {
                    default_res_model: component.props.resModel,
                    default_res_id: resId,
                },
            });
        },
        sequence: 325,
    };
}

registry.category("debug").category("form").add("mail.manageMessages", manageMessages);

// Legacy form views compatibility: remove as soon as we no longer support legacy views
function legacyManageMessages({ action, component, env }) {
    const selectedIds = component.widget.getSelectedIds();
    if (!selectedIds.length) {
        return null; // No record
    }
    const description = env._t("Manage Messages");
    return {
        type: "item",
        description,
        callback: () => {
            env.services.action.doAction({
                res_model: "mail.message",
                name: description,
                views: [
                    [false, "list"],
                    [false, "form"],
                ],
                type: "ir.actions.act_window",
                domain: [
                    ["res_id", "=", selectedIds[0]],
                    ["model", "=", action.res_model],
                ],
                context: {
                    default_res_model: action.res_model,
                    default_res_id: selectedIds[0],
                },
            });
        },
        sequence: 325,
    };
}
registry.category("debug").category("form_legacy").add("mail.manageMessages", legacyManageMessages);
