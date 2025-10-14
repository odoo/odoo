import { LivechatChannel } from "@im_livechat/core/common/livechat_channel_model";

import { fields } from "@mail/core/common/record";

import { patch } from "@web/core/utils/patch";

const livechatChannelPatch = {
    setup() {
        super.setup(...arguments);
        this.channel_ids = fields.Many("discuss.channel", { inverse: "livechat_channel_id" });
    },
};
patch(LivechatChannel.prototype, livechatChannelPatch);
