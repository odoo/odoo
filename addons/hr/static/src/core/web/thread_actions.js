import { registerThreadAction } from "@mail/core/common/thread_actions";
import { _t } from "@web/core/l10n/translation";

registerThreadAction("hr-view-profile", {
    condition: ({ channel, owner }) =>
        channel?.channel_type === "chat" &&
        owner.props.chatWindow?.isOpen &&
        channel.correspondent?.partner_id?.employeeId &&
        !owner.isDiscussSidebarChannelActions,
    icon: "fa fa-fw fa-id-card",
    name: _t("View Profile"),
    onSelected: async ({ channel, store }) => {
        const action = await store.env.services.orm.call("hr.employee", "get_record_default_action", [
            channel.correspondent.partner_id?.employeeId,
        ]);
        store.env.services.action.doAction(action);
    },
    async setup({ channel }) {
        let employeeId;
        if (channel?.correspondent?.partner_id && !channel.correspondent.partner_id.employeeId) {
            const employees = await this.store.env.services.orm.silent.searchRead(
                "hr.employee",
                [["user_partner_id", "=", channel.correspondent.partner_id.id]],
                ["id"]
            );
            employeeId = employees[0]?.id;
            if (employeeId) {
                channel.correspondent.partner_id.employeeId = employeeId;
            }
        }
    },
    sequence: 16,
});
