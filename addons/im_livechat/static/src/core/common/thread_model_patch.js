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
    },
    get autoOpenChatWindowOnNewMessage() {
        return (
            (this.channel?.channel_type === "livechat" &&
                !this.store.chatHub.compact &&
                this.self_member_id) ||
            super.autoOpenChatWindowOnNewMessage
        );
    },
    get showCorrespondentCountry() {
        if (this.channel?.channel_type === "livechat") {
            return (
                this.correspondent?.livechat_member_type === "visitor" &&
                Boolean(this.correspondentCountry)
            );
        }
        return super.showCorrespondentCountry;
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
        const selfMemberType = this.self_member_id?.livechat_member_type;
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
                    ? this.channel.livechat_agent_history_ids
                    : this.channel.livechat_customer_history_ids;
            memberNames = histories
                .map((h) => this.getPersonaName(h.partner_id || h.guest_id))
                .filter(Boolean);
        }
        return memberNames.length
            ? formatList(memberNames, { style: "standard-narrow" })
            : super.displayName;
    },
});
