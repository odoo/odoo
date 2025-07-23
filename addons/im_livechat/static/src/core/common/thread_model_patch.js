import { fields } from "@mail/core/common/record";
import { Thread } from "@mail/core/common/thread_model";

import { _t } from "@web/core/l10n/translation";
import { patch } from "@web/core/utils/patch";

patch(Thread.prototype, {
    setup() {
        super.setup();
        this.livechat_end_dt = fields.Datetime();
        this.livechat_operator_id = fields.One("res.partner");
        this.livechatVisitorMember = fields.One("discuss.channel.member", {
            compute() {
                if (this.channel_type !== "livechat") {
                    return;
                }
                // For livechat threads, the correspondent is the first
                // channel member that is not the operator.
                const orderedChannelMembers = [...this.channel_member_ids].sort(
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

    get composerDisabled() {
        return this.channel_type === "livechat" && this.livechat_end_dt;
    },

    get composerDisabledText() {
        return this.channel_type === "livechat" && this.livechat_end_dt
            ? _t("This livechat conversation has ended")
            : "";
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
});
