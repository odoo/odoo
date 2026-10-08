import { ChannelMember } from "@mail/discuss/core/common/channel_member_model";
import { patchModel } from "@mail/model/export";

export const discussChannelMemberPatch = patchModel(ChannelMember, {
    setup() {
        super.setup(...arguments);
        /** @type {"agent"|"bot"|"visitor"} */
        this.livechat_member_type = undefined;
    },
});
