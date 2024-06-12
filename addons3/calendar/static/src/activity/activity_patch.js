/** @odoo-module */

import { Activity } from "@mail/core/web/activity";
import { useService } from "@web/core/utils/hooks";
import { patch } from "@web/core/utils/patch";

patch(Activity.prototype, {
    setup() {
        super.setup();
        this.orm = useService("orm");
    },
    async onClickReschedule() {
        await this.env.services["mail.activity"].rescheduleMeeting(this.props.data.id);
    },
    /**
     * @override
     */
    async unlink() {
        if (this.props.data.calendar_event_id) {
            const thread = this.thread;
            this.activityService.delete(this.props.data);
            await this.orm.call("mail.activity", "unlink_w_meeting", [[this.props.data.id]]);
            this.props.onUpdate(thread);
        } else {
            super.unlink();
        }
    },
});
