import { Store } from "@mail/core/common/store_plugin";
import { patchModel } from "@mail/model/export";

import { deserializeDateTime } from "@web/core/l10n/dates";
import { formatDateTime } from "@web/views/fields/formatters";

export const StorePatch = patchModel(Store, {
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
});
