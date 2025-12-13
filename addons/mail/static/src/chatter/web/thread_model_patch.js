import { Record } from "@mail/core/common/record";
import { Thread } from "@mail/core/common/thread_model";
import { compareDatetime } from "@mail/utils/common/misc";
import "@mail/chatter/web_portal/thread_model_patch";

import { patch } from "@web/core/utils/patch";

patch(Thread.prototype, {
    setup() {
        super.setup();
        this.scheduledMessages = Record.many("ScheduledMessage", {
            sort: (a, b) => compareDatetime(a.scheduled_date, b.scheduled_date) || a.id - b.id,
            inverse: "thread",
        });
    },

    /** @param {string[]} requestList */
    async fetchData(requestList) {
        this.isLoadingAttachments =
            this.isLoadingAttachments || requestList.includes("attachments");
        await super.fetchData(requestList);
        if (!this.mainAttachment && this.attachmentsInWebClientView.length > 0) {
            this.setMainAttachmentFromIndex(0);
        }
    },
});
