import { ThreadService } from "@mail/core/common/thread_service";
import "@mail/chatter/web_portal/thread_service_patch";

import { patch } from "@web/core/utils/patch";

patch(ThreadService.prototype, {
    /**
     * @param {import("models").Thread} thread
     * @param {string[]} requestList
     */
    async fetchData(thread, requestList) {
        thread.isLoadingAttachments =
            thread.isLoadingAttachments || requestList.includes("attachments");
        const result = await super.fetchData(thread, requestList);
        if (!thread.mainAttachment && thread.attachmentsInWebClientView.length > 0) {
            this.setMainAttachmentFromIndex(thread, 0);
        }
        if ("attachments" in result) {
            Object.assign(thread, {
                areAttachmentsLoaded: true,
                isLoadingAttachments: false,
            });
        }
        return result;
    },
});
