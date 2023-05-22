/* @odoo-module */

import { PinnedMessagesPanel } from "@mail/discuss/message_pin/pinned_messages_panel";
import { ChatWindow, MODES } from "@mail/web/chat_window/chat_window";
import { useChildSubEnv } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
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
    get actions() {
        const acts = this._super();
        if (this.thread?.model === "discuss.channel" && this.props.chatWindow.isOpen) {
            acts.push({
                id: "pinned",
                name: _t("Pinned Messages"),
                icon: "fa fa-fw fa-thumb-tack",
                onSelect: () => this.togglePinMenu(),
                sequence: 20,
            });
        }
        return acts;
    },
});
