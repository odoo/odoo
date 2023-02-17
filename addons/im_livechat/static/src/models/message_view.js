/** @odoo-module **/

import { Patch } from "@mail/model";

Patch({
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
