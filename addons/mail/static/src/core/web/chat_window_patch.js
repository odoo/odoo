/* @odoo-module */

import { ChatWindow } from "@mail/core/common/chat_window";

import { useService } from "@web/core/utils/hooks";
import { patch } from "@web/core/utils/patch";

patch(ChatWindow.prototype, "mail/core/web", {
    setup() {
        this._super(...arguments);
        this.actionService = useService("action");
    },
});
