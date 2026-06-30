import { DiscussApp } from "@mail/core/public_web/discuss_app_model";
import "@mail/discuss/core/public_web/discuss_app_model_patch";

import { patch } from "@web/core/utils/patch";

patch(DiscussApp.prototype, {
    computeChats() {
        const res = super.computeChats(...arguments);
        res.hideWhenEmpty = true;
        return res;
    },
});
