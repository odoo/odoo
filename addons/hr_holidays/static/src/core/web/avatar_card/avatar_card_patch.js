import { AvatarCard } from "@mail/core/web/avatar_card/avatar_card";
import { patch } from "@web/core/utils/patch";
import { useService } from "@web/core/utils/hooks";

/** @type {AvatarCard} */
const avatarCardTimeOffPatch = {
    setup() {
        super.setup(...arguments);
        this.orm = useService("orm");
        this.actionService = useService("action");
    },

    get leaveSummary() {
        return this.employee?.avatar_leave_summary || [];
    },

    async onTimeOffClick() {
        const employeeId = this.employee?.id;
        if (!employeeId) {
            return;
        }
        const action = await this.orm.call("hr.employee", "action_time_off_dashboard", [
            [employeeId],
        ]);
        if (action) {
            await this.actionService.doAction(action);
        }
    },

    /** @override */
    get hasFooter() {
        return (Boolean(this.employee) && this.leaveSummary.length) || super.hasFooter;
    },
};

patch(AvatarCard.prototype, avatarCardTimeOffPatch);
