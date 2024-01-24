/* @odoo-module */

import { Record } from "@mail/core/common/record";
import { Thread } from "@mail/core/common/thread_model";

import { patch } from "@web/core/utils/patch";

patch(Thread.prototype, {
    setup() {
        super.setup();
        this.chatbotTypingMessage = Record.one("Message", {
            compute() {
                if (this.isChatbotThread) {
                    return { id: -0.1 - this.id, originThread: this, author: this.operator };
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
                        originThread: this,
                        author: this.operator,
                    };
                }
            },
        });
        this.chatbot_script_id = null;
        this.requested_by_operator = false;
    },

    get isLastMessageFromCustomer() {
        if (this.type !== "livechat") {
            return super.isLastMessageFromCustomer;
        }
        return this.newestMessage?.isSelfAuthored;
    },

    get avatarUrl() {
        if (this.type === "livechat") {
            return this.operator.avatarUrl;
        }
        return super.avatarUrl;
    },

    get isChatbotThread() {
        return Boolean(this.chatbot_script_id);
    },

    get hasWelcomeMessage() {
        return this.type === "livechat" && !this.isChatbotThread && !this.requested_by_operator;
    },
});
