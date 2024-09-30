import { Attachment } from "@mail/core/common/attachment_model";

import { patch } from "@web/core/utils/patch";

patch(Attachment.prototype, {
    get urlQueryParams() {
        return {
            ...super.urlQueryParams,
            ...this.thread?.rpcParams,
        };
    },

    get urlRoute() {
        if (!this.access_token && this.thread?.model !== "discuss.channel") {
            return this.isImage
                ? `/portal/thread/${this.thread.model}/${this.thread.id}/image/${this.id}`
                : `/portal/thread/${this.thread.model}/${this.thread.id}/attachment/${this.id}`;
        }
        return super.urlRoute;
    },
});
