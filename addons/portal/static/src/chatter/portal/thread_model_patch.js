import { Thread } from "@mail/core/common/thread_model";

import { patch } from "@web/core/utils/patch";

const threadPatch = {
    getFetchParams() {
        const fetchParams = super.getFetchParams();
        if (this.model === "discuss.channel" || this.model === "mail.box") {
            return fetchParams;
        }
        return {
            ...fetchParams,
            in_portal: true,
        };
    },
};
patch(Thread.prototype, threadPatch);
