/** @odoo-module **/

import { one, Patch } from "@mail/model";

Patch({
    name: "Messaging",
    fields: {
        publicLivechatGlobal: one("PublicLivechatGlobal", {
            isCausal: true,
        }),
    },
});
