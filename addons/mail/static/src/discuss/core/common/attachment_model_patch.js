import { Attachment } from "@mail/core/common/attachment_model";
import { fields, patchModel } from "@mail/model/export";

export const attachmentPatch = patchModel(Attachment, {
    setup() {
        super.setup(...arguments);
        this.voice_ids = fields.Many("discuss.voice.metadata");
    },
    get isDeletable() {
        if (this.message && this.thread?.channel) {
            return this.message.editable;
        }
        return super.isDeletable;
    },
});
