import { DiscussContent } from "@mail/core/public_web/discuss_content";

import { patch } from "@web/core/utils/patch";

import { useEffect } from "@odoo/owl";

patch(DiscussContent.prototype, {
    setup(...args) {
        super.setup(...args);
        useEffect(
            () => {
                if (this.thread && this.thread === this.store.openInviteThread) {
                    this.threadActions.actions
                        .find((action) => action.id === "invite-people")
                        ?.onSelected();
                    this.store.openInviteThread = null;
                }
            },
            () => [this.store.openInviteThread]
        );
    },
});
