import { DiscussChannel } from "@mail/discuss/core/common/discuss_channel_model";

import { fields } from "@mail/model/misc";

import { patch } from "@web/core/utils/patch";

const discussChannelPatch = {
    setup() {
        super.setup(...arguments);
        this.appAsLivechats = fields.One("DiscussApp", {
            compute() {
                return this.channel_type === "livechat" ? this.store.discuss : null;
            },
        });
    },
};
patch(DiscussChannel.prototype, discussChannelPatch);
