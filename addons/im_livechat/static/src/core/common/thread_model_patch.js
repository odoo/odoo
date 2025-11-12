import { fields } from "@mail/model/export";
import { Thread } from "@mail/core/common/thread_model";

import { patch } from "@web/core/utils/patch";

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
<<<<<<< db80e85e2b89b55dd78ab180ba14663d817c3f4b
            (this.channel?.channel_type === "livechat" && !this.store.chatHub.compact) ||
||||||| c758b93a57cd98ab76c26c03bd0097f2eef50961
            (this.channel_type === "livechat" && !this.store.chatHub.compact) ||
=======
            (this.channel_type === "livechat" &&
                !this.store.chatHub.compact &&
                this.self_member_id) ||
>>>>>>> b7f3f178138da3d91ff14f5acaf5724c51932ca9
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

    get isChatChannel() {
        return this.channel?.channel_type === "livechat" || super.isChatChannel;
    },

    get allowDescription() {
        return this.channel?.channel_type === "livechat" || super.allowDescription;
    },

    get composerHidden() {
        return this.channel?.channel_type === "livechat" && this.livechat_end_dt;
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
