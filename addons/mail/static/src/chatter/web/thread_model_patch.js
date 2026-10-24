import { Thread } from "@mail/core/common/thread_model";
import { patchModel } from "@mail/model/export";
import "@mail/chatter/web_portal_project/thread_model_patch";

export const threadPatch = patchModel(Thread, {
    /** @param {string[]} requestList */
    async fetchThreadData(requestList) {
        this.isLoadingAttachments =
            this.isLoadingAttachments || requestList.includes("attachments");
        await super.fetchThreadData(...arguments);
        if (!this.message_main_attachment_id && this.attachmentsInWebClientView.length > 0) {
            this.setMainAttachmentFromIndex(0);
        }
    },

    /** @returns {string[]} */
    get fullComposerCloseRequestList() {
        return super.fullComposerCloseRequestList.concat([
            "defaultSubject",
            "scheduledMessages",
            "suggestedSubject",
        ]);
    },
});
