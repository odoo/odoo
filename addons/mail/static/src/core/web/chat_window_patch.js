/* @odoo-module */

import { ChannelSelector } from "@mail/core/common/channel_selector";
import { ChatWindow } from "@mail/core/common/chat_window";

import { useService } from "@web/core/utils/hooks";
import { patch } from "@web/core/utils/patch";

Object.assign(ChatWindow.components, { ChannelSelector });

patch(ChatWindow.prototype, "mail/core/web", {
    setup() {
        this._super(...arguments);
        this.actionService = useService("action");
    },
});
