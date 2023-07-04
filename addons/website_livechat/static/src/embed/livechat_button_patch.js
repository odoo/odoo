/* @odoo-module */

import { LivechatButton } from "@im_livechat/embed/core_ui/livechat_button";

import { patch } from "@web/core/utils/patch";

patch(LivechatButton.prototype, {
    get text() {
        return "";
    },
});
