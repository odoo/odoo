import { Thread } from "@mail/core/common/thread_model";

import { patch } from "@web/core/utils/patch";

patch(Thread.prototype, {
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

    async post() {
        if (
            this.channel?.chatbot &&
            this.channel.self_member_id?.livechat_member_type === "visitor" &&
            !this.channel.livechat_agent_history_ids.length &&
            this.channel.chatbot.currentStep?.step_type !== "free_input_multi"
        ) {
            this.channel.chatbot.isProcessingAnswer = true;
        }
        const message = await super.post(...arguments);
        await this.channel?.chatbot?.processAnswer(message);
        return message;
    },
});
