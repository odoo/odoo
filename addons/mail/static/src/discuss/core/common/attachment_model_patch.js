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
    get urlRoute() {
        if (!this.access_token && this.thread?.model === "discuss.channel") {
            return this.isImage
                ? `/discuss/channel/${this.thread.id}/image/${this.id}`
                : `/discuss/channel/${this.thread.id}/attachment/${this.id}`;
        }
        return super.urlRoute;
    },
};
patch(Attachment.prototype, attachmentPatch);
