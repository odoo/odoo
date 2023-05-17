/* @odoo-module */

import { PinnedMessagesPanel } from "@mail/discuss/message_pin/pinned_messages_panel";
import { Discuss, MODES } from "@mail/discuss_app/discuss";
import { useChildSubEnv } from "@odoo/owl";
import { patch } from "@web/core/utils/patch";

MODES.PINNED_MESSAGES = "pinned-messages";

patch(Discuss, "discuss/message_pin", {
    components: { ...Discuss.components, PinnedMessagesPanel },
});

patch(Discuss.prototype, "discuss/message_pin", {
    setup() {
        this._super();
        useChildSubEnv({
            pinMenu: {
                open: () => (this.state.activeMode = "pinned-messages"),
                close: () => {
                    if (this.state.activeMode === "pinned-messages") {
                        this.state.activeMode = "";
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
