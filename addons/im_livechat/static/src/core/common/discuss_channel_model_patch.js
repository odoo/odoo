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
    get isHideUntilNewMessageSupported() {
        if (this.livechat_end_dt) {
            return false;
        }
        return super.isHideUntilNewMessageSupported;
    },
    get displayName() {
        if (this.channel_type !== "livechat" || this.self_member_id?.custom_channel_name) {
            return super.displayName;
        }
        const memberType = this.self_member_id?.livechat_member_type;
        if (memberType === "visitor") {
            const agents = this.correspondents.filter((c) => c.livechat_member_type === "agent");
            if (agents.length) {
                return formatList(
                    agents.map((agent) => agent.name),
                    { style: "standard-narrow" }
                );
            }
            if (this.livechat_agent_history_ids.length) {
                return formatList(
                    this.livechat_agent_history_ids.map((h) => this.getPersonaName(h.partner_id)),
                    { style: "standard-narrow" }
                );
            }
        }
        if (memberType === "agent") {
            const visitors = this.correspondents.filter(
                (c) => c.livechat_member_type === "visitor"
            );
            if (visitors.length) {
                return formatList(
                    visitors.map((visitor) => visitor.name),
                    { style: "standard-narrow" }
                );
            }
            if (this.livechat_customer_history_ids.length) {
                return formatList(
                    this.livechat_customer_history_ids.map((h) =>
                        this.getPersonaName(h.partner_id || h.guest_id)
                    ),
                    { style: "standard-narrow" }
                );
            }
        }
        if (!memberType) {
            const allNamesFromHistory = this.livechat_channel_member_history_ids
                .map((h) => this.getPersonaName(h.partner_id || h.guest_id))
                .filter(Boolean);
            if (allNamesFromHistory.length) {
                return formatList(allNamesFromHistory, { style: "standard-narrow" });
            }
        }
        return super.displayName;
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
