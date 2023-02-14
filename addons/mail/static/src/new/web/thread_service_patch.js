/** @odoo-module */

import { Follower } from "@mail/new/core/follower_model";
import { ThreadService, threadService } from "@mail/new/core/thread_service";
import { createLocalId } from "@mail/new/utils/misc";
import { parseEmail } from "@mail/js/utils";

import { _t } from "@web/core/l10n/translation";
import { patch } from "@web/core/utils/patch";

let nextId = 1;

patch(ThreadService.prototype, "mail/web", {
    setup(env, services) {
        this._super(env, services);
        /** @type {import("@mail/new/chat/chat_window_service").ChatWindowService} */
        this.chatWindowService = services["mail.chat_window"];
    },
    /**
     * @param {number} resId
     * @param {string} resModel
     * @param {['activities'|'followers'|'attachments'|'messages'|'suggestedRecipients']} requestList
     */
    async fetchData(
        resId,
        resModel,
        requestList = ["activities", "followers", "attachments", "messages", "suggestedRecipients"]
    ) {
        if (requestList.includes("messages")) {
            this.fetchNewMessages(this.insert({ model: resModel, id: resId }));
        }
        const result = await this.rpc("/mail/thread/data", {
            request_list: requestList,
            thread_id: resId,
            thread_model: resModel,
        });
        if ("attachments" in result) {
            result["attachments"] = result["attachments"].map((attachment) => ({
                ...attachment,
                originThread: this.insert(attachment.originThread[0][1]),
            }));
        }
        return result;
    },
    getThread(resModel, resId) {
        const localId = createLocalId(resModel, resId);
        if (localId in this.store.threads) {
            if (resId === false) {
                return this.store.threads[localId];
            }
            // to force a reload
            this.store.threads[localId].status = "new";
        }
        const thread = this.insert({
            id: resId,
            model: resModel,
            type: "chatter",
        });
        if (resId === false) {
            const tmpId = `virtual${this.nextId++}`;
            const tmpData = {
                id: tmpId,
                author: { id: this.store.self.id },
                body: _t("Creating a new record..."),
                message_type: "notification",
                trackingValues: [],
                res_id: thread.id,
                model: thread.model,
            };
            this.messageService.insert(tmpData);
        }
        return thread;
    },
    /**
     * @param {import("@mail/new/core/follower_model").Data} data
     * @returns {import("@mail/new/core/follower_model").Follower}
     */
    insertFollower(data) {
        let follower = this.store.followers[data.id];
        if (!follower) {
            this.store.followers[data.id] = new Follower();
            follower = this.store.followers[data.id];
        }
        Object.assign(follower, {
            followedThread: data.followedThread,
            id: data.id,
            isActive: data.is_active,
            partner: this.personaService.insert({ ...data.partner, type: "partner" }),
            _store: this.store,
        });
        if (!follower.followedThread.followers.includes(follower)) {
            follower.followedThread.followers.push(follower);
        }
        return follower;
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
    /**
     * @param {import("@mail/new/core/follower_model").Follower} follower
     */
    async removeFollower(follower) {
        await this.orm.call(follower.followedThread.model, "message_unsubscribe", [
            [follower.followedThread.id],
            [follower.partner.id],
        ]);
        const index = follower.followedThread.followers.indexOf(follower);
        if (index !== -1) {
            follower.followedThread.followers.splice(index, 1);
        }
        delete this.store.followers[follower.id];
    },
});

patch(threadService, "mail/web", {
    dependencies: [...threadService.dependencies, "mail.chat_window"],
});
