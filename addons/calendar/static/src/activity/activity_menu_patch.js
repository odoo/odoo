/** @odoo-module */

import { ActivityMenu } from "@mail/core/web/activity_menu";
import { patch } from "@web/core/utils/patch";
import fieldUtils from "@web/legacy/js/fields/field_utils";
import time from "@web/legacy/js/core/time";

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
                            .format(time.getLangTimeFormat());
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
