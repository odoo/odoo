import { Thread } from "@mail/core/common/thread_model";
import { fields } from "@mail/model/export";
import { compareDatetime } from "@mail/utils/common/misc";

import { patch } from "@web/core/utils/patch";

/** @type {import("models").Thread} */
const threadPatch = {
    setup() {
        super.setup();
        this.scheduledMessages = fields.Many("mail.scheduled.message", {
            sort: (a, b) => compareDatetime(a.scheduled_date, b.scheduled_date) || a.id - b.id,
            inverse: "thread",
        });
    },
};
patch(Thread.prototype, threadPatch);
