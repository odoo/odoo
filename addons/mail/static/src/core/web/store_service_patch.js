import { Record } from "@mail/core/common/record";
import { Store } from "@mail/core/common/store_service";
import { compareDatetime } from "@mail/utils/common/misc";

import { patch } from "@web/core/utils/patch";

/** @type {import("models").Store} */
const StorePatch = {
    setup() {
        super.setup(...arguments);
        this.activityCounter = 0;
        this.activity_counter_bus_id = 0;
        this.activityGroups = Record.attr([], {
            onUpdate() {
                this.onUpdateActivityGroups();
            },
            sort(g1, g2) {
                /**
                 * Sort by model ID ASC but always place the activity group for "mail.activity" model at
                 * the end (other activities).
                 */
                const getSortId = (activityGroup) =>
                    activityGroup.model === "mail.activity" ? Number.MAX_VALUE : activityGroup.id;
                return getSortId(g1) - getSortId(g2);
            },
        });
    },
    getNeedactionChannels() {
        return this.getRecentChannels().filter((channel) => channel.importantCounter > 0);
    },
    getRecentChannels() {
        return Object.values(this.Thread.records)
            .filter((thread) => thread.model === "discuss.channel")
            .sort((a, b) => compareDatetime(b.lastInterestDt, a.lastInterestDt) || b.id - a.id);
    },
    onUpdateActivityGroups() {},
};
patch(Store.prototype, StorePatch);
