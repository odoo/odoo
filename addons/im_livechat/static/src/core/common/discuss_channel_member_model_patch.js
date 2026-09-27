import { ChannelMember } from "@mail/discuss/core/common/channel_member_model";

import { patch } from "@web/core/utils/patch";

/** @type {import("models").ChannelMember} */
const discussChannelMemberPatch = {
    setup() {
        super.setup(...arguments);
        /** @type {"agent"|"bot"|"visitor"} */
        this.livechat_member_type = undefined;
    },
};
patch(ChannelMember.prototype, discussChannelMemberPatch);
