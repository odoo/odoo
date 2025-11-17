import { DiscussChannel } from "@mail/discuss/core/common/discuss_channel_model";

import { fields } from "@mail/model/misc";

import { patch } from "@web/core/utils/patch";

/** @type {import("@models").DiscussChannel} */
const discussChannelPatch = {
    setup() {
        super.setup(...arguments);
        this.livechat_agent_history_ids = fields.Many("im_livechat.channel.member.history", {
            inverse: "channelAsAgentHistory",
        });
        this.livechat_channel_id = fields.One("im_livechat.channel", { inverse: "channel_ids" });
        this.livechat_channel_member_history_ids = fields.Many(
            "im_livechat.channel.member.history",
            { inverse: "channel_id" }
        );
        this.livechat_customer_history_ids = fields.Many("im_livechat.channel.member.history", {
            inverse: "channelAsCustomerHistory",
        });
    },
    get membersThatCanSeen() {
        return super.membersThatCanSeen.filter((member) => member.livechat_member_type !== "bot");
    },
    get chatChannelTypes() {
        return [...super.chatChannelTypes, "livechat"];
    },
};
patch(DiscussChannel.prototype, discussChannelPatch);
