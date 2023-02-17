/** @odoo-module **/

import { Patch } from "@mail/model";

Patch({
    name: "ThreadIconView",
    fields: {
        threadTypingIconView: {
            compute() {
                if (
                    this.thread.channel &&
                    this.thread.channel.channel_type === "livechat" &&
                    this.thread.orderedOtherTypingMembers.length > 0
                ) {
                    return {};
                }
                return this._super();
            },
        },
    },
});
