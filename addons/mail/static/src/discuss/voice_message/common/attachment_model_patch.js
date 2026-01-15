import { Attachment } from "@mail/core/common/attachment_model";
import { fields } from "@mail/core/common/record";
import { patch } from "@web/core/utils/patch";

/** @type {import("models").Attachment} */
const attachmentPatch = {
    setup() {
        this.voice_ids = fields.Many("discuss.voice.metadata");
    },
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
    get voice() {
        return this.voice_ids.length > 0;
    },
};
patch(Attachment.prototype, attachmentPatch);
