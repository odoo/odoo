import { Thread } from "@mail/core/common/thread_model";

import { patch } from "@web/core/utils/patch";

patch(Thread.prototype, {
    getFetchParams() {
        const fetchParams = super.getFetchParams();
        if (this.model === "discuss.channel" || this.model === "mail.box") {
            return fetchParams;
        }
        return {
            ...fetchParams,
            portal: true,
        };
    },
});
