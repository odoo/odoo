/** @odoo-module */

import { ThreadService, threadService } from "@mail/new/core/thread_service";
import { parseEmail } from "@mail/js/utils";

import { patch } from "@web/core/utils/patch";

let nextId = 1;

patch(ThreadService.prototype, "mail/web", {
    setup(env, services) {
        this._super(env, services);
        /** @type {import("@mail/new/chat/chat_window_service").ChatWindowService} */
        this.chatWindowService = services["mail.chat_window"];
    },
    /**
     * @param {import("@mail/new/core/thread_model").Thread} thread
     * @param {import("@mail/new/web/suggested_recipient").SuggestedRecipient[]} dataList
     */
    async insertSuggestedRecipients(thread, dataList) {
        const recipients = [];
        for (const data of dataList) {
            const [partner_id, emailInfo, lang, reason] = data;
            const [name, email] = emailInfo && parseEmail(emailInfo);
            recipients.push({
                id: nextId++,
                name,
                email,
                lang,
                reason,
                persona: partner_id
                    ? this.personaService.insert({
                          type: "partner",
                          id: partner_id,
                      })
                    : false,
                checked: partner_id ? true : false,
            });
        }
        thread.suggestedRecipients = recipients;
    },
    open(thread, replaceNewMessageChatWindow) {
        if (!this.store.discuss.isActive || this.store.isSmall) {
            const chatWindow = this.chatWindowService.insert({
                folded: false,
                thread,
                replaceNewMessageChatWindow,
            });
            chatWindow.autofocus++;
            if (thread) {
                thread.state = "open";
            }
            this.chatWindowService.notifyState(chatWindow);
            return;
        }
        this._super(thread, replaceNewMessageChatWindow);
    },
});

patch(threadService, "mail/web", {
    dependencies: [...threadService.dependencies, "mail.chat_window"],
});
