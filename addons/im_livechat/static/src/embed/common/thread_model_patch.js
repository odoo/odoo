import { Record } from "@mail/core/common/record";
import { Thread } from "@mail/core/common/thread_model";
import "@mail/discuss/core/common/thread_model_patch";

import { patch } from "@web/core/utils/patch";
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
        this.livechat_active;
        this._startChatbot = Record.attr(false, {
            compute() {
                return (
                    this.chatbot?.thread?.eq(
                        this.store.env.services["im_livechat.livechat"].thread
                    ) && this.isLoaded
                );
            },
            onUpdate() {
                if (this._startChatbot) {
                    this.store.env.services["im_livechat.chatbot"].start();
                }
            },
        });
        this.requested_by_operator = false;
    },

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
            return this.getPersonaName(this.livechat_operator_id);
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
                body: await prettifyMessageContent(body, [], { allowEmojiLoading: false }),
                id: this.store.getNextTemporaryId(),
                model: "discuss.channel",
                res_id: this.id,
                thread: this,
            });
            this.messages.push(temporaryMsg);
            this?.chatbot?._simulateTyping(2 ** 31 - 1);
            const thread = await this.store.env.services["im_livechat.livechat"].persist();
            temporaryMsg.author = this.store.self; // Might have been created after persist.
            if (!thread) {
                return;
            }
            await thread.isLoadedDeferred;
            return thread.post(...arguments).then(() => thread.readyToSwapDeferred.resolve());
        }
        const message = await super.post(...arguments);
        this.store.env.services["im_livechat.chatbot"].bus.trigger("MESSAGE_POST", message);
        return message;
    },

    /** @deprecated */
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
            this.chatbot?.isProcessingAnswer ||
            (step &&
                !step.operatorFound &&
                (step.completed || !step.expectAnswer || step.answers.length > 0))
        );
    },

    get composerHidden() {
        if (this.chatbot?.forwarded && this.livechat_active) {
            return false;
        }
        return super.composerHidden || this.chatbot?.completed;
    },
});
