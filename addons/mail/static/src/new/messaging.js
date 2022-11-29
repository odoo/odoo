/** @odoo-module */

import { markRaw, markup, toRaw, reactive } from "@odoo/owl";
import { deserializeDateTime } from "@web/core/l10n/dates";
import { Deferred } from "@web/core/utils/concurrency";
import { sprintf } from "@web/core/utils/strings";
import { url } from "@web/core/utils/urls";
import { htmlToTextContentInline, convertBrToLineBreak, removeFromArray } from "./utils";
import { prettifyMessageContent } from "./message_prettify_utils";
import { Thread } from "./core/thread_model";
import { Partner } from "./core/partner_model";

const { DateTime } = luxon;

const FETCH_MSG_LIMIT = 30;

export const asyncMethods = [
    "fetchThreadMessages",
    "fetchPreviews",
    "postMessage",
    "updateMessage",
    "createChannel",
    "getChat",
    "joinChannel",
    "joinChat",
    "leaveChannel",
    "openChat",
    "toggleStar",
    "deleteMessage",
    "unstarAll",
    "notifyThreadNameToServer",
];

export class Messaging {
    constructor(...args) {
        this.setup(...args);
    }

    setup(env, rpc, orm, user, router, initialThreadId, im_status, notification) {
        this.env = env;
        this.rpc = rpc;
        this.orm = orm;
        this.notification = notification;
        this.nextId = 1;
        this.router = router;
        this.isReady = new Deferred();
        this.previewsProm = null;
        this.imStatusService = im_status;

        this.state = reactive({
            // base data
            user: {
                partnerId: user.partnerId,
                uid: user.context.uid,
                avatarUrl: `/web/image?field=avatar_128&id=${user.userId}&model=res.users`,
            },
            partners: {},
            partnerRoot: {},
            messages: {},
            threads: {},
            users: {},
            internalUserGroupId: null,
            registeredImStatusPartners: reactive([], () => this.updateImStatusRegistration()),
            // messaging menu
            menu: {
                counter: 5, // sounds about right.
            },
            // discuss app
            discuss: {
                isActive: false,
                messageToReplyTo: null,
                threadId: initialThreadId,
                channels: {
                    extraClass: "o-mail-category-channel",
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
                    extraClass: "o-mail-category-chat",
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
                inbox: null,
                starred: null,
                history: null,
            },
            chatWindows: [],
            commands: [],
        });
        this.state.discuss.inbox = Thread.insert(this.state, {
            id: "inbox",
            name: env._t("Inbox"),
            type: "mailbox",
            icon: "fa-inbox",
        });
        this.state.discuss.starred = Thread.insert(this.state, {
            id: "starred",
            name: env._t("Starred"),
            type: "mailbox",
            icon: "fa-star-o",
            counter: 0,
        });
        this.state.discuss.history = Thread.insert(this.state, {
            id: "history",
            name: env._t("History"),
            type: "mailbox",
            icon: "fa-history",
            counter: 0,
        });
        this.updateImStatusRegistration();
    }

    /**
     * Import data received from init_messaging
     */
    initialize() {
        this.rpc("/mail/init_messaging", {}, { silent: true }).then((data) => {
            Partner.insert(this.state, {
                id: data.current_partner.id,
                name: data.current_partner.name,
            });
            this.state.partnerRoot = Partner.insert(this.state, {
                id: data.partner_root.id,
                name: data.partner_root.name,
            });
            for (const channelData of data.channels) {
                this.createChannelThread(channelData);
            }
            this.sortChannels();
            const settings = data.current_user_settings;
            this.state.discuss.channels.isOpen = settings.is_discuss_sidebar_category_channel_open;
            this.state.discuss.chats.isOpen = settings.is_discuss_sidebar_category_chat_open;
            this.state.internalUserGroupId = data.internalUserGroupId;
            this.state.discuss.starred.counter = data.starred_counter;
            this.isReady.resolve();
            this.initCommands();
        });
    }

    /**
     * todo: merge this with Thread.insert() (?)
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
        const isAdmin = channelType !== "group" && serverData.create_uid === this.state.user.uid;
        Thread.insert(this.state, {
            id,
            name,
            type,
            isUnread,
            icon: "fa-hashtag",
            description,
            serverData: serverData,
            canLeave,
            isAdmin,
        });
    }

    sortChannels() {
        this.state.discuss.channels.threads.sort((id1, id2) => {
            const thread1 = this.state.threads[id1];
            const thread2 = this.state.threads[id2];
            return String.prototype.localeCompare.call(thread1.name, thread2.name);
        });
    }

    updateImStatusRegistration() {
        this.imStatusService.registerToImStatus(
            "res.partner",
            toRaw(this.state.registeredImStatusPartners)
        );
    }

    /**
     * TODO: remove thread argument and add a method addToThread or something
     * caller should do it, not this method
     */
    createMessage(body, data, thread) {
        const {
            attachment_ids: attachments,
            author,
            id,
            date,
            message_type: type,
            needaction,
            parentMessage,
            subtype_description: subtypeDescription,
            trackingValues,
            linkPreviews,
        } = data;
        if (id in this.state.messages) {
            return this.state.messages[id];
        }
        const now = DateTime.now();
        const dateTime = markRaw(date ? deserializeDateTime(date) : now);
        let dateDay = dateTime.toLocaleString(DateTime.DATE_FULL);
        if (dateDay === now.toLocaleString(DateTime.DATE_FULL)) {
            dateDay = this.env._t("Today");
        }
        let isStarred = false;
        if (
            data.starred_partner_ids &&
            data.starred_partner_ids.includes(this.state.user.partnerId)
        ) {
            isStarred = true;
        }

        const message = {
            attachments,
            id,
            type,
            body,
            author: Partner.insert(this.state, { id: author.id, name: author.name }),
            isAuthor: author.id === this.state.user.partnerId,
            dateDay,
            dateTimeStr: dateTime.toLocaleString(DateTime.DATETIME_SHORT),
            dateTime,
            isStarred,
            isNote: data.is_note,
            isTransient: data.is_transient,
            needaction,
            parentMessage,
            subtypeDescription,
            trackingValues,
            linkPreviews,
        };
        if (parentMessage) {
            const { body, ...data } = parentMessage;
            message["parentMessage"] = this.createMessage(body, data, thread);
        }
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
        this.state.messages[id] = message;
        if (thread.type === "chatter") {
            thread.messages.unshift(id);
        } else {
            thread.messages.push(id);
        }
        this.sortThreadMessages(thread);
        // return reactive version
        return this.state.messages[id];
    }

    sortThreadMessages(thread) {
        thread.messages.sort((msgId1, msgId2) => msgId1 - msgId2);
    }

    /**
     * Create a transient message, i.e. a message which does not come
     * from a member of the channel. Usually a log message, such as one
     * generated from a command with ('/').
     *
     * @param {Object} data
     */
    createTransientMessage(data) {
        const { body, res_id: threadId } = data;
        const lastMessageId = Object.values(this.state.messages).reduce(
            (lastMessageId, message) => Math.max(lastMessageId, message.id),
            0
        );
        this.createMessage(
            markup(body),
            {
                author: this.state.partnerRoot,
                id: lastMessageId + 0.01,
                is_note: true,
                is_transient: true,
            },
            this.state.threads[threadId]
        );
    }

    initCommands() {
        const commands = [
            {
                help: this.env._t("Show a helper message"),
                methodName: "execute_command_help",
                name: "help",
            },
            {
                help: this.env._t("Leave this channel"),
                methodName: "execute_command_leave",
                name: "leave",
            },
            {
                channel_types: ["channel", "chat"],
                help: this.env._t("List users in the current channel"),
                methodName: "execute_command_who",
                name: "who",
            },
        ];
        for (const c of commands) {
            this.state.commands.push(c);
        }
    }

    // -------------------------------------------------------------------------
    // process notifications received by the bus
    // -------------------------------------------------------------------------
    handleNotification(notifications) {
        console.log("notifications received", notifications);
        for (const notif of notifications) {
            switch (notif.type) {
                case "mail.channel/new_message":
                    {
                        const { id, message } = notif.payload;
                        const thread = this.state.threads[id];
                        const body = markup(message.body);
                        this.createMessage(body, message, thread);
                    }
                    break;
                case "mail.record/insert":
                    {
                        const receivedPartner = notif.payload.Partner;
                        if (receivedPartner) {
                            // If Partner in the payload is a single object
                            if (receivedPartner.im_status) {
                                const im_status = receivedPartner.im_status;
                                const id = receivedPartner.id;
                                this.state.partners[id].im_status = im_status;
                            } else {
                                // If Partner in the payload is an array of partners
                                for (const partner of receivedPartner) {
                                    if (partner.im_status) {
                                        const im_status = partner.im_status;
                                        const id = partner.id;
                                        this.state.partners[id].im_status = im_status;
                                    }
                                }
                            }
                        }
                        const { LinkPreview: linkPreviews } = notif.payload;
                        if (linkPreviews) {
                            for (const linkPreview of linkPreviews) {
                                this.state.messages[linkPreview.message.id].linkPreviews.push(
                                    linkPreview
                                );
                            }
                        }
                    }
                    break;
                case "mail.channel/transient_message":
                    return this.createTransientMessage(notif.payload);
                case "mail.link.preview/delete":
                    {
                        const { id, message_id } = notif.payload;
                        const index = this.state.messages[message_id].linkPreviews.findIndex(
                            (linkPreview) => linkPreview.id === id
                        );
                        delete this.state.messages[message_id].linkPreviews[index];
                    }
                    break;
                case "mail.message/toggle_star": {
                    const { message_ids: messageIds, starred } = notif.payload;
                    for (const messageId of messageIds) {
                        const message = this.state.messages[messageId];
                        if (!message) {
                            continue;
                        }
                        this.updateMessageStarredState(message, starred);
                    }
                    this.state.discuss.starred.messages.sort();
                    break;
                }
                case "mail.channel.member/seen": {
                    const { channel_id, last_message_id, partner_id } = notif.payload;
                    const channel = this.state.threads[channel_id];
                    if (!channel) {
                        // for example seen from another browser, the current one has no
                        // knowledge of the channel
                        return;
                    }
                    if (this.state.user.partnerId === partner_id) {
                        channel.serverLastSeenMsgByCurrentUser = last_message_id;
                    }
                    break;
                }
            }
        }
    }

    // -------------------------------------------------------------------------
    // actions that can be performed on the messaging system
    // -------------------------------------------------------------------------

    setDiscussThread(threadId) {
        this.state.discuss.threadId = threadId;
        const activeId =
            typeof threadId === "string" ? `mail.box_${threadId}` : `mail.channel_${threadId}`;
        this.router.pushState({ active_id: activeId });
    }

    openChatWindow(threadId) {
        const chatWindow = this.state.chatWindows.find((c) => c.threadId === threadId);
        if (!chatWindow) {
            this.state.chatWindows.push({ threadId, autofocus: 1, folded: false });
        } else {
            chatWindow.folded = false;
            chatWindow.autofocus++;
        }
    }

    closeChatWindow(threadId) {
        const index = this.state.chatWindows.findIndex((c) => c.threadId === threadId);
        if (index > -1) {
            this.state.chatWindows.splice(index, 1);
        }
    }

    getChatterThread(resModel, resId) {
        const localId = resModel + "," + resId;
        if (localId in this.state.threads) {
            if (resId === false) {
                return this.state.threads[localId];
            }
            // to force a reload
            this.state.threads[localId].status = "new";
        }
        const thread = Thread.insert(this.state, {
            id: localId,
            name: localId,
            type: "chatter",
            resId,
            resModel,
        });
        if (resId === false) {
            const tmpId = `virtual${this.nextId++}`;
            const tmpData = {
                id: tmpId,
                author: { id: this.state.user.partnerId },
                message_type: "notification",
                trackingValues: [],
            };
            const body = this.env._t("Creating a new record...");
            this.createMessage(body, tmpData, thread);
        }
        return thread;
    }

    fetchChatterData(
        resId,
        resModel,
        requestList = ["activities", "followers", "attachments", "messages"]
    ) {
        return this.rpc("/mail/thread/data", {
            request_list: requestList,
            thread_id: resId,
            thread_model: resModel,
        });
    }

    async fetchThreadMessages(thread, { min, max }) {
        thread.status = "loading";
        let rawMessages;
        switch (thread.type) {
            case "mailbox":
                rawMessages = await this.rpc(`/mail/${thread.id}/messages`, {
                    limit: FETCH_MSG_LIMIT,
                    max_id: max,
                    min_id: min,
                });
                break;
            case "chatter":
                if (thread.resId === false) {
                    return [];
                }
                rawMessages = await this.rpc("/mail/thread/messages", {
                    thread_id: thread.resId,
                    thread_model: thread.resModel,
                    limit: FETCH_MSG_LIMIT,
                    max_id: max,
                    min_id: min,
                });
                break;
            case "channel":
            case "chat":
                rawMessages = await this.rpc("/mail/channel/messages", {
                    channel_id: thread.id,
                    limit: FETCH_MSG_LIMIT,
                    max_id: max,
                    min_id: min,
                });
                break;
            default:
                throw new Error("Unknown thread type");
        }
        thread.status = "ready";
        const messages = rawMessages
            .reverse()
            .map((data) => this.createMessage(markup(data.body), data, thread));
        return messages;
    }

    async fetchThreadMessagesNew(threadId) {
        const thread = this.state.threads[threadId];
        const fetchedMsgs = await this.fetchThreadMessages(thread, {
            min: this.getThreadMostRecentMsg(thread),
        });
        const mostRecentMsgId = this.getThreadMostRecentMsg(thread);
        if (thread.isUnread && ["chat", "channel"].includes(thread.type)) {
            if (fetchedMsgs.length > 0) {
                this.rpc("/mail/channel/set_last_seen_message", {
                    channel_id: thread.id,
                    last_message_id: mostRecentMsgId,
                });
            }
        }
        Object.assign(thread, {
            isUnread: false,
            loadMore: fetchedMsgs.length === FETCH_MSG_LIMIT,
        });
    }

    async fetchThreadMessagesMore(threadId) {
        const thread = this.state.threads[threadId];
        const fetchedMsgs = await this.fetchThreadMessages(thread, {
            max: this.getThreadOldestMsg(thread),
        });
        if (fetchedMsgs.length < FETCH_MSG_LIMIT) {
            thread.loadMore = false;
        }
    }

    getThreadMostRecentMsg(thread) {
        if (thread.messages.length === 0) {
            return undefined;
        }
        return Math.max(...thread.messages);
    }

    getThreadOldestMsg(thread) {
        if (thread.messages.length === 0) {
            return undefined;
        }
        return Math.min(...thread.messages);
    }

    async fetchPreviews() {
        if (this.previewsProm) {
            return this.previewsProm;
        }
        const ids = [];
        for (const thread of Object.values(this.state.threads)) {
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
                    for (const preview of previews) {
                        preview.last_message.date = markRaw(
                            deserializeDateTime(preview.last_message.date)
                        );
                        preview.last_message.body = htmlToTextContentInline(
                            preview.last_message.body
                        );
                        const { id, name } = preview.last_message.author;
                        Partner.insert(this.state, { id, name });
                    }
                    return previews;
                });
        }
        return this.previewsProm;
    }

    async postInboxReply(threadId, threadModel, body, postData) {
        const thread = this.getChatterThread(threadModel, threadId);
        const message = await this.postMessage(thread.id, body, postData);
        this.env.services.notification.add(
            sprintf(this.env._t('Message posted on "%s"'), message.recordName),
            { type: "info" }
        );
        return message;
    }

    async postMessage(threadId, body, { isNote = false, parentId }) {
        const command = this.getCommandFromText(threadId, body);
        if (command) {
            await this.excuteCommand(threadId, command, body);
            return;
        }
        let tmpMsg;
        const thread = this.state.threads[threadId];
        const subtype = isNote ? "mail.mt_note" : "mail.mt_comment";
        const params = {
            post_data: {
                body: await prettifyMessageContent(body),
                attachment_ids: [],
                message_type: "comment",
                partner_ids: [],
                subtype_xmlid: subtype,
            },
            thread_id: threadId,
            thread_model: "mail.channel",
        };
        if (parentId) {
            params.post_data.parent_id = parentId;
        }
        if (thread.type === "chatter") {
            params.thread_id = thread.resId;
            params.thread_model = thread.resModel;
            // need to get suggested recipients here, if !isNote...
            params.post_data.partner_ids = [];
        } else {
            const tmpId = `pending${this.nextId++}`;
            const tmpData = {
                id: tmpId,
                author: { id: this.state.user.partnerId },
                res_id: thread.id,
                model: "mail.channel",
            };
            if (parentId) {
                tmpData.parentMessage = this.state.messages[parentId];
            }
            tmpMsg = this.createMessage(
                markup(await prettifyMessageContent(body)),
                tmpData,
                thread
            );
        }
        const data = await this.rpc(`/mail/message/post`, params);
        if (!this.isMessageEmpty(data)) {
            this.rpc(`/mail/link_preview`, { message_id: data.id }, { silent: true });
        }
        if (thread.type !== "chatter") {
            removeFromArray(thread.messages, tmpMsg.id);
            delete this.state.messages[tmpMsg.id];
        }
        return this.createMessage(markup(data.body), data, thread);
    }

    async excuteCommand(threadId, command, body = "") {
        return this.orm.call("mail.channel", command.methodName, [[threadId]], {
            body,
        });
    }

    getCommandFromText(threadId, content) {
        const thread = this.state.threads[threadId];
        if (["channel", "chat", "group"].includes(thread.type)) {
            if (content.startsWith("/")) {
                const firstWord = content.substring(1).split(/\s/)[0];
                return this.state.commands.find((command) => {
                    if (command.name !== firstWord) {
                        return false;
                    }
                    if (command.channel_types) {
                        return command.channel_types.includes(thread.type);
                    }
                    return true;
                });
            }
        }
        return undefined;
    }

    async updateMessage(messageId, body) {
        const message = this.state.messages[messageId];
        if (convertBrToLineBreak(message.body) === body) {
            return;
        }
        const data = await this.rpc("/mail/message/update_content", {
            attachment_ids: [],
            body: markup(body),
            message_id: message.id,
        });
        message.body = markup(data.body);
    }

    openDiscussion(threadId) {
        if (this.state.discuss.isActive) {
            this.setDiscussThread(threadId);
        } else {
            this.openChatWindow(threadId);
        }
    }

    toggleReplyTo(message) {
        if (this.state.discuss.messageToReplyTo === message) {
            this.state.discuss.messageToReplyTo = null;
        } else {
            this.state.discuss.messageToReplyTo = message;
        }
    }

    cancelReplyTo() {
        this.state.discuss.messageToReplyTo = null;
    }

    async createChannel(name) {
        const channel = await this.orm.call("mail.channel", "channel_create", [
            name,
            this.state.internalUserGroupId,
        ]);
        this.createChannelThread(channel);
        this.sortChannels();
        this.state.discuss.threadId = channel.id;
    }

    async getChat({ userId, partnerId }) {
        if (!partnerId) {
            let user = this.state.users[userId];
            if (!user) {
                this.state.users[userId] = { id: userId };
                user = this.state.users[userId];
            }
            if (!user.partner_id) {
                const [userData] = await this.orm.silent.read(
                    "res.users",
                    [user.id],
                    ["partner_id"],
                    {
                        context: { active_test: false },
                    }
                );
                if (userData) {
                    user.partner_id = userData.partner_id[0];
                }
            }
            if (!user.partner_id) {
                this.notification.add(this.env._t("You can only chat with existing users."), {
                    type: "warning",
                });
                return;
            }
            partnerId = user.partner_id;
        }
        let chat = Object.values(this.state.threads).find(
            (thread) => thread.type === "chat" && thread.chatPartnerId === partnerId
        );
        if (!chat || !chat.is_pinned) {
            chat = await this.joinChat(partnerId);
        }
        if (!chat) {
            this.notification.add(
                this.env._t("An unexpected error occurred during the creation of the chat."),
                { type: "warning" }
            );
            return;
        }
        return chat;
    }

    async joinChannel(id, name) {
        await this.orm.call("mail.channel", "add_members", [[id]], {
            partner_ids: [this.state.user.partnerId],
        });
        Thread.insert(this.state, {
            id,
            name,
            type: "channel",
            serverData: { channel: { avatarCacheKey: "hello" } },
        });
        this.sortChannels();
        this.state.discuss.threadId = id;
    }

    async joinChat(id) {
        const data = await this.orm.call("mail.channel", "channel_get", [], {
            partners_to: [id],
        });
        return Thread.insert(this.state, {
            id: data.id,
            name: undefined,
            type: "chat",
            serverData: data,
        });
    }

    async leaveChannel(id) {
        await this.orm.call("mail.channel", "action_unfollow", [id]);
        removeFromArray(this.state.discuss.channels.threads, id);
        this.setDiscussThread(this.state.discuss.channels.threads[0]);
    }

    async openChat(person) {
        const chat = await this.getChat(person);
        if (chat) {
            this.openDiscussion(chat.id);
        }
    }

    async toggleStar(messageId) {
        await this.orm.call("mail.message", "toggle_message_starred", [[messageId]]);
    }

    updateMessageStarredState(message, isStarred) {
        message.isStarred = isStarred;
        if (isStarred) {
            this.state.discuss.starred.counter++;
            this.state.discuss.starred.messages.push(message.id);
        } else {
            this.state.discuss.starred.counter--;
            removeFromArray(this.state.discuss.starred.messages, message.id);
        }
    }

    async deleteMessage(message) {
        if (message.isStarred) {
            this.state.discuss.starred.counter--;
            removeFromArray(this.state.discuss.starred.messages, message.id);
        }
        message.body = markup("");
        message.attachments = [];
        return this.rpc("/mail/message/update_content", {
            attachment_ids: [],
            body: "",
            message_id: message.id,
        });
    }

    isMessageBodyEmpty(message) {
        return (
            !message.body ||
            ["", "<p></p>", "<p><br></p>", "<p><br/></p>"].includes(message.body.replace(/\s/g, ""))
        );
    }

    isMessageEmpty(message) {
        return (
            this.isMessageBodyEmpty(message) &&
            message.attachments.length === 0 &&
            message.trackingValues.length === 0 &&
            !message.subtypeDescription
        );
    }

    async unstarAll() {
        // apply the change immediately for faster feedback
        this.state.discuss.starred.counter = 0;
        this.state.discuss.starred.messages = [];
        await this.orm.call("mail.message", "unstar_all");
    }

    async notifyThreadNameToServer(threadId, name) {
        const thread = this.state.threads[threadId];
        if (thread.type === "channel" || thread.type === "group") {
            thread.name = name;
            await this.orm.call("mail.channel", "channel_rename", [[thread.id]], { name });
        } else if (thread.type === "chat") {
            thread.name = name;
            await this.orm.call("mail.channel", "channel_set_custom_name", [[thread.id]], { name });
        }
    }

    async notifyThreadDescriptionToServer(threadId, description) {
        const thread = this.state.threads[threadId];
        thread.description = description;
        return this.orm.call("mail.channel", "channel_change_description", [[thread.id]], {
            description,
        });
    }

    // -------------------------------------------------------------------------
    // rtc (audio and video calls)
    // -------------------------------------------------------------------------

    startCall(threadId) {
        this.state.threads[threadId].inCall = true;
    }

    stopCall(threadId) {
        this.state.threads[threadId].inCall = false;
    }
}
