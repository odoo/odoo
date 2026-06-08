import { DiscussApp } from "@mail/core/public_web/discuss_app/discuss_app_model";
import "@mail/discuss/core/public_web/discuss_app/discuss_app_model_patch";

import { patch } from "@web/core/utils/patch";

patch(DiscussApp.prototype, {
    computeChatCategory() {
        const res = super.computeChatCategory(...arguments);
        res.hideWhenEmpty = true;
        return res;
    },
});
