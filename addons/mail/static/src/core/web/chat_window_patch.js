import { ChatWindow } from "@mail/core/common/chat_window";

import { patch } from "@web/core/utils/patch";

patch(ChatWindow.prototype, {
    get attClass() {
        return {
            ...super.attClass,
            border: true,
        };
    },
});
