/** @odoo-module */

import { Activity } from "@mail/new/web/activity/activity";
import { useService } from "@web/core/utils/hooks";
import { patch } from "@web/core/utils/patch";

patch(Activity.prototype, "calendar", {
    setup() {
        this._super();
        this.action = useService("action");
        this.orm = useService("orm");
    },
    async reschedule() {
        const action = await this.orm.call("mail.activity", "action_create_calendar_event", [
            [this.props.data.id],
        ]);
        this.action.doAction(action);
    },
    /**
     * @override
     */
    async unlink() {
        if (this.props.data.calendar_event_id) {
            await this.orm.call("mail.activity", "unlink_w_meeting", [[this.props.data.id]]);
            this.props.onUpdate();
        } else {
            this._super();
        }
    },
});
