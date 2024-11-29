import { ChannelMember } from "@mail/discuss/core/common/channel_member_model";
import { patch } from "@web/core/utils/patch";

/** @type {import("models").ChannelMember} */
const channelMemberPatch = {
    getLangName() {
        if (this.persona.is_public && this.thread.visitor?.langName) {
            return this.thread.visitor.langName;
        }
        return super.getLangName();
    },
};
patch(ChannelMember.prototype, channelMemberPatch);
