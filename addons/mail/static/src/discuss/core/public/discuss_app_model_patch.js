import { DiscussApp } from "@mail/core/public_web/discuss_app_model";

import { patch } from "@web/core/utils/patch";

patch(DiscussApp, {
    new() {
        const res = super.new(...arguments);
        res.chats.hideWhenEmpty = true;
        return res;
    },
});
