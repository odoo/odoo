import { LivechatChannel } from "@im_livechat/core/common/livechat_channel_model";
import { Record } from "@mail/core/common/record";

import { patch } from "@web/core/utils/patch";

const livechatChannelPatch = {
    setup() {
        super.setup(...arguments);
        this.appCategory = Record.one("DiscussAppCategory", {
            compute() {
                return {
                    extraClass: "o-mail-DiscussSidebarCategory-livechat",
                    hideWhenEmpty: !this.are_you_inside,
                    id: `im_livechat.category_${this.id}`,
                    name: this.name,
                    sequence: 22,
                };
            },
            inverse: "livechatChannel",
        });
        this.threads = Record.many("Thread", { inverse: "livechatChannel" });
    },
};
patch(LivechatChannel.prototype, livechatChannelPatch);
