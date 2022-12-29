/** @odoo-module */

import { ActivityMenu } from "@mail/new/web/activity/activity_menu";
import { patch } from "@web/core/utils/patch";
import fieldUtils from "web.field_utils";
import { getLangTimeFormat } from "web.time";

patch(ActivityMenu.prototype, "calendar", {
    async fetchSystrayActivities() {
        await this._super();
        for (const group of Object.values(this.store.activityGroups)) {
            if (group.type === "meeting") {
                for (const meeting of group.meetings) {
                    if (meeting.start) {
                        meeting.formattedStart = moment(
                            fieldUtils.parse.datetime(meeting.start, false, { isUTC: true })
                        )
                            .local()
                            .format(getLangTimeFormat());
                    }
                }
            }
        }
    },

    openActivityGroup(group) {
        if (group.model === "calendar.event") {
            document.body.click();
            this.action.doAction("calendar.action_calendar_event", {
                additionalContext: {
                    default_mode: "day",
                    search_default_mymeetings: 1,
                },
                clearBreadcrumbs: true,
            });
        } else {
            this._super(...arguments);
        }
    },
});
