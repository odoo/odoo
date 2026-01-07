import { Thread } from "@mail/core/common/thread_model";
import "@mail/discuss/core/common/thread_model_patch";
import { generateEmojisOnHtml } from "@mail/utils/common/format";

import { patch } from "@web/core/utils/patch";
import { Deferred } from "@web/core/utils/concurrency";

patch(Thread.prototype, {
    setup() {
        super.setup();
        /**
         * Deferred that resolves once a newly persisted thread is ready to swap
         * with its temporary counterpart (i.e. when the actions following the
         * persist call are done to avoid flickering).
         *
         * @type {Deferred}
         */
        this.readyToSwapDeferred = new Deferred();
        this._prevComposerDisabled = false;
    },
    /** @returns {Promise<import("models").Message} */
    async post(body, postData, extraData = {}) {
        if (
            this.channel?.chatbot &&
            !this.channel.chatbot.forwarded &&
            this.channel.chatbot.currentStep?.step_type !== "free_input_multi"
        ) {
            this.channel.chatbot.isProcessingAnswer = true;
        }
        if (this.channel?.channel_type === "livechat" && this.isTransient) {
            // For smoother transition: post the temporary message and set the
            // selected chat bot answer if any. Then, simulate the chat bot is
            // typing (2 ** 31 - 1 is the greatest value supported by
            // `setTimeout`).
            if (this.channel.chatbot && extraData.selected_answer_id) {
                this.channel.chatbot.currentStep.selectedAnswer = this.store[
                    "chatbot.script.answer"
                ].get(extraData.selected_answer_id);
            }
            const temporaryMsg = this.store["mail.message"].insert({
                author_id: this.store.self,
                body: await generateEmojisOnHtml(body, { allowEmojiLoading: false }),
                id: this.store.getNextTemporaryId(),
                model: "discuss.channel",
                res_id: this.id,
                thread: this,
            });
            this.messages.push(temporaryMsg);
            this.channel.chatbot?._simulateTyping(2 ** 31 - 1);
            const channel = await this.store.env.services["im_livechat.livechat"].persist(this);
            temporaryMsg.author_id = this.store.self; // Might have been created after persist.
            if (!channel) {
                return;
            }
            await channel.isLoadedDeferred;
            return channel.post(...arguments).then(() => channel.readyToSwapDeferred.resolve());
        }
        const message = await super.post(...arguments);
        await this.channel?.chatbot?.processAnswer(message);
        return message;
    },

    computeComposerDisabled() {
        if (this.channel?.channel_type !== "livechat") {
            return super.computeComposerDisabled(...arguments);
        }
        if (this.channel?.chatbot?.forwarded && !this.livechat_end_dt) {
            return false;
        }
        const step = this.channel?.chatbot?.currentStep;
        return (
            this.channel?.chatbot?.isProcessingAnswer ||
            (step &&
                !step.operatorFound &&
                (step.completed || !step.expectAnswer || step.answer_ids.length > 0))
        );
    },

    composerDisabledonUpdate() {
        if (!this.composerDisabled && this._prevComposerDisabled) {
            this.composer.autofocus++;
        }
        this._prevComposerDisabled = this.composerDisabled;
    },
});
