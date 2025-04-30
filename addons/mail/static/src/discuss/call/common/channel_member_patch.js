import { ChannelMember } from "@mail/discuss/core/common/channel_member_model";
import { fields } from "@mail/core/common/record";

import { patch } from "@web/core/utils/patch";

/** @type {import("models").ChannelMember} */
const ChannelMemberPatch = {
    setup() {
        super.setup(...arguments);
        this.rtcSession = fields.One("discuss.channel.rtc.session");
    },
};
patch(ChannelMember.prototype, ChannelMemberPatch);
