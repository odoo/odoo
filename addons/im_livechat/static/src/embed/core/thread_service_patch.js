/* @odoo-module */

import { SESSION_STATE } from "@im_livechat/embed/core/livechat_service";
import { closeChatWindow, insertChatWindow } from "@mail/core/common/chat_window_service";
import { getNextMessageTemporaryId, insertMessage } from "@mail/core/common/message_service";
import { insertPersona } from "@mail/core/common/persona_service";

import {
    ThreadService,
    avatarUrl,
    getMessagePostParams,
    getMessagePostRoute,
    insertThread,
    openChat,
    postMessage,
    removeThread,
    threadService,
    updateThread,
} from "@mail/core/common/thread_service";
import { prettifyMessageContent } from "@mail/utils/common/format";
import { createLocalId, onChange } from "@mail/utils/common/misc";
import { patchFn } from "@mail/utils/common/patch";

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

let store;
let chatbotService;
let livechatService;
let notificationService;

patchFn(avatarUrl, function (author, thread) {
    if (thread.type !== "livechat") {
        return this._super(...arguments);
    }
    const isFromOperator = author && author.id !== livechatService.options.current_partner_id;
    if (isFromOperator) {
        return `${session.origin}/im_livechat/operator/${author?.id ?? thread.operator.id}/avatar`;
    } else if (author) {
        return `${session.origin}/web/image/res.partner/${author.id}/avatar_128`;
    } else {
        return `${session.origin}/mail/static/src/img/smiley/avatar.jpg`;
    }
});

/**
 * @param {Object} param0
 * @param {boolean} param0.persisted
 * @returns {Promise<import("@mail/core/common/thread_model").Thread?>}
 */
export async function getLivechatThread({ persisted = false } = {}) {
    const session = await livechatService.getSession({ persisted });
    if (!session?.operator_pid) {
        notificationService.add(_t("No available collaborator, please try again later."));
        return;
    }
    const thread = insertThread({
        ...session,
        id: session.id ?? "livechat_temporary_thread",
        model: "discuss.channel",
        type: "livechat",
    });
    if (session.messages) {
        thread.messages = session.messages.map((message) => {
            if (message.parentMessage) {
                message.parentMessage.body = markup(message.parentMessage.body);
            }
            message.body = markup(message.body);
            return insertMessage(message);
        });
    }
    return thread;
}

patchFn(getMessagePostParams, async function ({ thread, body }) {
    if (thread.type !== "livechat") {
        return this._super(...arguments);
    }
    return {
        uuid: thread.uuid,
        message_content: await prettifyMessageContent(body),
    };
});

patchFn(getMessagePostRoute, function (thread) {
    if (thread.type !== "livechat") {
        return this._super(...arguments);
    }
    return "/im_livechat/chat_post";
});

patchFn(insertThread, function (data) {
    const isUnknown = !(createLocalId(data.model, data.id) in store.threads);
    const thread = this._super(data);
    if (thread.type === "livechat" && isUnknown) {
        if (livechatService.displayWelcomeMessage && !chatbotService.isChatbotThread(thread)) {
            livechatService.welcomeMessage = insertMessage({
                id: getNextMessageTemporaryId(),
                body: livechatService.options.default_message,
                res_id: thread.id,
                model: thread.model,
                author: thread.operator,
            });
        }
        if (chatbotService.isChatbotThread(thread)) {
            chatbotService.typingMessage = insertMessage({
                id: getNextMessageTemporaryId(),
                res_id: thread.id,
                model: thread.model,
                author: thread.operator,
            });
        }
        onChange(thread, "state", () => {
            if (livechatService.state !== SESSION_STATE.CLOSED) {
                livechatService.updateSession({ state: thread.state });
            }
        });
        onChange(thread, "seen_message_id", () => {
            if (livechatService.state !== SESSION_STATE.CLOSED) {
                livechatService.updateSession({ seen_message_id: thread.seen_message_id });
            }
        });
        onChange(thread, "message_unread_counter", () => {
            if (livechatService.state !== SESSION_STATE.CLOSED) {
                livechatService.updateSession({ channel: thread.channel });
            }
        });
        store.livechatThread = thread;
    }
    return thread;
});

patchFn(openChat, async function () {
    if (chatbotService.shouldRestore) {
        chatbotService.restore();
    }
    const thread = await getLivechatThread();
    if (!thread) {
        return;
    }
    const chatWindow = insertChatWindow({
        thread,
        folded: thread.state === "folded",
    });
    chatWindow.autofocus++;
    if (chatbotService.active) {
        chatbotService.start();
    }
});

/**
 * @returns {Promise<import("@mail/core/common/message_model").Message}
 */
patchFn(postMessage, async function (thread, body, params) {
    const _super = this._super;
    const chatWindow = store.chatWindows.find((c) => c.threadLocalId === thread.localId);
    if (
        livechatService.state !== SESSION_STATE.PERSISTED &&
        thread.localId === livechatService.thread?.localId
    ) {
        // replace temporary thread by the persisted one.
        const temporaryThread = thread;
        thread = await getLivechatThread({ persisted: true });
        if (!thread) {
            closeChatWindow(chatWindow);
            removeThread(temporaryThread);
            return;
        }
        chatWindow.thread = thread;
        removeThread(temporaryThread);
        if (chatbotService.active) {
            await chatbotService.postWelcomeSteps();
        }
    }
    const message = await _super(thread, body, params);
    if (!message) {
        notificationService.add(_t("Session expired... Please refresh and try again."));
        closeChatWindow(chatWindow);
        livechatService.leaveSession({ notifyServer: false });
        return;
    }
    chatbotService.bus.trigger("MESSAGE_POST", message);
    return message;
});

patchFn(updateThread, function (thread, data) {
    this._super(...arguments);
    if (data.operator_pid) {
        thread.operator = insertPersona({
            type: "partner",
            id: data.operator_pid[0],
            name: data.operator_pid[1],
        });
    }
});

patch(ThreadService.prototype, "im_livechat", {
    /**
     * @param {import("@web/env").OdooEnv} env
     * @param {{
     * "im_livechat.chatbot": import("@im_livechat/embed/chatbot/chatbot_service").ChatBotService,
     * "im_livechat.livechat": import("@im_livechat/embed/core/livechat_service").LivechatService,
     * notification: typeof import("@web/core/notifications/notification_service").notificationService.start,
     * }} services
     */
    setup(env, services) {
        this._super(env, services);
        chatbotService = services["im_livechat.chatbot"];
        livechatService = services["im_livechat.livechat"];
        notificationService = services.notification;
        store = this.store;
    },
});
