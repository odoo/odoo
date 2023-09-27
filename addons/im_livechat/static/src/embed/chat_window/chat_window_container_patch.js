/* @odoo-module */

import { ChatWindowContainer } from "@mail/core/common/chat_window_container";

import { patch } from "@web/core/utils/patch";

patch(ChatWindowContainer.prototype, {
    setup() {
        super.setup(...arguments);
        this.messaging.isReady.resolve({
            channels: [],
            current_user_settings: {},
        });
    },
});
