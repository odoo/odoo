/* @odoo-module */

import { ThreadService, threadService } from "@mail/core/common/thread_service";

import { patch } from "@web/core/utils/patch";
import { url } from "@web/core/utils/urls";

threadService.dependencies.push("im_livechat.livechat", "im_livechat.chatbot");

patch(ThreadService.prototype, {
    /**
     * @param {import("@web/env").OdooEnv} env
     * @param {{
     * "im_livechat.chatbot": import("@im_livechat/embed/chatbot/chatbot_service").ChatBotService,
     * "im_livechat.livechat": import("@im_livechat/embed/common/livechat_service").LivechatService,
     * }} services
     */
    setup(env, services) {
        super.setup(env, services);
        this.livechatService = services["im_livechat.livechat"];
        this.chatbotService = services["im_livechat.chatbot"];
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
        const thread = await this.livechatService.getOrCreateThread();
        if (!thread) {
            return;
        }
        const chatWindow = this.store.ChatWindow.insert({
            thread,
            folded: thread.state === "folded",
        });
        chatWindow.autofocus++;
        if (this.chatbotService.savedState) {
            this.chatbotService._restore();
        }
        if (this.chatbotService.active) {
            this.chatbotService.start();
        }
    },

    avatarUrl(persona, thread) {
        if (thread.type === "livechat" && persona.eq(thread.operator)) {
            return url(`/im_livechat/operator/${persona.id}/avatar`);
        }
        return super.avatarUrl(...arguments);
    },
});
