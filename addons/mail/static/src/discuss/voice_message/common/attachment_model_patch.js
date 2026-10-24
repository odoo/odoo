import { Attachment } from "@mail/core/common/attachment_model";
import { patchModel } from "@mail/model/export";

export const attachmentPatch = patchModel(Attachment, {
    /** @returns {boolean} */
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
    /** @returns {boolean} */
    get voice() {
        return this.voice_ids.length > 0;
    },
});
