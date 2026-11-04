import { ChannelMember } from "@mail/core/common/channel_member_model";
import { Record } from "@mail/core/common/record";

import { patch } from "@web/core/utils/patch";

/** @type {import("models").ChannelMember} */
const ChannelMemberPatch = {
    setup() {
        super.setup(...arguments);
        this.rtcSession = Record.one("RtcSession");
    },
};
patch(ChannelMember.prototype, ChannelMemberPatch);
