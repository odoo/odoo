/** @odoo-module */

import { markRaw, markup } from "@odoo/owl";
import { deserializeDateTime } from "@web/core/l10n/dates";
import { Deferred } from "@web/core/utils/concurrency";
import { url } from "@web/core/utils/urls";
import { htmlToTextContentInline, removeFromArray } from "./utils";

const { DateTime } = luxon;

export class Messaging {
    constructor(env, rpc, orm, user, router, initialThreadId) {
        this.env = env;
        this.rpc = rpc;
        this.orm = orm;
        this.nextId = 1;
        this.router = router;
        this.isReady = new Deferred();
        this.previewsProm = null;

        // base data
        this.user = {
            partnerId: user.partnerId,
            internalUserGroupId: null,
            uid: user.context.uid,
            avatarUrl: `/web/image?field=avatar_128&id=${user.userId}&model=res.users`,
        };
        this.partners = {};
        this.messages = {};
        this.threads = {};

        // messaging menu
        this.menu = {
            counter: 5, // sounds about right.
        };

        // discuss app
        this.discuss = {
            isActive: false,
            threadId: initialThreadId,
            channels: {
                id: "channels",
                name: env._t("Channels"),
                isOpen: false,
                canView: true,
                canAdd: true,
                addTitle: env._t("Add or join a channel"),
                counter: 0,
                threads: [], // list of ids
            },
            chats: {
                id: "chats",
                name: env._t("Direct messages"),
                isOpen: false,
                canView: false,
                canAdd: true,
                addTitle: env._t("Start a conversation"),
                counter: 0,
                threads: [], // list of ids
            },
            // mailboxes in sidebar
            inbox: this.createThread("inbox", env._t("Inbox"), "mailbox", { icon: "fa-inbox" }),
            starred: this.createThread("starred", env._t("Starred"), "mailbox", {
                icon: "fa-star-o",
                counter: 0,
            }),
            history: this.createThread("history", env._t("History"), "mailbox", {
                icon: "fa-history",
                counter: 0,
            }),
        };

        this.chatWindows = [];
    }

    /**
     * Import data received from init_messaging
     */
    initialize() {
        this.rpc("/mail/init_messaging", {}, { silent: true }).then((data) => {
            this.createPartner(data.current_partner.id, data.current_partner.name);
            this.createPartner(data.partner_root.id, data.partner_root.name);
            for (let channelData of data.channels) {
                this.createChannelThread(channelData);
            }
            this.sortChannels();
            const settings = data.current_user_settings;
            this.discuss.channels.isOpen = settings.is_discuss_sidebar_category_channel_open;
            this.discuss.chats.isOpen = settings.is_discuss_sidebar_category_chat_open;
            this.user.internalUserGroupId = data.internalUserGroupId;
            this.discuss.starred.counter = data.starred_counter;
            this.isReady.resolve();
        });
    }

    /**
     * todo: merge this with createThread (?)
     */
    createChannelThread(serverData) {
        const { id, name, last_message_id, seen_message_id, description, channel } = serverData;
        const isUnread = last_message_id !== seen_message_id;
        const type = channel.channel_type;
        const channelType = serverData.channel.channel_type;
        const canLeave =
            (channelType === "channel" || channelType === "group") &&
            !serverData.message_needaction_counter &&
            !serverData.group_based_subscription;
        const isAdmin = channelType !== "group" && serverData.create_uid === this.user.uid;
        this.createThread(id, name, type, {
            isUnread,
            icon: "fa-hashtag",
            description,
            serverData: serverData,
            canLeave,
            isAdmin,
        });
    }

    sortChannels() {
        this.discuss.channels.threads.sort((id1, id2) => {
            const thread1 = this.threads[id1];
            const thread2 = this.threads[id2];
            return String.prototype.localeCompare.call(thread1.name, thread2.name);
        });
    }

    createThread(id, name, type, data = {}) {
        if (id in this.threads) {
            return this.threads[id];
        }
        const thread = {
            id,
            name,
            type,
            counter: 0,
            messages: [],
            isUnread: false,
            icon: false,
            description: false,
            status: "new", // 'new', 'loading', 'ready'
            imgUrl: false,
            messages: [], // list of ids
            chatPartnerId: false,
            isAdmin: false,
            canLeave: data.canLeave || false,
        };
        for (let key in data) {
            thread[key] = data[key];
        }
        if (type === "channel") {
            this.discuss.channels.threads.push(thread.id);
            const avatarCacheKey = data.serverData.channel.avatarCacheKey;
            thread.imgUrl = `/web/image/mail.channel/${id}/avatar_128?unique=${avatarCacheKey}`;
        }
        if (type === "chat") {
            this.discuss.chats.threads.push(thread.id);
            if (data.serverData) {
                const avatarCacheKey = data.serverData.channel.avatarCacheKey;
                for (let elem of data.serverData.channel.channelMembers[0][1]) {
                    this.createPartner(elem.persona.partner.id, elem.persona.partner.name);
                }
                for (let partner of data.serverData.seen_partners_info) {
                    if (partner.partner_id !== this.user.partnerId) {
                        thread.chatPartnerId = partner.partner_id;
                        thread.name = this.partners[partner.partner_id].name;
                        break;
                    }
                }
                thread.imgUrl = `/web/image/res.partner/${thread.chatPartnerId}/avatar_128?unique=${avatarCacheKey}`;
            }
        }

        this.threads[id] = thread;
        return thread;
    }

