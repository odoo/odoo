/** @odoo-module **/

import { plugin } from "@odoo/owl";
import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { _t } from "@web/core/l10n/translation";
import { ORM } from "@web/core/orm_plugin";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

registry.category("actions").add("departure_conflict_dialog", async (env, actionDescr) => {
    const { title, message, employee_id } = actionDescr.params || {};
    const orm = plugin(ORM);
    const dialog = useService("dialog");
    const action = useService("action");

    return new Promise((resolve) => {
        dialog.add(ConfirmationDialog, {
            title: title,
            body: message,
            confirmLabel: _t("Cancel Departure"),
            cancelLabel: _t("Discard"),
            confirm: async () => {
                await orm.call("hr.employee", "action_cancel_departure", [employee_id]);
                await action.doAction({
                    type: "ir.actions.client",
                    tag: "soft_reload",
                });
                resolve();
            },
            cancel: () => resolve(),
        });
    });
});
