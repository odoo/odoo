import { Thread } from "@mail/core/common/thread_model";

import { patch } from "@web/core/utils/patch";

patch(Thread.prototype, {
    getFetchParams() {
        const params = super.getFetchParams(...arguments);
        if (this.model !== "discuss.channel") {
            params["rating_include"] = true;
        }
        return params;
    },
});
