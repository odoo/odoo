/** @odoo-module */

import { ActivityMenu } from "@mail/core/web/activity_menu";
import { patch } from "@web/core/utils/patch";
import { deserializeDateTime, formatDateTime } from "@web/core/l10n/dates";
import { localization } from "@web/core/l10n/localization";

patch(ActivityMenu.prototype, "calendar", {
    async fetchSystrayActivities() {
        await this._super();
        for (const group of Object.values(this.store.activityGroups)) {
            if (group.type === "meeting") {
                for (const meeting of group.meetings) {
                    if (meeting.start) {
                        const date = deserializeDateTime(meeting.start);
                        meeting.formattedStart = formatDateTime(date, { format: localization.timeFormat });
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
