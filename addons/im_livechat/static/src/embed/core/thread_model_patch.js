/* @odoo-module */

import { Thread } from "@mail/core/common/thread_model";
import { onChange } from "@mail/utils/common/misc";

import { patch } from "@web/core/utils/patch";
import { session } from "@web/session";
import { SESSION_STATE } from "./livechat_service";

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

patch(Thread, {
    insert(data) {
        const isUnknown = !this.store.Thread.findById(data);
        const thread = super.insert(...arguments);
        if (thread.type === "livechat" && isUnknown) {
            if (
                this.env.services["im_livechat.livechat"].displayWelcomeMessage &&
                !this.env.services["im_livechat.chatbot"].isChatbotThread(thread)
            ) {
                this.env.services["im_livechat.livechat"].welcomeMessage =
                    this.store.Message.insert({
                        id: this.store.Message.getNextTemporaryId(),
                        body: this.env.services["im_livechat.livechat"].options.default_message,
                        res_id: thread.id,
                        model: thread.model,
                        author: thread.operator,
                    });
            }
            if (this.env.services["im_livechat.chatbot"].isChatbotThread(thread)) {
                this.env.services["im_livechat.chatbot"].typingMessage = this.store.Message.insert({
                    id: this.store.Message.getNextTemporaryId(),
                    res_id: thread.id,
                    model: thread.model,
                    author: thread.operator,
                });
            }
            onChange(thread, "state", () => {
                if (
                    ![SESSION_STATE.CLOSED, SESSION_STATE.NONE].includes(
                        this.env.services["im_livechat.livechat"].state
                    )
                ) {
                    this.env.services["im_livechat.livechat"].updateSession({
                        state: thread.state,
                    });
                }
            });
            onChange(thread, "seen_message_id", () => {
                if (
                    ![SESSION_STATE.CLOSED, SESSION_STATE.NONE].includes(
                        this.env.services["im_livechat.livechat"].state
                    )
                ) {
                    this.env.services["im_livechat.livechat"].updateSession({
                        seen_message_id: thread.seen_message_id,
                    });
                }
            });
            onChange(thread, "message_unread_counter", () => {
                if (
                    ![SESSION_STATE.CLOSED, SESSION_STATE.NONE].includes(
                        this.env.services["im_livechat.livechat"].state
                    )
                ) {
                    this.env.services["im_livechat.livechat"].updateSession({
                        channel: thread.channel,
                    });
                }
            });
            this.store.livechatThread = thread;
        }
        return thread;
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
});
