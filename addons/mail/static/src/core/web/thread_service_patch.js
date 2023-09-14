/* @odoo-module */

import { ThreadService, threadService } from "@mail/core/common/thread_service";
import { parseEmail } from "@mail/js/utils";

import { patch } from "@web/core/utils/patch";

let nextId = 1;

patch(ThreadService.prototype, {
    /**
     * @param {import("@web/env").OdooEnv} env
     * @param {Partial<import("services").Services>} services
     */
    setup(env, services) {
        super.setup(env, services);
        this.action = services.action;
        this.activityService = services["mail.activity"];
        this.chatWindowService = services["mail.chat_window"];
    },
    /**
     * @param {import("models").Thread} thread
     * @param {import("@mail/core/web/suggested_recipient").SuggestedRecipient[]} dataList
     */
    async insertSuggestedRecipients(thread, dataList) {
        const recipients = [];
        for (const data of dataList) {
            const [partner_id, emailInfo, lang, reason, customerInfo] = data;
            let [name, email] = emailInfo ? parseEmail(emailInfo) : [];
            if ((!name || name === email) && customerInfo?.name) {
                name = customerInfo.name;
            }
            recipients.push({
                id: nextId++,
                name,
                email,
                lang,
                reason,
                persona: partner_id ? { type: "partner", id: partner_id } : false,
                checked: true,
            });
        }
        thread.suggestedRecipients = recipients;
    },
    async leaveChannel(channel) {
        const chatWindow = this.store.discuss.chatWindows.find((c) => c.thread?.eq(channel));
        if (chatWindow) {
            await this.chatWindowService.close(chatWindow);
        }
        super.leaveChannel(...arguments);
    },
    /** @param {import("models").Thread} thread */
    async loadMoreFollowers(thread) {
        const followers = await this.orm.call(thread.model, "message_get_followers", [
            [thread.id],
            thread.followers.at(-1).id,
        ]);
        for (const data of followers) {
            const follower = this.store.Follower.insert({
                followedThread: thread,
                ...data,
            });
            if (follower.notEq(thread.selfFollower)) {
                thread.followers.add(follower);
            }
        }
    },
    async loadMoreRecipients(thread) {
        const recipients = await this.orm.call(
            thread.model,
            "message_get_followers",
            [[thread.id], thread.recipients.at(-1).id],
            { filter_recipients: true }
        );
        for (const data of recipients) {
            thread.recipients.add({ followedThread: thread, ...data });
        }
    },
    open(thread, replaceNewMessageChatWindow) {
        if (!this.store.discuss.isActive && !this.ui.isSmall) {
            this._openChatWindow(thread, replaceNewMessageChatWindow);
            return;
        }
        if (this.ui.isSmall && thread.model === "discuss.channel") {
            this._openChatWindow(thread, replaceNewMessageChatWindow);
            return;
        }
        if (thread.model !== "discuss.channel") {
            this.action.doAction({
                type: "ir.actions.act_window",
                res_id: thread.id,
                res_model: thread.model,
                views: [[false, "form"]],
            });
            return;
        }
        super.open(thread, replaceNewMessageChatWindow);
    },
    /** @param {import("models").Follower} recipient */
    removeRecipient(recipient) {
        recipient.followedThread.recipients.delete(recipient);
    },
    /**
     * @param {import("models").Follower} follower
     */
    async removeFollower(follower) {
        await this.orm.call(follower.followedThread.model, "message_unsubscribe", [
            [follower.followedThread.id],
            [follower.partner.id],
        ]);
        follower.delete();
    },
    async unpin(thread) {
        const chatWindow = this.store.discuss.chatWindows.find((c) => c.thread?.eq(thread));
        if (chatWindow) {
            await this.chatWindowService.close(chatWindow);
        }
        super.unpin(...arguments);
    },
    _openChatWindow(thread, replaceNewMessageChatWindow) {
        const chatWindow = this.store.ChatWindow.insert({
            folded: false,
            thread,
            replaceNewMessageChatWindow,
        });
        chatWindow.autofocus++;
        if (thread) {
            thread.state = "open";
        }
        this.chatWindowService.notifyState(chatWindow);
    },
    getRecentChannels() {
        return Object.values(this.store.Thread.records)
            .filter((thread) => thread.model === "discuss.channel")
            .sort((a, b) => {
                if (!a.lastInterestDateTime && !b.lastInterestDateTime) {
                    return 0;
                }
                if (a.lastInterestDateTime && !b.lastInterestDateTime) {
                    return -1;
                }
                if (!a.lastInterestDateTime && b.lastInterestDateTime) {
                    return 1;
                }
                return b.lastInterestDateTime.ts - a.lastInterestDateTime.ts;
            });
    },
    getNeedactionChannels() {
        return this.getRecentChannels().filter((channel) => this.getCounter(channel) > 0);
    },
});

patch(threadService, {
    dependencies: [...threadService.dependencies, "action", "mail.activity", "mail.chat_window"],
});
