import { DiscussChannel } from "@mail/discuss/core/common/discuss_channel_model";
import { fields } from "@mail/model/misc";

import { patch } from "@web/core/utils/patch";

/** @type {import("models").DiscussChannel} */
const discussChannelPatch = {
    setup() {
        super.setup(...arguments);
        this.meeting_invited_member_ids = fields.Many("discuss.channel.member");
    },
};
patch(DiscussChannel.prototype, discussChannelPatch);
