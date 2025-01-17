import { ThreadService, threadService } from "@mail/core/common/thread_service";
import { patch } from "@web/core/utils/patch";
import { Record } from "@mail/core/common/record";
import { assignDefined, compareDatetime } from "@mail/utils/common/misc";
import { rpc } from "@web/core/network/rpc";
import { isMobileOS } from "@web/core/browser/feature_detection";

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
        const result = await rpc("/mail/thread/data", {
            request_list: requestList,
            thread_id: thread.id,
            thread_model: thread.model,
        });
        this.store.Thread.insert(result, { html: true });
        if ("attachments" in result) {
            Object.assign(thread, {
                areAttachmentsLoaded: true,
                isLoadingAttachments: false,
            });
        }
        if (!thread.mainAttachment && thread.attachmentsInWebClientView.length > 0) {
            this.setMainAttachmentFromIndex(thread, 0);
        }
        return result;
    },
    closeChatWindow(channel) {
        const chatWindow = this.store.discuss.chatWindows.find((c) => c.thread?.eq(channel));
        if (chatWindow) {
            this.chatWindowService.close(chatWindow, { notifyState: false });
        }
    },
    async leaveChannel(channel) {
        this.closeChatWindow(channel);
        super.leaveChannel(...arguments);
    },
    /** @param {import("models").Thread} thread */
    async loadMoreFollowers(thread) {
        const followers = await this.orm.call(thread.model, "message_get_followers", [
            [thread.id],
            thread.followers.at(-1).id,
        ]);
        Record.MAKE_UPDATE(() => {
            for (const data of followers) {
                const follower = this.store.Follower.insert({
                    thread,
                    ...data,
                });
                if (follower.notEq(thread.selfFollower)) {
                    thread.followers.add(follower);
                }
            }
        });
    },
    async loadMoreRecipients(thread) {
        const recipients = await this.orm.call(
            thread.model,
            "message_get_followers",
            [[thread.id], thread.recipients.at(-1).id],
            { filter_recipients: true }
        );
        Record.MAKE_UPDATE(() => {
            for (const data of recipients) {
                thread.recipients.add({ thread, ...data });
            }
        });
    },
    /** @override */
    open(thread, replaceNewMessageChatWindow, options) {
        if (thread.model === "discuss.channel") {
            this.store.env.services["bus_service"].addChannel(thread.busChannel);
        }
        if (!this.store.discuss.isActive && !this.ui.isSmall) {
            this._openChatWindow(thread, replaceNewMessageChatWindow, options);
            return;
        }
        if (this.ui.isSmall && thread.model === "discuss.channel") {
            this._openChatWindow(thread, replaceNewMessageChatWindow, options);
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
        recipient.thread.recipients.delete(recipient);
    },
    /**
     * @param {import("models").Follower} follower
     */
    async removeFollower(follower) {
        await this.orm.call(follower.thread.model, "message_unsubscribe", [
            [follower.thread.id],
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
    _openChatWindow(thread, replaceNewMessageChatWindow, { autofocus = true, openMessagingMenuOnClose } = {}) {
        const chatWindow = this.store.ChatWindow.insert(
            assignDefined(
                {
                    folded: false,
                    replaceNewMessageChatWindow,
                    thread,
                },
                {
                    openMessagingMenuOnClose,
                }
            )
        );
        if (autofocus && !isMobileOS()) {
            chatWindow.autofocus++;
        }
        if (thread) {
            thread.state = "open";
        }
        this.chatWindowService.notifyState(chatWindow);
    },
    getRecentChannels() {
        return Object.values(this.store.Thread.records)
            .filter((thread) => thread.model === "discuss.channel")
            .sort((a, b) => compareDatetime(b.lastInterestDt, a.lastInterestDt) || b.id - a.id);
    },
    getNeedactionChannels() {
        return this.getRecentChannels().filter((channel) => channel.importantCounter > 0);
    },
});

patch(threadService, {
    dependencies: [...threadService.dependencies, "action", "mail.activity", "mail.chat_window"],
});
