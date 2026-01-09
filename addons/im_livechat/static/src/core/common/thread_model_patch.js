import { fields } from "@mail/model/export";
import { Thread } from "@mail/core/common/thread_model";

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
});
