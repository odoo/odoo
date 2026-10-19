import { Store } from "@mail/core/common/store_service";

import { deserializeDateTime } from "@web/core/l10n/dates";
import { formatDateTime } from "@web/views/fields/formatters";
import { patch } from "@web/core/utils/patch";

/** @type {import("models").Store} */
const StorePatch = {
    onUpdateActivityGroups() {
        super.onUpdateActivityGroups(...arguments);
        for (const group of Object.values(this.activityGroups)) {
            if (group.type === "meeting") {
                for (const meeting of group.meetings) {
                    if (meeting.start) {
                        const date = deserializeDateTime(meeting.start);
                        meeting.formattedStart = formatDateTime(date, {
                            showDate: false,
                            showSeconds: false,
                        });
                    }
                }
            }
        }
    },
};
patch(Store.prototype, StorePatch);
