import { registerThreadAction } from "@mail/core/common/thread_actions";
import { _t } from "@web/core/l10n/translation";

const employeeIdPromiseByPartner = new WeakMap();

registerThreadAction("hr-view-profile", {
    condition: ({ channel, owner }) =>
        channel?.channel_type === "chat" &&
        owner.props.chatWindow?.isOpen &&
        channel.correspondent?.partner_id?.employeeId &&
        !owner.isDiscussSidebarChannelActions,
    icon: "badge",
    iconClass: "oi-filled",
    name: _t("View Profile"),
    onSelected: async ({ channel, store }) => {
        const action = await store.env.services.orm.call(
            "hr.employee",
            "get_record_default_action",
            [channel.correspondent.partner_id?.employeeId]
        );
        store.env.services.action.doAction(action);
    },
    async setup({ channel }) {
        const partner = channel?.correspondent?.partner_id;
        if (partner && !partner.employeeId) {
            let employeeIdPromise = employeeIdPromiseByPartner.get(partner);
            if (!employeeIdPromise) {
                employeeIdPromise = this.store.env.services.orm.silent.searchRead(
                    "hr.employee",
                    [["user_partner_id", "=", partner.id]],
                    ["id"]
                );
                employeeIdPromiseByPartner.set(partner, employeeIdPromise);
            }
            try {
                const employees = await employeeIdPromise;
                const employeeId = employees[0]?.id;
                if (employeeId) {
                    partner.employeeId = employeeId;
                }
            } finally {
                if (employeeIdPromiseByPartner.get(partner) === employeeIdPromise) {
                    employeeIdPromiseByPartner.delete(partner);
                }
            }
        }
    },
    sequence: 16,
});
