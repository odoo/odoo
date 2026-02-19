/** @odoo-module **/

import { many } from "@mail/model/model_field";
import { registerPatch } from "@mail/model/model_core";

registerPatch({
    name: "Messaging",
    fields: {
        /**
         * All pinned livechats that are known.
         */
        pinnedMLChats: many("Thread", {
            inverse: "messagingAsPinnedMLChat",
            readonly: true,
        }),
    },
});
