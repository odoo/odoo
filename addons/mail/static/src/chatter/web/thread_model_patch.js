import { Record } from "@mail/core/common/record";
import { Thread } from "@mail/core/common/thread_model";
import { compareDatetime } from "@mail/utils/common/misc";
import "@mail/chatter/web_portal/thread_model_patch";

import { patch } from "@web/core/utils/patch";

/** @type {import("models").Thread} */
const threadPatch = {
    setup() {
        super.setup();
        this.scheduledMessages = Record.many("mail.scheduled.message", {
            sort: (a, b) => compareDatetime(a.scheduled_date, b.scheduled_date) || a.id - b.id,
            inverse: "thread",
        });
    },

    /** @param {string[]} requestList */
    async fetchThreadData(requestList) {
        this.isLoadingAttachments =
            this.isLoadingAttachments || requestList.includes("attachments");
        await super.fetchThreadData(requestList);
        if (!this.mainAttachment && this.attachmentsInWebClientView.length > 0) {
            this.setMainAttachmentFromIndex(0);
        }
    },
};
patch(Thread.prototype, threadPatch);
