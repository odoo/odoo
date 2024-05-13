import { Attachment } from "@mail/core/common/attachment_model";

import { patch } from "@web/core/utils/patch";

patch(Attachment.prototype, {
    get isDeletable() {
        if (this.thread?.model !== "discuss.channel") {
            return false;
        }
        return super.isDeletable;
    },
});
