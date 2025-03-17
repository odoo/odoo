import { Record } from "@mail/core/common/record";
import { Thread } from "@mail/core/common/thread_model";
import "@mail/discuss/core/common/thread_model_patch";

import { patch } from "@web/core/utils/patch";
import { _t } from "@web/core/l10n/translation";
import { Deferred } from "@web/core/utils/concurrency";
import { prettifyMessageContent } from "@mail/utils/common/format";

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
        this.livechat_operator_id = Record.one("Persona");
        this.chatbotTypingMessage = Record.one("mail.message", {
            compute() {
                if (this.chatbot) {
                    return { id: -0.1 - this.id, thread: this, author: this.livechat_operator_id };
                }
            },
        });
        this.livechatWelcomeMessage = Record.one("mail.message", {
            compute() {
                if (this.hasWelcomeMessage) {
                    const livechatService = this.store.env.services["im_livechat.livechat"];
                    return {
                        id: -0.2 - this.id,
                        body: livechatService.options.default_message,
                        thread: this,
                        author: this.livechat_operator_id,
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
        this.chatbot = Record.one("Chatbot");
        this.livechat_active = false;
        this._toggleChatbot = Record.attr(false, {
            compute() {
                return this.chatbot && this.isLoaded && this.livechat_active;
            },
            onUpdate() {
                if (this._toggleChatbot) {
                    this.chatbot.start();
                } else {
                    this.chatbot?.stop();
                }
            },
            eager: true,
        });
        this.storeAsActiveLivechats = Record.one("Store", {
            compute() {
                return this.livechat_active ? this.store : null;
            },
        });
        this.requested_by_operator = false;
    },
    /** @returns {boolean} */
    get isLastMessageFromCustomer() {
        return this.newestPersistentOfAllMessage?.isSelfAuthored;
    },

    get membersThatCanSeen() {
        return super.membersThatCanSeen.filter((member) => !member.is_bot);
    },

    get avatarUrl() {
        if (this.channel_type === "livechat") {
            return this.livechat_operator_id.avatarUrl;
        }
        return super.avatarUrl;
    },
    get displayName() {
        if (this.channel_type === "livechat" && this.livechat_operator_id) {
            return (
                this.livechat_operator_id.user_livechat_username || this.livechat_operator_id.name
            );
        }
        return super.displayName;
    },
    get hasWelcomeMessage() {
        return this.channel_type === "livechat" && !this.chatbot && !this.requested_by_operator;
    },
    /** @returns {Promise<import("models").Message} */
    async post(body, postData, extraData = {}) {
        if (
            this.chatbot &&
            !this.chatbot.forwarded &&
            this.chatbot.currentStep?.type !== "free_input_multi"
        ) {
            this.chatbot.isProcessingAnswer = true;
        }
        if (this.channel_type === "livechat" && this.isTransient) {
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
                author: this.store.self,
                body: await prettifyMessageContent(body, { allowEmojiLoading: false }),
                id: this.store.getNextTemporaryId(),
                model: "discuss.channel",
                res_id: this.id,
                thread: this,
            });
            this.messages.push(temporaryMsg);
            this?.chatbot?._simulateTyping(2 ** 31 - 1);
            const thread = await this.store.env.services["im_livechat.livechat"].persist(this);
            temporaryMsg.author = this.store.self; // Might have been created after persist.
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

    get showUnreadBanner() {
        if (this.chatbot && !this.chatbot.currentStep?.operatorFound) {
            return false;
        }
        return super.showUnreadBanner;
    },

    get composerDisabled() {
        const step = this.chatbot?.currentStep;
        if (this.chatbot?.forwarded && this.livechat_active) {
            return false;
        }
        return (
            super.composerDisabled ||
            this.chatbot?.isProcessingAnswer ||
            (step &&
                !step.operatorFound &&
                (step.completed || !step.expectAnswer || step.answers.length > 0))
        );
    },

    get composerDisabledText() {
        const text = super.composerDisabledText;
        if (text || !this.chatbot) {
            return text;
        }
        if (this.chatbot.completed) {
            return _t("This livechat conversation has ended");
        }
        if (
            this.chatbot.currentStep?.type === "question_selection" &&
            !this.chatbot.currentStep.selectedAnswer
        ) {
            return _t("Select an option above");
        }
        return _t("Say something");
    },
});
