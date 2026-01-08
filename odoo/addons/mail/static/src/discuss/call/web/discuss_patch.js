/* @odoo-module */

import { Discuss } from "@mail/core/common/discuss";
import { useChildSubEnv, useEffect, useState } from "@odoo/owl";

import { patch } from "@web/core/utils/patch";

patch(Discuss.prototype, {
    setup(...args) {
        super.setup(...args);
        const state = useState({ openInviteButton: 0 });
        useChildSubEnv({
            onStartMeeting: () => {
                state.openInviteButton++;
            },
        });
        useEffect(
            () => {
                if (state.openInviteButton === 0) {
                    return;
                }
                this.threadActions.actions.find((action) => action.id === "add-users")?.onSelect();
            },
            () => [state.openInviteButton]
        );
    },
});
