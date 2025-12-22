import { ChatWindow } from "@mail/core/common/chat_window";

import { patch } from "@web/core/utils/patch";

import { useEffect } from "@odoo/owl";

patch(ChatWindow.prototype, {
    setup(...args) {
        super.setup(...args);
        useEffect(
            () => {
                if (this.props.chatWindow.thread === this.store.openInviteThread) {
                    this.threadActions.actions
                        .find((action) => action.id === "invite-people")
                        ?.onSelect();
                    this.store.openInviteThread = null;
                }
            },
            () => [this.store.openInviteThread]
        );
    },
});
