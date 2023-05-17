/* @odoo-module */

import { PinnedMessagesPanel } from "@mail/discuss/message_pin/pinned_messages_panel";
import { ChatWindow, MODES } from "@mail/web/chat_window/chat_window";
import { useChildSubEnv } from "@odoo/owl";
import { patch } from "@web/core/utils/patch";

MODES.PINNED_MESSAGES = "pinned-messages";

patch(ChatWindow, "discuss/message_pin", {
    components: { ...ChatWindow.components, PinnedMessagesPanel },
});

patch(ChatWindow.prototype, "discuss/message_pin", {
    setup() {
        this._super();
        useChildSubEnv({
            pinMenu: {
                open: () => (this.state.activeMode = MODES.PINNED_MESSAGES),
                close: () => {
                    if (this.state.activeMode === MODES.PINNED_MESSAGES) {
                        this.state.activeMode = MODES.NONE;
                    }
                },
            },
        });
    },
    togglePinMenu() {
        this.state.activeMode =
            this.state.activeMode === MODES.PINNED_MESSAGES ? MODES.NONE : MODES.PINNED_MESSAGES;
    },
});
