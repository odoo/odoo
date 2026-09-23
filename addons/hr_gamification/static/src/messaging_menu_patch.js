/** @odoo-module native */
import { MessagingMenu } from "@mail/core/public_web/messaging_menu";
import { makeLogger } from "@web/core/debug/debug_logger";
import { patch } from "@web/core/utils/patch";
import { useService } from "@web/core/utils/hooks";
import { user } from "@web/core/user";

const log = makeLogger("hr_gamification.messaging_menu");

patch(MessagingMenu.prototype, {
    setup() {
        super.setup();
        this.action = useService("action");
        this.orm = useService("orm");
    },

    onClickThread(isMarkAsRead, thread) {
        if (!isMarkAsRead && thread.model === "gamification.badge.user") {
            this.openEmployeeView(thread);
        } else {
            super.onClickThread(...arguments);
        }
    },

    async openEmployeeView(thread) {
        const employeeId = await this.orm.searchRead(
            "hr.employee",
            [
                ["user_id", "=", user.userId],
                ["company_id", "=", user.activeCompany.id],
            ],
            ["id"],
        );

        log.logic("openEmployeeView", () => ({
            badgeUserId: thread.id,
            userId: user.userId,
            companyId: user.activeCompany.id,
            employeeIds: employeeId.map((employee) => employee.id),
        }));
        if (employeeId.length > 0) {
            await this.action.doAction({
                type: "ir.actions.act_window",
                res_model: "hr.employee",
                res_id: employeeId[0].id,
                views: [[false, "form"]],
                target: "current",
                context: {
                    open_badges_tab: true,
                    user_badge_id: thread.id,
                },
            });
            this.markAsRead(thread);
            this.dropdown.close();
        }
    },
});
