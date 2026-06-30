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

    /** @type {Parameters<MessagingMenu.prototype.onClickMessage>} */
    onClickMessage(message, { isMiddleClick } = {}) {
        if (message.thread?.model === "gamification.badge.user") {
            this.openEmployeeView(message.thread, { newWindow: isMiddleClick });
        } else {
            super.onClickMessage(...arguments);
        }
    },

    /**
     * @param {import("models").Thread} thread
     * @param {Object} [options]
     * @param {boolean} [options.newWindow]
     */
    async openEmployeeView(thread, { newWindow = false } = {}) {
        const employeeId = await this.orm.searchRead(
            "hr.employee.public",
            [
                ["user_id", "=", user.userId],
                ["company_id", "in", user.activeCompany.id],
            ],
            ["id"]
        );

        if (employeeId.length > 0) {
            await this.action.doAction(
                {
                    type: "ir.actions.act_window",
                    res_model: "hr.employee.public",
                    res_id: employeeId[0].id,
                    views: [[false, "form"]],
                    target: "current",
                    context: {
                        open_badges_tab: true,
                        user_badge_id: thread.id,
                    },
                },
                { newWindow }
            );
            thread.markAllMessagesAsRead();
            this.close?.();
        }
    },
});
