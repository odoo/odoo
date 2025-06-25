import { Record } from "@mail/core/common/record";
import { Thread } from "@mail/core/common/thread_model";
import "@mail/chatter/web_portal/thread_model_patch";

import { patch } from "@web/core/utils/patch";

patch(Thread.prototype, {
    setup() {
        super.setup();
        this.scheduledMessages = Record.many("ScheduledMessage", {
            sort: (a, b) => {
                if (a.scheduled_date === b.scheduled_date) {
                    return a.id - b.id;
                }
                return a.scheduled_date < b.scheduled_date ? -1 : 1;
            },
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
