import { Record } from "@mail/core/common/record";

export class LivechatChannel extends Record {
    static id = "id";

    appCategory = Record.one("DiscussAppCategory", {
        compute() {
            return {
                extraClass: "o-mail-DiscussSidebarCategory-livechat",
                hideWhenEmpty: true,
                id: `im_livechat.category_${this.id}`,
                livechatChannel: this,
                name: this.name,
                open: true,
                sequence: 22,
            };
        },
    });
    /** @type {number} */
    id;
    /** @type {string} */
    name;
}
LivechatChannel.register();
