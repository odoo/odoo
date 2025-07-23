import { registerThreadAction } from "@mail/core/common/thread_actions";
import { _t } from "@web/core/l10n/translation";
import { useService } from "@web/core/utils/hooks";

registerThreadAction("open-hr-profile", {
    condition(component) {
        return (
            component.thread?.channel_type === "chat" &&
            component.props.chatWindow?.isOpen &&
            component.thread.correspondent?.partner_id?.employeeId
        );
    },
    icon: "fa fa-fw fa-id-card",
    iconLarge: "fa fa-lg fa-fw fa-id-card",
    name: _t("Open Profile"),
    async open(component) {
        component.actionService.doAction({
            type: "ir.actions.act_window",
            res_id: component.thread.correspondent.partner_id?.employeeId,
            res_model: "hr.employee.public",
            views: [[false, "form"]],
        });
    },
    async setup(component) {
        const orm = useService("orm");
        let employeeId;
        if (
            !component.thread?.correspondent?.partner_id?.employeeId &&
            component.thread?.correspondent
        ) {
            const employees = await orm.silent.searchRead(
                "hr.employee",
                [["user_partner_id", "=", component.thread.correspondent.partner_id?.id]],
                ["id"]
            );
            employeeId = employees[0]?.id;
            if (employeeId) {
                component.thread.correspondent.partner_id.employeeId = employeeId;
            }
        }
    },
    sequence: 16,
});
