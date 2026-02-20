import { Thread } from "@mail/core/common/thread_model";

import { patch } from "@web/core/utils/patch";

const threadPatch = {
    getFetchParams() {
        return {
            ...super.getFetchParams(),
            ...(this.inPortal ? { only_portal: true } : {}),
        };
    },
};
patch(Thread.prototype, threadPatch);
