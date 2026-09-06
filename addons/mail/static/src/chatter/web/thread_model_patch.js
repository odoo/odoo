import { Thread } from "@mail/core/common/thread_model";

import { patch } from "@web/core/utils/patch";

/** @type {import("models").Thread} */
const threadPatch = {
    /** @param {string[]} requestList */
    async fetchThreadData(requestList) {
        this.isLoadingAttachments =
            this.isLoadingAttachments || requestList.includes("attachments");
        await this.store.fetchStoreData("mail.thread", {
            request_list: requestList.filter((r) => r !== "messages"),
            thread_id: this.id,
            thread_model: this.model,
        });
        if (!this.message_main_attachment_id && this.attachmentsInWebClientView.length > 0) {
            this.setMainAttachmentFromIndex(0);
        }
    },

    get fullComposerCloseRequestList() {
        return ["defaultSubject", "messages", "scheduledMessages", "suggestedSubject"];
    },
};
patch(Thread.prototype, threadPatch);
