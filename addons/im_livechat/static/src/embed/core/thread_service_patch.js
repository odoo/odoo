/* @odoo-module */

import { SESSION_STATE } from "@im_livechat/embed/core/livechat_service";

import { ThreadService, threadService } from "@mail/core/common/thread_service";
import { prettifyMessageContent } from "@mail/utils/common/format";

import { markup } from "@odoo/owl";

import { _t } from "@web/core/l10n/translation";
import { patch } from "@web/core/utils/patch";
import { session } from "@web/session";

threadService.dependencies.push(
    "im_livechat.livechat",
    "im_livechat.chatbot",
    "mail.chat_window",
    "notification"
);

patch(ThreadService.prototype, {
    TEMPORARY_ID: "livechat_temporary_thread",

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
    },

    getMessagePostRoute(thread) {
        if (thread.type !== "livechat") {
            return super.getMessagePostRoute(...arguments);
        }
        return "/im_livechat/chat_post";
    },

    async getMessagePostParams({ thread, body }) {
        if (thread.type !== "livechat") {
            return super.getMessagePostParams(...arguments);
        }
        return {
            uuid: thread.uuid,
            message_content: await prettifyMessageContent(body),
        };
    },

    /**
     * @returns {Promise<import("@mail/core/common/message_model").Message}
     */
    async post(thread, body, params) {
        const chatWindow = this.store.ChatWindow.records.find(
            (c) => c.threadLocalId === thread.localId
        );
        if (
            this.livechatService.state !== SESSION_STATE.PERSISTED &&
            thread.localId === this.livechatService.thread?.localId
        ) {
            // replace temporary thread by the persisted one.
            const temporaryThread = thread;
            thread = await this.getLivechatThread({ persisted: true });
            if (!thread) {
                this.chatWindowService.close(chatWindow);
                this.remove(temporaryThread);
                return;
            }
            chatWindow.thread = thread;
            this.remove(temporaryThread);
            if (this.chatbotService.active) {
                await this.chatbotService.postWelcomeSteps();
            }
        }
        const message = await super.post(thread, body, params);
        if (!message) {
            this.notificationService.add(_t("Session expired... Please refresh and try again."));
            this.chatWindowService.close(chatWindow);
            this.livechatService.leaveSession({ notifyServer: false });
            return;
        }
        this.chatbotService.bus.trigger("MESSAGE_POST", message);
        return message;
    },

    async openChat() {
        if (this.chatbotService.shouldRestore) {
            this.chatbotService.restore();
        }
        const thread = await this.getLivechatThread();
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

    async update(thread, data) {
        super.update(...arguments);
        if (data.operator_pid) {
            thread.operator = this.store.Persona.insert({
                type: "partner",
                id: data.operator_pid[0],
                name: data.operator_pid[1],
            });
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

    /**
     * @param {Object} param0
     * @param {boolean} param0.persisted
     * @returns {Promise<import("@mail/core/common/thread_model").Thread?>}
     */
    async getLivechatThread({ persisted = false } = {}) {
        const session = await this.livechatService.getSession({ persisted });
        if (!session?.operator_pid) {
            this.notification.add(_t("No available collaborator, please try again later."));
            return;
        }
        const thread = this.store.Thread.insert({
            ...session,
            id: session.id ?? this.TEMPORARY_ID,
            model: "discuss.channel",
            type: "livechat",
        });
        if (session.messages) {
            thread.messages = session.messages.map((message) => {
                if (message.parentMessage) {
                    message.parentMessage.body = markup(message.parentMessage.body);
                }
                message.body = markup(message.body);
                return this.store.Message.insert(message);
            });
        }
        return thread;
    },
});
