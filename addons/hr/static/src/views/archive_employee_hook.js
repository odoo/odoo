/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { useService } from "@web/core/utils/hooks";
import { useComponent } from "@odoo/owl";

export function useArchiveEmployee() {
    const component = useComponent();
    const action = useService("action");
    return (ids) => {
        action.doAction(
            {
                type: "ir.actions.act_window",
                name: _t("Employee Termination"),
                res_model: "hr.departure.wizard",
                views: [[false, "form"]],
                view_mode: "form",
                target: "new",
                context: {
                    active_ids: ids,
                    toggle_active: true,
                },
            },
            {
                onClose: async () => {
                    await component.model.load();
                },
            }
        );
    };
}
