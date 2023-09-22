/* @odoo-module */

import { ThreadService, threadService } from "@mail/core/common/thread_service";

import { patch } from "@web/core/utils/patch";
import { session } from "@web/session";

threadService.dependencies.push(
    "im_livechat.livechat",
    "im_livechat.chatbot",
    "mail.chat_window",
    "notification"
);

patch(ThreadService.prototype, {
    /**
     * @param {import("@web/env").OdooEnv} env
     * @param {{
     * "im_livechat.chatbot": import("@im_livechat/embed/chatbot/chatbot_service").ChatBotService,
     * "im_livechat.livechat": import("@im_livechat/embed/core/livechat_service").LivechatService,
     * "mail.chat_window": import("@mail/core/common/chat_window_service").ChatWindowService,
     * notification: typeof import("@web/core/notifications/notification_service").notificationService.start,
     * }} services
     */
    setup(env, services) {
        super.setup(env, services);
        this.livechatService = services["im_livechat.livechat"];
        this.chatWindowService = services["mail.chat_window"];
        this.chatbotService = services["im_livechat.chatbot"];
        this.notification = services.notification;
        /** @type {Promise<import("models").Thread>?} */
        this.persistPromise = null;
    },

    /**
     * @returns {Promise<import("models").Message}
     */
    async post(thread, body, params) {
        thread = thread.type === "livechat" ? await this.livechatService.persistThread() : thread;
        if (!thread) {
            return;
        }
        const message = await super.post(thread, body, params);
        this.chatbotService.bus.trigger("MESSAGE_POST", message);
        return message;
    },

    async openChat() {
        if (this.chatbotService.shouldRestore) {
            this.chatbotService.restore();
        }
        const thread = await this.livechatService.getOrCreateThread();
        if (!thread) {
            return;
        }
        const chatWindow = this.store.ChatWindow.insert({
            thread,
            folded: thread.state === "folded",
        });
        chatWindow.autofocus++;
        if (this.chatbotService.active) {
            this.chatbotService.start();
        }
    },

    avatarUrl(author, thread) {
        if (thread.type !== "livechat") {
            return super.avatarUrl(...arguments);
        }
        const isFromOperator =
            author && author.id !== this.livechatService.options.current_partner_id;
        if (isFromOperator) {
            return `${session.origin}/im_livechat/operator/${
                author?.id ?? thread.operator.id
            }/avatar`;
        } else if (author) {
            return `${session.origin}/web/image/res.partner/${author.id}/avatar_128`;
        } else {
            return `${session.origin}/mail/static/src/img/smiley/avatar.jpg`;
        }
    },
});
