/* @odoo-module */

import { DiscussAppCategory } from "@mail/core/common/discuss_app_category_model";
import { Record } from "@mail/core/common/record";

export class LivechatChannel extends Record {
    static id = "id";

    /** @type {number} */
    id;
    /** @type {string} */
    name;
    discussChannels = Record.many("Thread", { inverse: "livechatChannel" });
    appCategory = Record.one("DiscussAppCategory", {
        compute() {
            return {
                id: `im_livechat.category_${this.id}`,
                livechatChannel: this,
                name: this.name,
                sequence: DiscussAppCategory.LIVECHAT_SEQUENCE + this.id,
                extraClass: "o-mail-DiscussSidebarCategory-livechat",
            };
        },
    });
}
LivechatChannel.register();
