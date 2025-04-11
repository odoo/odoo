import { ChatWindow } from "@mail/core/common/chat_window";

import { useChildSubEnv } from "@odoo/owl";
import { patch } from "@web/core/utils/patch";


patch(ChatWindow.prototype, {
    get style() {
        const res = super.style;
        return res + ' z-index: 1057;';
    }
});
