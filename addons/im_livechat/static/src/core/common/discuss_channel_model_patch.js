import { DiscussChannel } from "@mail/discuss/core/common/discuss_channel_model";

import { fields } from "@mail/model/misc";

import { patch } from "@web/core/utils/patch";
import { formatList } from "@web/core/l10n/utils";

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
    get displayName() {
        if (this.channel_type !== "livechat" || this.self_member_id?.custom_channel_name) {
            return super.displayName;
        }
        const selfMemberType = this.isTransient
            ? "visitor"
            : this.self_member_id?.livechat_member_type;
        let memberNames = this.correspondents
            .filter((m) => {
                if (selfMemberType === "visitor") {
                    return m.livechat_member_type === "agent";
                }
                return m.livechat_member_type === "visitor";
            })
            .map((m) => m.name);
        if (!memberNames.length) {
            const histories =
                selfMemberType === "visitor"
                    ? this.livechat_agent_history_ids
                    : this.livechat_customer_history_ids;
            memberNames = histories
                .map((h) => this.getPersonaName(h.partner_id || h.guest_id))
                .filter(Boolean);
        }
        return memberNames.length
            ? formatList(memberNames, { style: "standard-narrow" })
            : super.displayName;
    },
    get isHideUntilNewMessageSupported() {
        if (this.livechat_end_dt) {
            return false;
        }
        return super.isHideUntilNewMessageSupported;
    },
    get livechatShouldAskLeaveConfirmation() {
        if (
            this.isTransient ||
            this.livechat_end_dt ||
            !this.self_member_id ||
            this.channel_type !== "livechat"
        ) {
            return false;
        }
        return (
            this.self_member_id.livechat_member_type === "visitor" ||
            this.channel_member_ids.length <= 2
        );
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
    get showCorrespondentCountry() {
        if (this.channel_type === "livechat") {
            return (
                this.correspondent?.livechat_member_type === "visitor" &&
                Boolean(this.correspondentCountry)
            );
        }
        return super.showCorrespondentCountry;
    },
    get showImStatus() {
        if (this.self_member_id?.livechat_member_type === "visitor") {
            return false;
        }
        return super.showImStatus;
    },
};
patch(DiscussChannel.prototype, discussChannelPatch);
