/** @odoo-module **/

// ensure mail override is applied first.
import "@mail/../tests/helpers/mock_server/models/mail_activity";

import { patch } from "@web/core/utils/patch";
import { MockServer } from "@web/../tests/helpers/mock_server";

patch(MockServer.prototype, {
    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @override
     */
    async _performRPC(route, args) {
        if (args.model === "mail.activity" && args.method === "action_create_calendar_event") {
            return {
                type: "ir.actions.act_window",
                name: "Meetings",
                res_model: "calendar.event",
                view_mode: "calendar",
                views: [[false, "calendar"]],
                target: "current",
            };
        }
        if (args.model === "mail.activity" && args.method === "unlink_w_meeting") {
            const activities = this.getRecords("mail.activity", [["id", "in", args.args[0]]]);
            const eventIds = activities.map((act) => act.calendar_event_id);
            const res = this.mockUnlink("mail.activity", args.args[0]);
            this.mockUnlink("calendar.event", eventIds);
            return res;
        }
        return super._performRPC(...arguments);
    },
});
