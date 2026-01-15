import { LivechatChannel } from "@im_livechat/core/common/livechat_channel_model";
import { fields } from "@mail/core/common/record";

import { patch } from "@web/core/utils/patch";

const livechatChannelPatch = {
    setup() {
        super.setup(...arguments);
        this.appCategory = fields.One("DiscussAppCategory", {
            compute() {
                return {
                    extraClass: "o-mail-DiscussSidebarCategory-livechat",
                    hideWhenEmpty: !this.are_you_inside,
                    id: `im_livechat.category_${this.id}`,
                    icon: "fa fa-commenting-o",
                    name: this.name,
                    sequence: 22,
                };
            },
            eager: true,
            inverse: "livechat_channel_id",
        });
        this.threads = fields.Many("Thread", { inverse: "livechat_channel_id" });
    },
};
patch(LivechatChannel.prototype, livechatChannelPatch);
