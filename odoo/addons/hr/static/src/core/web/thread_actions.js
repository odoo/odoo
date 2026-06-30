/* @odoo-module */

import { threadActionsRegistry } from "@mail/core/common/thread_actions";
import { _t } from "@web/core/l10n/translation";
import { useComponent } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";

threadActionsRegistry.add("open-hr-profile", {
    condition(component) {
        return (
            component.thread?.type === "chat" &&
            component.props.chatWindow?.isOpen &&
            component.thread.chatPartner.employeeId
        );
    },
    icon: "fa fa-fw fa-id-card",
    name: _t("Open Profile"),
    async open(component) {
        component.actionService.doAction({
            type: "ir.actions.act_window",
            res_id: component.thread.correspondent.employeeId,
            res_model: "hr.employee.public",
            views: [[false, "form"]],
        });
    },
    async setup(action) {
        const component = useComponent();
        const orm = useService("orm");
        let employeeId;
        if (!component.thread?.correspondent?.employeeId && component.thread?.chatPartner) {
            const employees = await orm.silent.searchRead(
                "hr.employee",
                [["user_partner_id", "=", component.thread.chatPartner.id]],
                ["id"]
            );
            employeeId = employees[0]?.id;
            if (employeeId) {
                component.thread.chatPartner.employeeId = employeeId;
            }
        }
    },
    sequence: 16,
});
