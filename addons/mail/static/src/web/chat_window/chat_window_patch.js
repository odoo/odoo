/* @odoo-module */

import { ChatWindow } from "@mail/chat_window/chat_window";
import { ChannelSelector } from "@mail/discuss_app/channel_selector";

import { useService } from "@web/core/utils/hooks";
import { patch } from "@web/core/utils/patch";

Object.assign(ChatWindow.components, { ChannelSelector });

patch(ChatWindow.prototype, "mail/chat_window", {
    setup() {
        this._super(...arguments);
        this.actionService = useService("action");
    },
});
