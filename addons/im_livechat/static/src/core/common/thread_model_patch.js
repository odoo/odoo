import { Thread } from "@mail/core/common/thread_model";

import { patch } from "@web/core/utils/patch";

patch(Thread.prototype, {
    setup() {
        super.setup();
        this._prevComposerDisabled = false;
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
    async post() {
        if (
            this.channel?.chatbot &&
            !this.channel.livechat_agent_history_ids.length &&
            this.channel.chatbot.currentStep?.step_type !== "free_input_multi"
        ) {
            this.channel.chatbot.isProcessingAnswer = true;
        }
        const message = await super.post(...arguments);
        await this.channel?.chatbot?.processAnswer(message);
        return message;
    },
    computeComposerDisabled() {
        if (this.channel?.channel_type !== "livechat") {
            return super.computeComposerDisabled(...arguments);
        }
        if (this.channel?.livechat_agent_history_ids.length && !this.livechat_end_dt) {
            return false;
        }
        const step = this.channel?.chatbot?.currentStep;
        return (
            this.channel?.chatbot?.isProcessingAnswer ||
            (step &&
                !step.operatorFoundEver &&
                (step.completed || !step.expectAnswer || step.answer_ids.length > 0))
        );
    },
    composerDisabledonUpdate() {
        if (!this.composerDisabled && this._prevComposerDisabled) {
            this.composer.autofocus++;
        }
        this._prevComposerDisabled = this.composerDisabled;
    },
    get shouldTranslateNewMessages() {
        if (
            this.channel?.channel_type === "livechat" &&
            this.channel.self_member_id?.livechat_member_type === "visitor" &&
            this.store.hasMessageTranslationFeature
        ) {
            return this.autoTranslateEnabled === undefined ? true : this.autoTranslateEnabled;
        }
        return super.shouldTranslateNewMessages;
    },
});
