/* @odoo-module */

import { ChatWindow } from "@mail/core/common/chat_window_model";
import { patch } from "@web/core/utils/patch";

patch(ChatWindow, {
    hide(chatWindow) {
        super.hide(...arguments);
        this.env.services["mail.chat_window"].notifyState(chatWindow);
    },
    show(chatWindow) {
        super.show(...arguments);
        this.env.services["mail.chat_window"].notifyState(chatWindow);
    },
});
