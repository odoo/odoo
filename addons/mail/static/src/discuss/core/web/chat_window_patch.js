/* @odoo-module */

import { ChannelSelector } from "@mail/discuss/core/web/channel_selector";
import { ChatWindow } from "@mail/core/common/chat_window";
import { closeNewMessage } from "@mail/core/common/chat_window_service";
import { patch } from "@web/core/utils/patch";

Object.assign(ChatWindow.components, { ChannelSelector });

patch(ChatWindow.prototype, "discuss/core/web", {
    setup() {
        this._super(...arguments);
        this.closeNewMessage = closeNewMessage;
    },
});
