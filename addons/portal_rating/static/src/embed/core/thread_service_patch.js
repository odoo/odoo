/* @odoo-module */

import { ThreadService } from "@mail/core/common/thread_service";

import { patch } from "@web/core/utils/patch";

patch(ThreadService.prototype, {
    getFetchParams(thread) {
        const params = super.getFetchParams(...arguments);
        if (thread.type === "chatter") {
            params["rating_include"] = true;
        }
        return params;
    },
});
