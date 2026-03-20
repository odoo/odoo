import { Thread } from "@mail/core/common/thread_model";
import "@mail/chatter/web_portal_project/thread_model_patch";

import { patch } from "@web/core/utils/patch";

/** @type {import("models").Thread} */
const threadPatch = {
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
