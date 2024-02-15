import { Record } from "@mail/core/common/record";
import { Thread } from "@mail/core/common/thread_model";

import { patch } from "@web/core/utils/patch";

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
                    const livechatService = this._store.env.services["im_livechat.livechat"];
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
        this.requested_by_operator = false;
    },

    get isLastMessageFromCustomer() {
        if (this.channel_type !== "livechat") {
            return super.isLastMessageFromCustomer;
        }
        return this.newestMessage?.isSelfAuthored;
    },

    get avatarUrl() {
        if (this.channel_type === "livechat") {
            return this.operator.avatarUrl;
        }
        return super.avatarUrl;
    },

    get hasWelcomeMessage() {
        return this.channel_type === "livechat" && !this.chatbot && !this.requested_by_operator;
    },
});
