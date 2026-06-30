import { MessagingMenu } from "@mail/core/public_web/messaging_menu/messaging_menu";
import { patch } from "@web/core/utils/patch";
import { useService } from "@web/core/utils/hooks";
import { user } from "@web/core/user";

patch(MessagingMenu.prototype, {
    setup() {
        super.setup();
        this.action = useService("action");
        this.orm = useService("orm");
    },

    onClickMessage(message) {
        if (message.thread?.model === "gamification.badge.user") {
            this.openEmployeeView(message.thread);
        } else {
            super.onClickMessage(message);
        }
    },

    async openEmployeeView(thread) {
        const employeeId = await this.orm.searchRead(
            "hr.employee.public",
            [
                ["user_id", "=", user.userId],
                ["company_id", "in", user.activeCompany.id],
            ],
            ["id"]
        );

        if (employeeId.length > 0) {
            await this.action.doAction({
                type: "ir.actions.act_window",
                res_model: "hr.employee.public",
                res_id: employeeId[0].id,
                views: [[false, "form"]],
                target: "current",
                context: {
                    open_badges_tab: true,
                    user_badge_id: thread.id,
                },
            });
            thread.markAllMessagesAsRead();
            this.close?.();
        }
    },
});