    /**
     * TODO: remove thread argument and add a method addToThread or something
     * caller should do it, not this method
     */
    createMessage(body, data, thread, confirmed = true) {
        const { author, id, date, message_type: type } = data;
        if (id in this.messages) {
            return this.messages[id];
        }
        this.createPartner(author.id, author.name);
        const now = DateTime.now();
        const dateTime = markRaw(date ? deserializeDateTime(date) : now);
        let dateDay = dateTime.toLocaleString(DateTime.DATE_FULL);
        if (dateDay === now.toLocaleString(DateTime.DATE_FULL)) {
            dateDay = this.env._t("Today");
        }
        let isStarred = false;
        if (data.starred_partner_ids && data.starred_partner_ids.includes(this.user.partnerId)) {
            isStarred = true;
        }

        const message = {
            id,
            type,
            body,
            authorId: author.id,
            isAuthor: author.id === this.user.partnerId,
            confirmed,
            dateDay,
            dateTimeStr: dateTime.toLocaleString(DateTime.DATETIME_SHORT),
            dateTime,
            isStarred,
            isNote: data.is_note,
        };
        message.recordName = data.record_name;
        message.resId = data.res_id;
        message.resModel = data.model;
        message.url = `${url("/web")}#model=${data.model}&id=${data.res_id}`;
        if (type === "notification") {
            message.trackingValues = data.trackingValues;
            if (data.model === "mail.channel") {
                // is that correct?
                message.isNotification = true;
            }
            if (data.subtype_description) {
                message.subtype_description = data.subtype_description;
            }
        }
        this.messages[id] = message;
        if (thread.type === "chatter") {
            thread.messages.unshift(id);
        } else {
            thread.messages.push(id);
        }
        return message;
    }

    createPartner(id, name) {
        if (id in this.partners) {
            return this.partners[id];
        }
        const partner = { id, name };
        this.partners[id] = partner;
        return partner;
    }

    // -------------------------------------------------------------------------
    // process notifications received by the bus
    // -------------------------------------------------------------------------
    handleNotification(notifications) {
        console.log("notifications received", notifications);
        for (let notif of notifications) {
            switch (notif.type) {
                case "mail.channel/new_message":
                    {
                        const { id, message } = notif.payload;
                        const thread = this.threads[id];
                        const body = markup(message.body);
                        this.createMessage(body, message, thread);
                    }
                    break;
            }
        }
    }

    // -------------------------------------------------------------------------
    // actions that can be performed on the messaging system
    // -------------------------------------------------------------------------

    setDiscussThread(threadId) {
        this.discuss.threadId = threadId;
        const activeId =
            typeof threadId === "string" ? `mail.box_${threadId}` : `mail.channel_${threadId}`;
        this.router.pushState({ active_id: activeId });
    }

    openChatWindow(threadId) {
        const chatWindow = this.chatWindows.find((c) => c.threadId === threadId);
        if (!chatWindow) {
            this.chatWindows.push({ threadId, autofocus: 1 });
        } else {
            chatWindow.autofocus++;
        }
    }

    closeChatWindow(threadId) {
        const index = this.chatWindows.findIndex((c) => c.threadId === threadId);
        if (index > -1) {
            this.chatWindows.splice(index, 1);
        }
    }

    getChatterThread(resModel, resId) {
        let localId = resModel + "," + resId;
        if (localId in this.threads) {
            if (resId === false) {
                return this.threads[localId];
            }
            // to force a reload
            this.threads[localId].status = "new";
        }
        const thread = this.createThread(localId, localId, "chatter", { resId, resModel });
        if (resId === false) {
            const tmpId = `virtual${this.nextId++}`;
            const tmpData = {
                id: tmpId,
                author: { id: this.user.partnerId },
                message_type: "notification",
                trackingValues: [],
            };
            const body = this.env._t("Creating a new record...");
            this.createMessage(body, tmpData, thread, false);
        }
        return thread;
    }

