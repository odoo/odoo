/* @odoo-module */

import { ThreadService, threadService } from "@mail/core/common/thread_service";
import { parseEmail } from "@mail/js/utils";

import { markup } from "@odoo/owl";

import { _t } from "@web/core/l10n/translation";
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
     * @param {['activities'|'followers'|'attachments'|'messages'|'suggestedRecipients']} requestList
     */
    async fetchData(
        thread,
        requestList = ["activities", "followers", "attachments", "messages", "suggestedRecipients"]
    ) {
        thread.isLoadingAttachments =
            thread.isLoadingAttachments || requestList.includes("attachments");
        if (requestList.includes("messages")) {
            this.fetchNewMessages(thread);
        }
        const result = await this.rpc("/mail/thread/data", {
            request_list: requestList,
            thread_id: thread.id,
            thread_model: thread.model,
        });
        if ("attachments" in result) {
            result["attachments"] = result["attachments"].map((attachment) => ({
                ...attachment,
                originThread: this.store.Thread.insert(attachment.originThread[0][1]),
            }));
        }
        thread.canPostOnReadonly = result.canPostOnReadonly;
        thread.hasReadAccess = result.hasReadAccess;
        thread.hasWriteAccess = result.hasWriteAccess;
        if ("activities" in result) {
            const existingIds = new Set();
            for (const activity of result.activities) {
                if (activity.note) {
                    activity.note = markup(activity.note);
                }
                existingIds.add(this.store.Activity.insert(activity).id);
            }
            for (const activity of thread.activities) {
                if (!existingIds.has(activity.id)) {
                    this.activityService.delete(activity);
                }
            }
        }
        if ("attachments" in result) {
            thread.update({
                areAttachmentsLoaded: true,
                attachments: result.attachments,
                isLoadingAttachments: false,
            });
        }
        if ("mainAttachment" in result) {
            thread.mainAttachment = result.mainAttachment.id
                ? this.store.Attachment.insert(result.mainAttachment)
                : undefined;
        }
        if (!thread.mainAttachment && thread.attachmentsInWebClientView.length > 0) {
            this.setMainAttachmentFromIndex(thread, 0);
        }
        if ("followers" in result) {
            if (result.selfFollower) {
                thread.selfFollower = this.store.Follower.insert({
                    followedThread: thread,
                    ...result.selfFollower,
                });
            }
            thread.followersCount = result.followersCount;
            for (const followerData of result.followers) {
                const follower = this.store.Follower.insert({
                    followedThread: thread,
                    ...followerData,
                });
                if (follower.notEq(thread.selfFollower)) {
                    thread.followers.add(follower);
                }
            }
            thread.recipientsCount = result.recipientsCount;
            for (const recipientData of result.recipients) {
                const recipient = this.store.Follower.insert({
                    followedThread: thread,
                    ...recipientData,
                });
                thread.recipients.add(recipient);
            }
        }
        if ("suggestedRecipients" in result) {
            this.insertSuggestedRecipients(thread, result.suggestedRecipients);
        }
        return result;
    },
    getThread(resModel, resId) {
        let thread = this.store.Thread.get({ model: resModel, id: resId });
        if (thread) {
            if (resId === false) {
                return thread;
            }
            // to force a reload
            thread.status = "new";
        }
        thread = this.store.Thread.insert({
            id: resId,
            model: resModel,
            type: "chatter",
        });
        if (resId === false) {
            const tmpId = this.messageService.getNextTemporaryId();
            const tmpData = {
                id: tmpId,
                author: { id: this.store.self.id },
                body: _t("Creating a new record..."),
                message_type: "notification",
                trackingValues: [],
                res_id: thread.id,
                model: thread.model,
            };
            const message = this.store.Message.insert(tmpData);
            thread.messages.push(message);
        }
        return thread;
    },
    /**
     * @param {import("models").Thread} thread
     * @param {import("@mail/core/web/suggested_recipient").SuggestedRecipient[]} dataList
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
                    ? this.store.Persona.insert({
                          type: "partner",
                          id: partner_id,
                      })
                    : false,
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
            const recipient = this.store.Follower.insert({
                followedThread: thread,
                ...data,
            });
            thread.recipients.add(recipient);
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
