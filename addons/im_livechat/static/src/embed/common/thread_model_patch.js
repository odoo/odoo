import { Record } from "@mail/core/common/record";
import { Thread } from "@mail/core/common/thread_model";
import "@mail/discuss/core/common/thread_model_patch";

import { patch } from "@web/core/utils/patch";
import { SESSION_STATE } from "./livechat_service";
import { _t } from "@web/core/l10n/translation";

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
        this.chatbot = Record.one("Chatbot");
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
    async post() {
        if (
            this.channel_type === "livechat" &&
            this.store.env.services["im_livechat.livechat"].state !== SESSION_STATE.PERSISTED
        ) {
            const thread = await this.store.env.services["im_livechat.livechat"].persist();
            if (!thread) {
                return;
            }
            return thread.post(...arguments);
        }
        const message = await super.post(...arguments);
        this.store.env.services["im_livechat.chatbot"].bus.trigger("MESSAGE_POST", message);
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
        return (
            super.composerDisabled ||
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
            !this.chatbot.currentStep.completed
        ) {
            return _t("Select an option above");
        }
        return _t("Say something");
    },
});
