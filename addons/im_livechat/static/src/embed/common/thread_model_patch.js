import { fields } from "@mail/core/common/record";
import { Thread } from "@mail/core/common/thread_model";
import "@mail/discuss/core/common/thread_model_patch";
import { generateEmojisOnHtml } from "@mail/utils/common/format";

import { patch } from "@web/core/utils/patch";
import { Deferred } from "@web/core/utils/concurrency";

/** @type {typeof Thread} */
const threadStaticPatch = {
    async getOrFetch(data, fieldNames = []) {
        const thread = await super.getOrFetch(...arguments);
        if (thread) {
            return thread;
        }
        // wait for restore of livechatService.savedState as channel might be inserted from there
        await this.store.isReady;
        return super.getOrFetch(...arguments);
    },
};
patch(Thread, threadStaticPatch);

patch(Thread.prototype, {
    setup() {
        super.setup();
        this.livechat_operator_id = fields.One("res.partner");
        this.chatbotTypingMessage = fields.One("mail.message", {
            compute() {
                if (this.chatbot) {
                    return {
                        id: -0.1 - this.id,
                        thread: this,
                        author_id: this.livechat_operator_id,
                    };
                }
            },
        });
        this.livechatWelcomeMessage = fields.One("mail.message", {
            compute() {
                if (this.hasWelcomeMessage) {
                    const livechatService = this.store.env.services["im_livechat.livechat"];
                    return {
                        id: -0.2 - this.id,
                        body: livechatService.options.default_message,
                        thread: this,
                        author_id: this.livechat_operator_id,
                    };
                }
            },
        });
        /**
         * Deferred that resolves once a newly persisted thread is ready to swap
         * with its temporary counterpart (i.e. when the actions following the
         * persist call are done to avoid flickering).
         *
         * @type {Deferred}
         */
        this.readyToSwapDeferred = new Deferred();
        this.chatbot = fields.One("Chatbot");
        this._toggleChatbot = fields.Attr(false, {
            compute() {
                return this.chatbot && !this.livechat_end_dt;
            },
            onUpdate() {
                this.isLoadedDeferred.then(() => {
                    if (this._toggleChatbot) {
                        this.chatbot.start();
                    } else {
                        this.chatbot?.stop();
                    }
                });
            },
            eager: true,
        });
        this.requested_by_operator = false;
        this._prevComposerDisabled = false;
    },
    /** @returns {boolean} */
    get isLastMessageFromCustomer() {
        return this.newestPersistentOfAllMessage?.isSelfAuthored;
    },

    get membersThatCanSeen() {
        return super.membersThatCanSeen.filter((member) => member.livechat_member_type !== "bot");
    },

    get avatarUrl() {
        if (this.channel?.channel_type === "livechat") {
            return this.livechat_operator_id.avatarUrl;
        }
        return super.avatarUrl;
    },
    get displayName() {
        if (this.channel?.channel_type === "livechat" && this.livechat_operator_id) {
            return this.getPersonaName(this.livechat_operator_id);
        }
        return super.displayName;
    },
    get hasWelcomeMessage() {
        return (
            this.channel?.channel_type === "livechat" &&
            !this.chatbot &&
            !this.requested_by_operator
        );
    },
    /** @returns {Promise<import("models").Message} */
    async post(body, postData, extraData = {}) {
        if (
            this.chatbot &&
            !this.chatbot.forwarded &&
            this.chatbot.currentStep?.step_type !== "free_input_multi"
        ) {
            this.chatbot.isProcessingAnswer = true;
        }
        if (this.channel?.channel_type === "livechat" && this.isTransient) {
            // For smoother transition: post the temporary message and set the
            // selected chat bot answer if any. Then, simulate the chat bot is
            // typing (2 ** 31 - 1 is the greatest value supported by
            // `setTimeout`).
            if (this.chatbot && extraData.selected_answer_id) {
                this.chatbot.currentStep.selectedAnswer = this.store["chatbot.script.answer"].get(
                    extraData.selected_answer_id
                );
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
            this?.chatbot?._simulateTyping(2 ** 31 - 1);
            const thread = await this.store.env.services["im_livechat.livechat"].persist(this);
            temporaryMsg.author_id = this.store.self; // Might have been created after persist.
            if (!thread) {
                return;
            }
            await thread.isLoadedDeferred;
            return thread.post(...arguments).then(() => thread.readyToSwapDeferred.resolve());
        }
        const message = await super.post(...arguments);
        await this.chatbot?.processAnswer(message);
        return message;
    },

    get composerHidden() {
        return (
            super.composerHidden ||
            this.livechat_end_dt ||
            (this.chatbot?.completed && !this.chatbot?.forwarded)
        );
    },

    computeComposerDisabled() {
        const step = this.chatbot?.currentStep;
        if (this.chatbot?.forwarded && !this.livechat_end_dt) {
            return false;
        }
        return (
            this.chatbot?.isProcessingAnswer ||
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
