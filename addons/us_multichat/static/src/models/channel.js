/** @odoo-module **/

import { attr, one } from "@mail/model/model_field";
import { registerPatch } from "@mail/model/model_core";

registerPatch({
    name: "Channel",
    fields: {
        discussSidebarCategory: {
            compute() {
                if (this.channel_type?.startsWith("multi_livechat_")) {
                    const NAME = this.channel_type.split("multi_livechat_")[1];
                    return this.messaging.discuss["categoryMLChat_" + NAME];
                }
                return this._super();
            },
        },
    },
});
