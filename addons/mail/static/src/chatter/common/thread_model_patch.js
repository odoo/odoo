import { Thread } from "@mail/core/common/thread_model";
import { fields, patchModel } from "@mail/model/export";
import { compareDatetime } from "@mail/utils/common/misc";

export const threadPatch = patchModel(Thread, {
    setup() {
        super.setup();
        this.scheduledMessages = fields.Many("mail.scheduled.message", { inverse: "thread" });
        this.sortedScheduledMessages = this.computed(() =>
            [...this.scheduledMessages].sort(
                (a, b) => compareDatetime(a.scheduled_date, b.scheduled_date) || a.id - b.id
            )
        );
    },
});
