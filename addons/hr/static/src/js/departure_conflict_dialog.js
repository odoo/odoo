/** @odoo-module **/

import { registry } from "@web/core/registry";
import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { _t } from "@web/core/l10n/translation";

registry.category("actions").add("departure_conflict_dialog", async (env, action) => {
    const { title, message, employee_id } = action.params || {};
    const orm = env.services.orm;
    const dialog = env.services.dialog;

    return new Promise((resolve) => {
        dialog.add(ConfirmationDialog, {
            title: title,
            body: message,
            confirmLabel: _t("Cancel Departure"),
            cancelLabel: _t("Discard"),
            confirm: async () => {
                await orm.call("hr.employee", "action_cancel_departure", [employee_id]);
                await env.services.action.doAction({
                    type: "ir.actions.client",
                    tag: "soft_reload",
                    });
                resolve();
            },
            cancel: () => resolve(),
        });
    });
});
