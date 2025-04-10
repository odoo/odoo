import { fields } from "@mail/core/common/record";
import { Thread } from "@mail/core/common/thread_model";
import "@mail/chatter/web_portal/thread_model_patch";

import { patch } from "@web/core/utils/patch";

/** @type {import("models").Thread} */
const threadPatch = {
    setup() {
        super.setup();
        this.scheduledMessages = fields.Many("mail.scheduled.message", {
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
    async fetchThreadData(requestList) {
        this.isLoadingAttachments =
            this.isLoadingAttachments || requestList.includes("attachments");
        await super.fetchThreadData(requestList);
        if (!this.message_main_attachment_id && this.attachmentsInWebClientView.length > 0) {
            this.setMainAttachmentFromIndex(0);
        }
    },
};
patch(Thread.prototype, threadPatch);
