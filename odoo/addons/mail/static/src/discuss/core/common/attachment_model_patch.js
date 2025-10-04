/* @odoo-module */

import { Attachment } from "@mail/core/common/attachment_model";

import { patch } from "@web/core/utils/patch";

patch(Attachment.prototype, {
    get isDeletable() {
        if (this.message && this.originThread?.model === "discuss.channel") {
            return this.message.editable;
        }
        return super.isDeletable;
    },
    get urlRoute() {
        if (!this.accessToken && this.originThread?.model === "discuss.channel") {
            return this.isImage
                ? `/discuss/channel/${this.originThread.id}/image/${this.id}`
                : `/discuss/channel/${this.originThread.id}/attachment/${this.id}`;
        }
        return super.urlRoute;
    },
});
