/* @odoo-module */

import { Thread } from "@mail/core/common/thread_model";
import { onChange } from "@mail/utils/common/misc";

import { patch } from "@web/core/utils/patch";
import { session } from "@web/session";
import { SESSION_STATE } from "./livechat_service";

patch(Thread, {
    insert(data) {
        const isUnknown = !this.get(data);
        const thread = super.insert(...arguments);
        const livechatService = this.env.services["im_livechat.livechat"];
        const chatbotService = this.env.services["im_livechat.chatbot"];
        const messageService = this.env.services["mail.message"];
        if (thread.type === "livechat" && isUnknown) {
            if (livechatService.displayWelcomeMessage && !chatbotService.isChatbotThread(thread)) {
                livechatService.welcomeMessage = this.store.Message.insert({
                    id: messageService.getNextTemporaryId(),
                    body: livechatService.options.default_message,
                    res_id: thread.id,
                    model: thread.model,
                    author: thread.operator,
                });
            }
            if (chatbotService.isChatbotThread(thread)) {
                chatbotService.typingMessage = this.store.Message.insert({
                    id: messageService.getNextTemporaryId(),
                    res_id: thread.id,
                    model: thread.model,
                    author: thread.operator,
                });
            }
            onChange(thread, ["state", "seen_message_id", "message_unread_counter"], () => {
                if (![SESSION_STATE.CLOSED, SESSION_STATE.NONE].includes(livechatService.state)) {
                    livechatService.updateSession({
                        state: thread.state,
                        seen_message_id: thread.seen_message_id,
                        channel: thread.channel,
                    });
                }
            });
            this.store.livechatThread = thread;
        }
        return thread;
    },
});

patch(Thread.prototype, {
    chatbotScriptId: null,

    get isChannel() {
        return this.type === "livechat" || super.isChannel;
    },

    get isChatChannel() {
        return this.type === "livechat" || super.isChatChannel;
    },

    get isLastMessageFromCustomer() {
        if (this.type !== "livechat") {
            return super.isLastMessageFromCustomer;
        }
        return this.newestMessage?.isSelfAuthored;
    },

    get imgUrl() {
        if (this.type !== "livechat") {
            return super.imgUrl;
        }
        return `${session.origin}/im_livechat/operator/${this.operator.id}/avatar`;
    },
});
