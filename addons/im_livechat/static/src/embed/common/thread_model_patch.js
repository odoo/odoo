import { Record } from "@mail/core/common/record";
import { Thread } from "@mail/core/common/thread_model";

import { patch } from "@web/core/utils/patch";
import { SESSION_STATE } from "./livechat_service";

patch(Thread.prototype, {
    setup() {
        super.setup();
        this.chatbotTypingMessage = Record.one("Message", {
            compute() {
                if (this.chatbot) {
                    return { id: -0.1 - this.id, thread: this, author: this.operator };
                }
            },
        });
        this.livechatWelcomeMessage = Record.one("Message", {
            compute() {
                if (this.hasWelcomeMessage) {
                    const livechatService = this.store.env.services["im_livechat.livechat"];
                    return {
                        id: -0.2 - this.id,
                        body: livechatService.options.default_message,
                        thread: this,
                        author: this.operator,
                    };
                }
            },
        });
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
        if (this.channel_type !== "livechat") {
            return super.avatarUrl;
        }
        if (this.visitorMember && this.selfMember?.notEq(this.visitorMember)) {
            return this.visitorMember.persona.avatarUrl;
        }
        return this.operator.avatarUrl;
    },
    get displayName() {
        if (
            this.channel_type === "livechat" &&
            this.visitorMember &&
            this.selfMember?.notEq(this.visitorMember)
        ) {
            return this.custom_channel_name || this.visitorMember.name;
        }
        if (this.channel_type === "livechat" && this.operator) {
            return this.operator.user_livechat_username || this.operator.name;
        }
        return super.displayName;
    },
    get visitorMember() {
        return [...this.channelMembers]
            .sort((a, b) => a.id - b.id)
            .find((member) => member.persona.notEq(this.operator));
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
});
