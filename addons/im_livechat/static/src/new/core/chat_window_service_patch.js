/** @odoo-module */

import { ChatWindowService } from "@mail/web/chat_window/chat_window_service";
import { patch } from "@web/core/utils/patch";

patch(ChatWindowService.prototype, "im_livechat", {
    notifyState() {
        return;
    },
});
