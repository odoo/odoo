import { fields } from "@mail/model/export";
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
        this.pendingPostScheduledMessages = [];
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
    handleNewScheduleMessageData(data) {
        this.pendingPostScheduledMessages.push(data.message_id);
        super.handleNewScheduleMessageData(data);
    },
    isPendingScheduledMessage(scheduledMessage) {
        return this.pendingPostScheduledMessages.includes(scheduledMessage.id);
    },
    async cancelPendingScheduledMessage(scheduledMessage) {
        if (this.isPendingScheduledMessage(scheduledMessage)) {
            if (!this.composer.composerText) {
                await scheduledMessage.resetAttachmentsInComposer();
                // TODO: might have more than just attachments, to check
                this.composer.attachments = scheduledMessage.attachment_ids;
                this.composer.insertText(scheduledMessage.textContent, 0, {
                    moveCursorToEnd: true,
                });
            }
            this.pendingPostScheduledMessages = this.pendingPostScheduledMessages.filter(
                (id) => id !== scheduledMessage.id
            );
            return true;
        }
    },
};
patch(Thread.prototype, threadPatch);
