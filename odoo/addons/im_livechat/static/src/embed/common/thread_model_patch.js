/* @odoo-module */

import { LivechatService, SESSION_STATE } from "@im_livechat/embed/common/livechat_service";

import { Record } from "@mail/core/common/record";
import { Thread } from "@mail/core/common/thread_model";
import { onChange } from "@mail/utils/common/misc";

import { patch } from "@web/core/utils/patch";
import { url } from "@web/core/utils/urls";

patch(Thread, {
    _insert(data) {
        const isUnknown = !this.get(data);
        const thread = super._insert(...arguments);
        const livechatService = this.env.services["im_livechat.livechat"];
        if (thread.type === "livechat" && isUnknown) {
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
    setup() {
        super.setup();
        this.chatbotTypingMessage = Record.one("Message", {
            compute() {
                if (this._store.env.services["im_livechat.chatbot"].isChatbotThread(this)) {
                    return {
                        id: Number.isInteger(this.id) ? -0.1 - this.id : -0.1,
                        res_id: this.id,
                        model: this.model,
                        author: this.operator,
                    };
                }
            },
        });
        this.livechatWelcomeMessage = Record.one("Message", {
            compute() {
                if (this.displayWelcomeMessage) {
                    const livechatService = this._store.env.services["im_livechat.livechat"];
                    return {
                        id: Number.isInteger(this.id) ? -0.2 - this.id : -0.2,
                        body: livechatService.options.default_message,
                        res_id: this.id,
                        model: this.model,
                        author: this.operator,
                    };
                }
            },
        });
        this.chatbotScriptId = null;
        /**
         * Indicates whether this thread was just created (i.e. no reload occurs
         * since the creation).
         */
        this.isNewlyCreated = false;
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
        return url(`/im_livechat/operator/${this.operator.id}/avatar`);
    },

    get isTransient() {
        return super.isTransient || this.id === LivechatService.TEMPORARY_ID;
    },

    get displayWelcomeMessage() {
        return !this._store.env.services["im_livechat.chatbot"].isChatbotThread(this);
    },
});