    async fetchThreadMessages(threadId) {
        const thread = this.threads[threadId];
        if (thread.status !== "new") {
            return;
        }
        thread.status = "loading";
        let rawMessages;
        switch (thread.type) {
            case "mailbox":
                rawMessages = await this.rpc(`/mail/${threadId}/messages`, { limit: 30 });
                break;
            case "chatter":
                if (thread.resId === false) {
                    return;
                }
                rawMessages = await this.rpc("/mail/thread/messages", {
                    thread_id: thread.resId,
                    thread_model: thread.resModel,
                    limit: 30,
                });
                break;
            case "channel":
            case "chat":
                rawMessages = await this.rpc("/mail/channel/messages", {
                    channel_id: threadId,
                    limit: 30,
                });
                break;
            default:
                throw new Error("Unknown thread type");
        }
        const lastMessage = rawMessages[0];
        for (let data of rawMessages.reverse()) {
            this.createMessage(markup(data.body), data, thread);
        }
        thread.status = "ready";
        if (thread.isUnread && ["chat", "channel"].includes(thread.type)) {
            if (lastMessage) {
                this.rpc("/mail/channel/set_last_seen_message", {
                    channel_id: thread.id,
                    last_message_id: lastMessage.id,
                });
            }
        }
        thread.isUnread = false;
    }

    async fetchPreviews() {
        if (this.previewsProm) {
            return this.previewsProm;
        }
        let ids = [];
        for (let thread of Object.values(this.threads)) {
            if (thread.type === "channel" || thread.type === "chat") {
                ids.push(thread.id);
            }
        }
        if (!ids.length) {
            this.previewsProm = Promise.resolve([]);
        } else {
            this.previewsProm = this.orm
                .call("mail.channel", "channel_fetch_preview", [ids])
                .then((previews) => {
                    for (let preview of previews) {
                        preview.last_message.date = markRaw(
                            deserializeDateTime(preview.last_message.date)
                        );
                        preview.last_message.body = htmlToTextContentInline(
                            preview.last_message.body
                        );
                        const { id, name } = preview.last_message.author;
                        this.createPartner(id, name);
                    }
                    return previews;
                });
        }
        return this.previewsProm;
    }
    async postMessage(threadId, body, isNote = false) {
        let tmpMsg;
        const thread = this.threads[threadId];
        const subtype = isNote ? "mail.mt_note" : "mail.mt_comment";
        const params = {
            post_data: {
                body,
                attachment_ids: [],
                message_type: "comment",
                partner_ids: [],
                subtype_xmlid: subtype,
            },
            thread_id: threadId,
            thread_model: "mail.channel",
        };
        if (thread.type === "chatter") {
            params.thread_id = thread.resId;
            params.thread_model = thread.resModel;
            // need to get suggested recipients here, if !isNote...
            params.post_data.partner_ids = [];
        } else {
            const tmpId = `pending${this.nextId++}`;
            const tmpData = { id: tmpId, author: { id: this.user.partnerId } };
            tmpMsg = this.createMessage(markup(body), tmpData, thread, false);
        }
        const data = await this.rpc(`/mail/message/post`, params);
        if (thread.type !== "chatter") {
            removeFromArray(thread.messages, tmpMsg.id);
            delete this.messages[tmpMsg.id];
        }
        this.createMessage(markup(data.body), data, thread);
    }

    openDiscussion(threadId) {
        if (this.discuss.isActive) {
            this.setDiscussThread(threadId);
        } else {
            this.openChatWindow(threadId);
        }
    }

    async createChannel(name) {
        const channel = await this.orm.call("mail.channel", "channel_create", [
            name,
            this.user.internalUserGroupId,
        ]);
        this.createChannelThread(channel);
        this.sortChannels();
        this.discuss.threadId = channel.id;
    }

    async joinChannel(id, name) {
        await this.orm.call("mail.channel", "add_members", [[id]], {
            partner_ids: [this.user.partnerId],
        });
        this.createThread(id, name, "channel", {
            serverData: { channel: { avatarCacheKey: "hello" } },
        });
        this.sortChannels();
        this.discuss.threadId = id;
    }

    async joinChat(id, name) {
        const data = await this.orm.call("mail.channel", "channel_get", [], {
            partners_to: [id],
        });
        this.createThread(data.id, name, "chat", { serverData: data });
        this.discuss.threadId = data.id;
    }

    async leaveChannel(id) {
        await this.orm.call("mail.channel", "action_unfollow", [id]);
        removeFromArray(this.discuss.channels.threads, id);
        this.setDiscussThread(this.discuss.channels.threads[0]);
    }

    async toggleStar(messageId) {
        const message = this.messages[messageId];
        message.isStarred = !message.isStarred;
        if (message.isStarred) {
            this.discuss.starred.counter++;
            this.discuss.starred.messages.push(messageId);
        } else {
            this.discuss.starred.counter--;
            removeFromArray(this.discuss.starred.messages, messageId);
        }
        this.discuss.starred.messages.sort();
        await this.orm.call("mail.message", "toggle_message_starred", [[messageId]]);
    }

    async unstarAll() {
        // apply the change immediately for faster feedback
        this.discuss.starred.counter = 0;
        this.discuss.starred.messages = [];
        await this.orm.call("mail.message", "unstar_all");
    }

    // -------------------------------------------------------------------------
    // rtc (audio and video calls)
    // -------------------------------------------------------------------------

    startCall(threadId) {
        this.threads[threadId].inCall = true;
    }

    stopCall(threadId) {
        this.threads[threadId].inCall = false;
    }
}
