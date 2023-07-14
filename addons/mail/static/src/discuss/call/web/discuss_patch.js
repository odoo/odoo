/* @odoo-module */

import { Discuss } from "@mail/core/common/discuss";
import { useEffect } from "@odoo/owl";

import { patch } from "@web/core/utils/patch";

patch(Discuss.prototype, "discuss/call/web", {
    setup(...args) {
        this._super(...args);
        Object.assign(this.state, { openInviteButton: 0 });
        useEffect(
            () => {
                if (this.state.openInviteButton === 0) {
                    return;
                }
                this.threadActions.actions.find((action) => action.id === "add-users")?.onSelect();
            },
            () => [this.state.openInviteButton]
        );
    },
    onStartMeeting() {
        this.state.openInviteButton++;
    },
});
