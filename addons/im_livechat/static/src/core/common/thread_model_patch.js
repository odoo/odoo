import { fields } from "@mail/model/export";
import { Thread } from "@mail/core/common/thread_model";

import { formatList } from "@web/core/l10n/utils";
import { patch } from "@web/core/utils/patch";
import { url } from "@web/core/utils/urls";

patch(Thread.prototype, {
    setup() {
        super.setup();
        this.livechat_end_dt = fields.Datetime();
        this.livechat_operator_id = fields.One("res.partner");
        this.livechatVisitorMember = fields.One("discuss.channel.member", {
            compute() {
                if (this.channel?.channel_type !== "livechat") {
                    return;
                }
                // For live chat conversation, the correspondent is the first
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
            (this.channel?.channel_type === "livechat" && !this.store.chatHub.compact) ||
            super.autoOpenChatWindowOnNewMessage
        );
    },
    get showCorrespondentCountry() {
        if (this.channel?.channel_type === "livechat") {
            return (
                this.livechat_operator_id?.eq(this.store.self) && Boolean(this.correspondentCountry)
            );
        }
        return super.showCorrespondentCountry;
    },
    get typesAllowingCalls() {
        return super.typesAllowingCalls.concat(["livechat"]);
    },

    get allowDescription() {
        return this.channel?.channel_type === "livechat" || super.allowDescription;
    },

    get composerHidden() {
        return this.channel?.channel_type === "livechat" && this.livechat_end_dt;
    },

    get transcriptUrl() {
        return url(`/im_livechat/download_transcript/${this.id}`);
    },

    /**
     * @override
     * @param {import("models").Persona} persona
     */
    getPersonaName(persona) {
        if (this.channel?.channel_type === "livechat" && persona?.user_livechat_username) {
            return persona.user_livechat_username;
        }
        return super.getPersonaName(persona);
    },
    get displayName() {
        if (this.channel?.channel_type !== "livechat" || this.self_member_id?.custom_channel_name) {
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
            if (this.channel?.livechat_agent_history_ids.length) {
                return formatList(
                    this.channel.livechat_agent_history_ids.map((h) =>
                        this.getPersonaName(h.partner_id)
                    ),
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
            if (this.channel?.livechat_customer_history_ids.length) {
                return formatList(
                    this.channel?.livechat_customer_history_ids.map((h) =>
                        this.getPersonaName(h.partner_id || h.guest_id)
                    ),
                    { style: "standard-narrow" }
                );
            }
        }
        if (!memberType) {
            const allNamesFromHistory = this.channel?.livechat_channel_member_history_ids
                .map((h) => this.getPersonaName(h.partner_id || h.guest_id))
                .filter(Boolean);
            if (allNamesFromHistory.length) {
                return formatList(allNamesFromHistory, { style: "standard-narrow" });
            }
        }
        return super.displayName;
    },
});
