/** @odoo-module */

import { patch } from "@web/core/utils/patch";

import { Message } from "@mail/core_ui/message";

patch(Message.prototype, "im_livechat", {
    get imStatusClassName() {
        // Do not show ImStatus in public livechat.
        return "d-none";
    },
});
