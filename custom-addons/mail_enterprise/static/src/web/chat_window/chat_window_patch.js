/* @odoo-module */

import { ChatWindow } from "@mail/core/common/chat_window";

import { patch } from "@web/core/utils/patch";

import { useBackButton } from "@web_mobile/js/core/hooks";

patch(ChatWindow.prototype, {
    setup() {
        super.setup();
        useBackButton(() => this.chatWindowService.close(this.props.chatWindow));
    },
});
