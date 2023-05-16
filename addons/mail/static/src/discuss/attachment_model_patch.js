/* @odoo-module */

import { Attachment } from "@mail/attachments/attachment_model";
import { patch } from "@web/core/utils/patch";

patch(Attachment.prototype, "discuss", {
    get isDeletable() {
        if (this.message && this.originThread?.model === "discuss.channel") {
            return this.message.editable;
        }
        return this._super();
    },
    get urlRoute() {
        if (!this.accessToken && this.originThread?.model === "discuss.channel") {
            return this.isImage
                ? `/discuss/channel/${this.originThread.id}/image/${this.id}`
                : `/discuss/channel/${this.originThread.id}/attachment/${this.id}`;
        }
        return this._super();
    },
});
