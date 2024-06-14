import { Discuss } from "@mail/core/common/discuss";

import { patch } from "@web/core/utils/patch";

import { useEffect } from "@odoo/owl";

patch(Discuss.prototype, {
    setup(...args) {
        super.setup(...args);
        useEffect(
            () => {
                if (this.thread && this.thread === this.store.openInviteThread) {
                    this.threadActions.actions
                        .find((action) => action.id === "add-users")
                        ?.onSelect();
                    this.store.openInviteThread = null;
                }
            },
            () => [this.store.openInviteThread]
        );
    },
});
