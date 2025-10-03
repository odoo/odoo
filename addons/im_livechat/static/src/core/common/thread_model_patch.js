import { fields } from "@mail/core/common/record";
import { Thread } from "@mail/core/common/thread_model";

import { patch } from "@web/core/utils/patch";

patch(Thread.prototype, {
    setup() {
        super.setup();
        this.livechat_agent_history_ids = fields.Many("im_livechat.channel.member.history", {
            inverse: "threadAsAgentHistory",
        });
        this.livechat_channel_member_history_ids = fields.Many(
            "im_livechat.channel.member.history"
        );
        this.livechat_customer_history_ids = fields.Many("im_livechat.channel.member.history", {
            inverse: "threadAsCustomerHistory",
        });
        this.livechat_end_dt = fields.Datetime();
        this.livechat_operator_id = fields.One("res.partner");
        this.livechat_conversation_tag_ids = fields.Many("im_livechat.conversation.tag");
        this.livechatVisitorMember = fields.One("discuss.channel.member", {
            compute() {
                if (this.channel_type !== "livechat") {
                    return;
                }
                // For livechat threads, the correspondent is the first
                // channel member that is not the operator.
                const orderedChannelMembers = [...this.channel.channel_member_ids].sort(
                    (a, b) => a.id - b.id
                );
                const isFirstMemberOperator = orderedChannelMembers[0]?.partner_id?.eq(
                    this.livechat_operator_id
                );
                const visitor = isFirstMemberOperator
                    ? orderedChannelMembers[1]
                    : orderedChannelMembers[0];
                return visitor;
            },
        });
        /** @type {true|undefined} */
        this.open_chat_window = fields.Attr(undefined, {
            /** @this {import("models").Thread} */
            onUpdate() {
                if (this.open_chat_window) {
                    this.open_chat_window = undefined;
                    this.openChatWindow({ focus: true });
                }
            },
        });
    },
    get autoOpenChatWindowOnNewMessage() {
        return (
            (this.channel_type === "livechat" && !this.store.chatHub.compact) ||
            super.autoOpenChatWindowOnNewMessage
        );
    },
    get showCorrespondentCountry() {
        if (this.channel_type === "livechat") {
            return (
                this.livechat_operator_id?.eq(this.store.self) && Boolean(this.correspondentCountry)
            );
        }
        return super.showCorrespondentCountry;
    },
    get typesAllowingCalls() {
        return super.typesAllowingCalls.concat(["livechat"]);
    },

    get isChatChannel() {
        return this.channel_type === "livechat" || super.isChatChannel;
    },

    get allowDescription() {
        return this.channel_type === "livechat" || super.allowDescription;
    },

    get composerHidden() {
        return this.channel_type === "livechat" && this.livechat_end_dt;
    },
    /**
     * @override
     * @param {import("models").Persona} persona
     */
    getPersonaName(persona) {
        if (this.channel_type === "livechat" && persona.user_livechat_username) {
            return persona.user_livechat_username;
        }
        return super.getPersonaName(persona);
    },
    get displayName() {
        if (this.channel_type !== "livechat" || this.self_member_id?.custom_channel_name) {
            return super.displayName;
        }
        if (this.self_member_id?.livechat_member_type === "visitor") {
            const agents = this.correspondents.filter((c) => c.livechat_member_type === "agent");
            if (agents.length) {
                return agents.map((a) => this.getPersonaName(a.partner_id)).join(", ");
            }
            if (this.livechat_agent_history_ids.length) {
                return this.livechat_agent_history_ids
                    .map((h) => this.getPersonaName(h.partner_id))
                    .join(", ");
            }
        }
        if (this.self_member_id?.livechat_member_type === "agent") {
            const visitors = this.correspondents.filter(
                (c) => c.livechat_member_type === "visitor"
            );
            if (visitors.length) {
                return visitors
                    .map((v) => (v.partner_id ? v.partner_id.name : v.guest_id.name))
                    .join(", ");
            }
            if (this.livechat_customer_history_ids.length) {
                return this.livechat_customer_history_ids
                    .map((h) => (h.partner_id ? h.partner_id.name : h.guest_id.name))
                    .join(", ");
            }
        }
        return super.displayName;
    },
});
