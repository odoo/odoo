import { Attachment } from "@mail/core/common/attachment_model";
import { fields } from "@mail/model/export";

import { patch } from "@web/core/utils/patch";

/** @type {import("models").Attachment} */
const attachmentPatch = {
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
};
patch(Attachment.prototype, attachmentPatch);
