import { Activity } from "@mail/core/web/activity";
import { useService } from "@web/core/utils/hooks";
import { patch } from "@web/core/utils/patch";

patch(Activity.prototype, {
    setup() {
        super.setup();
        this.orm = useService("orm");
    },
    async onClickReschedule() {
        await this.props.activity.rescheduleMeeting();
    },
    /**
     * @override
     */
    async unlink() {
        if (this.props.activity.calendar_event_id) {
            const thread = this.thread;
            this.props.activity.remove();
            await this.orm.call("mail.activity", "unlink_w_meeting", [[this.props.activity.id]]);
            this.props.onActivityChanged(thread);
        } else {
            super.unlink();
        }
    },
});
