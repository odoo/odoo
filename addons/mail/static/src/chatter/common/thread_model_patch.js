import { Thread } from "@mail/core/common/thread_model";
import { fields } from "@mail/model/export";
import { compareDatetime } from "@mail/utils/common/misc";

import { patch } from "@web/core/utils/patch";

/** @type {import("models").Thread} */
const threadPatch = {
    setup() {
        super.setup();
        this.scheduledMessages = fields.Many("mail.scheduled.message", { inverse: "thread" });
    },
    get sortedScheduledMessages() {
        return [...this.scheduledMessages].sort(
            (a, b) => compareDatetime(a.scheduled_date, b.scheduled_date) || a.id - b.id
        );
    },
};
patch(Thread.prototype, threadPatch);
