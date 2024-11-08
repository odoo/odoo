import { Attachment } from "@mail/core/common/attachment_model";
import { patch } from "@web/core/utils/patch";

/** @type {import("models").Attachment} */
const attachmentPatch = {
    get isViewable() {
        return !this.voice && super.isViewable;
    },
    delete() {
        if (this.voice && this.id > 0) {
            this.store.env.services["discuss.voice_message"].activePlayer = null;
        }
        super.delete(...arguments);
    },
    onClickAttachment(attachment) {
        if (!attachment.voice) {
            super.onClickAttachment(attachment);
        }
    },
};
patch(Attachment.prototype, attachmentPatch);
