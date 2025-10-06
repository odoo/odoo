import { Attachment } from "@mail/core/common/attachment_model";

import { patch } from "@web/core/utils/patch";

/** @type {import("models").Attachment} */
const attachmentPatch = {
    get isDeletable() {
        if (this.thread?.model === "discuss.channel") {
            return this.ownership_token;
        }
        return super.isDeletable;
    },
};
patch(Attachment.prototype, attachmentPatch);
