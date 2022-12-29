/** @odoo-module **/

import { one, Patch } from "@mail/legacy/model";

Patch({
    name: "Messaging",
    fields: {
        publicLivechatGlobal: one("PublicLivechatGlobal", {
            isCausal: true,
        }),
    },
});
