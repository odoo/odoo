import { fields } from "@mail/core/common/record";
import { Thread } from "@mail/core/common/thread_model";

import { patch } from "@web/core/utils/patch";

patch(Thread.prototype, {
    setup() {
        super.setup();
        this.livechat_end_dt = fields.Datetime();
        this.livechat_conversation_tag_ids = fields.Many("im_livechat.conversation.tag");
        this.livechat_customer_member_id = fields.One("discuss.channel.member");
        this.livechat_main_agent_partner_id = fields.One("res.partner");
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
                this.livechat_main_agent_partner_id?.eq(this.store.self) &&
                Boolean(this.correspondentCountry)
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
        if (this.channel?.channel_type === "livechat" && persona.user_livechat_username) {
            return persona.user_livechat_username;
        }
        return super.getPersonaName(persona);
    },
});
