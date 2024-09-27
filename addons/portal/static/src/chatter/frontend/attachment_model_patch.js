import { Attachment } from "@mail/core/common/attachment_model";

import { patch } from "@web/core/utils/patch";

patch(Attachment.prototype, {
    get urlQueryParams() {
        const urlQueryParams = super.urlQueryParams;
        if (this.env.inPortalChatter) {
            Object.assign(urlQueryParams, this.thread.securityParams)
        }
        return urlQueryParams;
    },

    get urlRoute() {
        if (!this.accessToken && this.thread?.model !== "discuss.channel") {
            return this.isImage
                ? `/portal/thread/${this.thread.model}/${this.thread.id}/image/${this.id}`
                : `/portal/thread/${this.thread.model}/${this.thread.id}/attachment/${this.id}`;
        }
        return super.urlRoute;
    },
});
