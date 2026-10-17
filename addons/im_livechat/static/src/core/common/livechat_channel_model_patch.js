import { LivechatChannel } from "@im_livechat/core/common/livechat_channel_model";

import { fields, patchModel } from "@mail/model/export";

export const livechatChannelPatch = patchModel(LivechatChannel, {
    setup() {
        super.setup(...arguments);
        this.channel_ids = fields.Many("discuss.channel", { inverse: "livechat_channel_id" });
    },
});
