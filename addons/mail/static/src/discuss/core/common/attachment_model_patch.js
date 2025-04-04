import { Attachment } from "@mail/core/common/attachment_model";

import { patch } from "@web/core/utils/patch";

/** @type {import("models").Attachment} */
const attachmentPatch = {
    get isDeletable() {
        if (this.message && this.thread?.model === "discuss.channel") {
            return this.message.editable;
        }
        return super.isDeletable;
    },
};
patch(Attachment.prototype, attachmentPatch);
