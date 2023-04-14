/** @odoo-module */

import { ThreadService, threadService } from "@mail/core/thread_service";
import { createLocalId } from "@mail/utils/misc";
import { markup } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { patch } from "@web/core/utils/patch";
import { session } from "@web/session";

threadService.dependencies.push("im_livechat.livechat", "mail.chat_window", "notification");

patch(ThreadService.prototype, "im_livechat", {
    TEMPORARY_ID: "livechat_temporary_thread",

    setup(env, services) {
        this._super(env, services);
        this.livechatService = services["im_livechat.livechat"];
        this.chatWindowService = services["mail.chat_window"];
        this.notification = services.notification;
    },

    async post(thread, body) {
        const session = await this.livechatService.getSession({ persisted: true });
        const chatWindow = this.store.chatWindows.find(
            (chatWindow) =>
                chatWindow.thread.localId === createLocalId("discuss.channel", this.TEMPORARY_ID) ||
                chatWindow.thread.localId === thread.localId
        );
        if (!session) {
            this.notification.add(_t("No available collaborator, please try again later."));
            this.chatWindowService.close(chatWindow);
            return;
        }
        if (!thread.uuid) {
            // replace temporary thread by the persisted one.
            thread = this.insert({
                ...session,
                model: "discuss.channel",
                type: "livechat",
            });
            chatWindow.thread = thread;
        }
        const data = await this.rpc("/im_livechat/chat_post", {
            uuid: thread.uuid,
            message_content: body,
        });
        const message = this.messageService.insert(
            Object.assign(data, { body: markup(data.body) })
        );
        if (!thread.messages.some(({ id }) => id === message.id)) {
            thread.messages.push(message);
        }
    },

    async openChat() {
        const session = await this.livechatService.getSession();
        if (!session?.operator_pid) {
            this.notification.add(_t("No available collaborator, please try again later."));
            return;
        }
        const livechatThread = this.insert({
            ...session,
            id: session.id ?? this.TEMPORARY_ID,
            model: "discuss.channel",
            type: "livechat",
        });
        if (session.messages) {
            livechatThread.messages = session.messages.map((message) => {
                if (message.parentMessage) {
                    message.parentMessage.body = markup(message.parentMessage.body);
                }
                message.body = markup(message.body);
                return this.messageService.insert(message);
            });
        }
        this.chatWindowService.insert({ thread: livechatThread });
    },

    insert(data) {
        const isUnknown = !(createLocalId(data.model, data.id) in this.store.threads);
        const thread = this._super(data);
        if (thread.type === "livechat" && isUnknown) {
            thread.welcomeMessage = this.messageService.insert({
                body: this.livechatService.options.default_message,
                resId: thread.id,
                resModel: thread.model,
                author: thread.operator,
            });
        }
        return thread;
    },

    async update(thread, data) {
        this._super(thread, data);
        if (data?.operator_pid) {
            thread.operator = this.personaService.insert({
                type: "partner",
                id: data.operator_pid[0],
                name: data.operator_pid[1],
            });
        }
    },

    async fetchNewMessages(thread) {
        if (thread.type !== "livechat") {
            this._super(thread);
        }
    },

    avatarUrl(author, thread) {
        if (thread?.type !== "livechat") {
            return this._super(author, thread);
        }
        if (author?.id === thread.operator.id && author.type === thread.operator.type) {
            return `${session.origin}/im_livechat/operator/${thread.operator.id}/avatar`;
        } else if (author) {
            return `${session.origin}/web/image/res.partner/${author.id}/avatar_128`;
        } else {
            return `${session.origin}/mail/static/src/img/smiley/avatar.jpg`;
        }
    },
});
