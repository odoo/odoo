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
            if (this.env.services["im_livechat.chatbot"].isChatbotThread(thread)) {
                thread.chatbotTypingMessage = {
                    id: this.env.services["mail.message"].getNextTemporaryId(),
                    author: thread.operator,
                    originThread: thread,
                };
            } else {
                thread.livechatWelcomeMessage = {
                    id: this.env.services["mail.message"].getNextTemporaryId(),
                    body: livechatService.options.default_message,
                    author: thread.operator,
                    originThread: thread,
                };
            }
        }
        return thread;
    },
});

patch(Thread.prototype, {
    chatbotScriptId: null,

    setup() {
        super.setup();
        this.chatbotTypingMessage = Record.one("Message");
        this.livechatWelcomeMessage = Record.one("Message");
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
});
