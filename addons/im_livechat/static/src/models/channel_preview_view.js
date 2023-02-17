/** @odoo-module **/

import { Patch } from "@mail/model";

Patch({
    name: "ChannelPreviewView",
    fields: {
        imageUrl: {
            compute() {
                if (this.channel.channel_type === "livechat") {
                    return "/mail/static/src/img/smiley/avatar.jpg";
                }
                return this._super();
            },
        },
    },
});
