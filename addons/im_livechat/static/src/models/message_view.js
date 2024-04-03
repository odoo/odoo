/** @odoo-module **/

import { registerPatch } from "@mail/model/model_core";

registerPatch({
    name: "MessageView",
    fields: {
        hasAuthorClickable: {
            compute() {
                if (
                    this.message &&
                    this.message.originThread &&
                    this.message.originThread.channel &&
                    this.message.originThread.channel.channel_type === "livechat"
                ) {
                    return this.message.author === this.message.originThread.channel.correspondent;
                }
                return this._super();
            },
        },
    },
});
