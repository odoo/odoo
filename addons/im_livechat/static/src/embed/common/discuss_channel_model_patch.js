import { DiscussChannel } from "@mail/discuss/core/common/discuss_channel_model";

import { patch } from "@web/core/utils/patch";

patch(DiscussChannel.prototype, {
    get avatarUrl() {
        if (this.channel_type === "livechat") {
            return this.thread.livechat_operator_id.avatarUrl;
        }
        return super.avatarUrl;
    },
    get membersThatCanSeen() {
        return super.membersThatCanSeen.filter((member) => member.livechat_member_type !== "bot");
    },
});
