/* @odoo-module */

import { Attachment } from "@mail/core/common/attachment_model";
import { patch } from "@web/core/utils/patch";

patch(Attachment.prototype, {
    get urlQueryParams() {
        return {
            ...super.urlQueryParams,
            guest_token: this._store.env.services["im_livechat.livechat"].guestToken,
        };
    },
    get urlRoute() {
        if (!this.accessToken && this.originThread?.model === "discuss.channel") {
            return this.isImage
                ? `/im_livechat/cors/channel/${this.originThread.id}/image/${this.id}`
                : `/im_livechat/cors/channel/${this.originThread.id}/attachment/${this.id}`;
        }
        return super.urlRoute;
    },
});
