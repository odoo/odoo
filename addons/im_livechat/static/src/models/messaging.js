/** @odoo-module **/

import { many, Patch } from "@mail/model";

Patch({
    name: "Messaging",
    fields: {
        /**
         * All pinned livechats that are known.
         */
        pinnedLivechats: many("Thread", {
            inverse: "messagingAsPinnedLivechat",
            readonly: true,
        }),
    },
});
