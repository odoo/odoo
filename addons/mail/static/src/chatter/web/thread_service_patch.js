/* @odoo-module */

import { ThreadService } from "@mail/core/common/thread_service";

import { patch } from "@web/core/utils/patch";

patch(ThreadService.prototype, {
    async fetchData(
        thread,
        requestList = ["activities", "followers", "attachments", "messages", "suggestedRecipients"]
    ) {
        const result = super.fetchData(...arguments);
        if ("mainAttachment" in result) {
            thread.mainAttachment = result.mainAttachment.id
                ? this.store.Attachment.insert(result.mainAttachment)
                : undefined;
        }
        if (!thread.mainAttachment && thread.attachmentsInWebClientView.length > 0) {
            this.setMainAttachmentFromIndex(thread, 0);
        }
        return result;
    },
});
