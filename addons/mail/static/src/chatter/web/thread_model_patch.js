import { Thread } from "@mail/core/common/thread_model";
import "@mail/chatter/web_portal/thread_model_patch";

import { patch } from "@web/core/utils/patch";

patch(Thread.prototype, {
    /** @param {string[]} requestList */
    async fetchData(requestList) {
        this.isLoadingAttachments =
            this.isLoadingAttachments || requestList.includes("attachments");
        const result = await super.fetchData(requestList);
        if (!this.mainAttachment && this.attachmentsInWebClientView.length > 0) {
            this.setMainAttachmentFromIndex(0);
        }
        if ("attachments" in result) {
            Object.assign(this, {
                areAttachmentsLoaded: true,
                isLoadingAttachments: false,
            });
        }
        return result;
    },
});
