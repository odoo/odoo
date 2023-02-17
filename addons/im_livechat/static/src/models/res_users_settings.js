/** @odoo-module **/

import { attr, Patch } from "@mail/model";

Patch({
    name: "res.users.settings",
    fields: {
        is_discuss_sidebar_category_livechat_open: attr({
            default: true,
        }),
    },
});
