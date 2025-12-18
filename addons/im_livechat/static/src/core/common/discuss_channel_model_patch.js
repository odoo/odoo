import { DiscussChannel } from "@mail/discuss/core/common/discuss_channel_model";

import { fields } from "@mail/model/misc";

import { patch } from "@web/core/utils/patch";

/** @type {import("models").DiscussChannel} */
const discussChannelPatch = {
    setup() {
        super.setup(...arguments);
        this.chatbot = fields.One("Chatbot", { inverse: "channel_id" });
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
        this.livechat_looking_for_help_since_dt = fields.Datetime();
    },
    get allowDescriptionTypes() {
        return [...super.allowDescriptionTypes, "livechat"];
    },
    get allowedToLeaveChannelTypes() {
        return [...super.allowedToLeaveChannelTypes, "livechat"];
    },
    /** @override */
    _computeCanHide() {
        if (this.channel_type === "livechat") {
            return false;
        }
        return super._computeCanHide(...arguments);
    },
    get isHideUntilNewMessageSupported() {
        if (this.livechat_end_dt) {
            return false;
        }
        return super.isHideUntilNewMessageSupported;
    },
    get typesAllowingCalls() {
        return [...super.typesAllowingCalls, "livechat"];
    },
    get membersThatCanSeen() {
        return super.membersThatCanSeen.filter((member) => member.livechat_member_type !== "bot");
    },
    get chatChannelTypes() {
        return [...super.chatChannelTypes, "livechat"];
    },
    get memberListTypes() {
        return [...super.memberListTypes, "livechat"];
    },
};
patch(DiscussChannel.prototype, discussChannelPatch);
