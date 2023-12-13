/* @odoo-module */

import { SESSION_STATE } from "@im_livechat/embed/common/livechat_service";

import { Record } from "@mail/core/common/record";
import { Thread } from "@mail/core/common/thread_model";
import { onChange } from "@mail/utils/common/misc";

import { patch } from "@web/core/utils/patch";

patch(Thread, {
    _insert(data) {
        const isUnknown = !this.get(data);
        const thread = super._insert(...arguments);
        const livechatService = this.env.services["im_livechat.livechat"];
        if (thread.channel_type === "livechat" && isUnknown) {
            onChange(
                thread,
                ["state", "seen_message_id", "message_unread_counter", "allow_public_upload"],
                () => {
                    if (
                        ![SESSION_STATE.CLOSED, SESSION_STATE.NONE].includes(livechatService.state)
                    ) {
                        livechatService.updateSession({
                            state: thread.state,
                            seen_message_id: thread.seen_message_id,
                            channel: thread,
                            allow_public_upload: thread.allow_public_upload,
                        });
                    }
                }
            );
        }
        return thread;
    },
});

patch(Thread.prototype, {
    chatbot_script_id: null,
    requested_by_operator: false,

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
