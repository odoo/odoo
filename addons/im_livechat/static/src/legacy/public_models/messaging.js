/** @odoo-module **/

import { one, Patch } from "@im_livechat/legacy/model";

Patch({
    name: "Messaging",
    fields: {
        publicLivechatGlobal: one("PublicLivechatGlobal", {
            isCausal: true,
        }),
    },
});
