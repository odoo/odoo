import { Thread } from "@mail/core/common/thread_model";

import { patch } from "@web/core/utils/patch";

patch(Thread.prototype, {
    setup() {
        super.setup();
        this._prevComposerDisabled = false;
        this.onChange(
            () => [this.composerDisabled],
            function onChangeComposerDisabled(composerDisabled) {
                if (!composerDisabled && this._prevComposerDisabled) {
                    this.composer.autofocus++;
                }
                this._prevComposerDisabled = composerDisabled;
            }
        );
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
        if (this.channel?.selfMemberType !== "visitor") {
            return super.post(...arguments);
        }
        if (
            this.channel.chatbot &&
            !this.channel.livechat_agent_history_ids.length &&
            this.channel.chatbot.currentStep?.step_type !== "free_input_multi"
        ) {
            this.channel.chatbot.isProcessingAnswer = true;
        }
        const message = await super.post(...arguments);
        if (this.channel?.chatbot?.currentStep?.step_type === "free_input_multi") {
            // Multi-line answers are processed after a debounce delay: do not wait to swap
            // temporary thread with persisted one.
            this.channel.chatbot.processAnswer(message);
        } else {
            await this.channel?.chatbot?.processAnswer(message);
        }
        return message;
    },
    computeComposerDisabled() {
        if (this.channel?.selfMemberType !== "visitor") {
            return super.computeComposerDisabled(...arguments);
        }
        if (this.channel.livechat_agent_history_ids.length && !this.channel.livechat_end_dt) {
            return false;
        }
        const step = this.channel.chatbot?.currentStep;
        return Boolean(
            this.channel.chatbot?.isProcessingAnswer ||
                (step &&
                    !step.operatorFoundEver &&
                    (step.completed || !step.expectAnswer || step.answer_ids.length > 0))
        );
    },
    get shouldTranslateNewMessages() {
        if (
            this.store.hasMessageTranslationFeature &&
            this.channel?.selfMemberType === "visitor"
        ) {
            return this.autoTranslateEnabled === undefined ? true : this.autoTranslateEnabled;
        }
        return super.shouldTranslateNewMessages;
    },
});
