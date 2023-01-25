/** @odoo-module */

import { markup } from "@odoo/owl";
import { ChannelMember } from "../core/channel_member_model";
import { Thread } from "../core/thread_model";
import { _t } from "@web/core/l10n/translation";
import { removeFromArray, replaceArrayWithCompare } from "@mail/new/utils/arrays";
import { assignDefined, createLocalId } from "../utils/misc";
import { Composer } from "../composer/composer_model";
import { prettifyMessageContent } from "../utils/format";
import { registry } from "@web/core/registry";

const FETCH_MSG_LIMIT = 30;

export class ThreadService {
    nextId = 0;

    constructor(env, services) {
        this.env = env;
        /** @type {import("@mail/new/attachments/attachment_service")} */
        this.attachments = services["mail.attachment"];
        /** @type {import("@mail/new/core/store_service").Store} */
        this.store = services["mail.store"];
        this.orm = services.orm;
        this.rpc = services.rpc;
        /** @type {import("@mail/new/chat/chat_window_service").ChatWindowService} */
        this.chatWindow = services["mail.chat_window"];
        this.notification = services.notification;
        this.router = services.router;
        /** @type {import("@mail/new/core/persona_service").PersonaService} */
        this.persona = services["mail.persona"];
        /** @type {import("@mail/new/core/message_service").MessageService} */
        this.message = services["mail.message"];
        // FIXME this prevents cyclic dependencies between mail.thread and mail.message
        this.env.bus.addEventListener("MESSAGE-SERVICE:INSERT_THREAD", ({ detail }) => {
            const model = detail.model;
            const id = detail.id;
            this.insert({ model, id });
        });
    }

    /**
     * todo: merge this with this.insert() (?)
     *
     * @returns {Thread}
     */
    createChannelThread(serverData) {
        const {
            id,
            name,
            last_message_id,
            seen_message_id,
            description,
            channel,
            uuid,
            authorizedGroupFullName,
        } = serverData;
        const isUnread = last_message_id !== seen_message_id;
        const type = channel.channel_type;
        const channelType = serverData.channel.channel_type;
        const isAdmin =
            channelType !== "group" && serverData.create_uid === this.store.user.user?.id;
        const thread = this.insert({
            id,
            model: "mail.channel",
            name,
            type,
            isUnread,
            description,
            serverData: serverData,
            isAdmin,
            uuid,
            authorizedGroupFullName,
        });
        this.fetchChannelMembers(thread);
        return thread;
    }

    async fetchChannelMembers(thread) {
        const known_member_ids = thread.channelMembers.map((channelMember) => channelMember.id);
        const results = await this.rpc("/mail/channel/members", {
            channel_id: thread.id,
            known_member_ids: known_member_ids,
        });
        let channelMembers = [];
        if (
            results["channelMembers"] &&
            results["channelMembers"][0] &&
            results["channelMembers"][0][1]
        ) {
            channelMembers = results["channelMembers"][0][1];
        }
        thread.memberCount = results["memberCount"];
        for (const channelMember of channelMembers) {
            if (channelMember.persona?.partner) {
                this.insertChannelMember({
                    id: channelMember.id,
                    persona: this.persona.insert({
                        ...channelMember.persona.partner,
                        type: "partner",
                    }),
                    threadId: thread.id,
                });
            }
            if (channelMember.persona?.guest) {
                this.insertChannelMember({
                    id: channelMember.id,
                    persona: this.persona.insert({
                        ...channelMember.persona.guest,
                        type: "guest",
                        channelId: thread.id,
                    }),
                    threadId: thread.id,
                });
            }
        }
    }

    /**
     * @param {Thread} thread
     */
    async markAsRead(thread) {
        const mostRecentNonTransientMessage = thread.mostRecentNonTransientMessage;
        if (
            thread.isUnread &&
            ["chat", "channel"].includes(thread.type) &&
            mostRecentNonTransientMessage
        ) {
            await this.rpc("/mail/channel/set_last_seen_message", {
                channel_id: thread.id,
                last_message_id: mostRecentNonTransientMessage.id,
            });
        }
        this.update(thread, { isUnread: false });
    }

    /**
     * @param {Thread} thread
     */
    async markAsFetched(thread) {
        await this.orm.silent.call("mail.channel", "channel_fetched", [[thread.id]]);
    }

    /**
     * @param {Thread} thread
     * @param {{min: Number, max: Number}}
     */
    async fetchMessages(thread, { min, max }) {
        thread.status = "loading";
        if (thread.type === "chatter" && !thread.id) {
            return [];
        }
        const route = (() => {
            if (thread.model === "mail.channel") {
                return "/mail/channel/messages";
            }
            switch (thread.type) {
                case "chatter":
                    return "/mail/thread/messages";
                case "mailbox":
                    return `/mail/${thread.id}/messages`;
                default:
                    throw new Error(`Unknown thread type: ${thread.type}`);
            }
        })();
        const params = (() => {
            if (thread.model === "mail.channel") {
                return { channel_id: thread.id };
            }
            if (thread.type === "chatter") {
                return {
                    thread_id: thread.id,
                    thread_model: thread.model,
                };
            }
            return {};
        })();
        const rawMessages = await this.rpc(route, {
            ...params,
            limit: FETCH_MSG_LIMIT,
            max_id: max,
            min_id: min,
        });
        thread.status = "ready";
        const messages = rawMessages.reverse().map((data) => {
            if (data.parentMessage) {
                data.parentMessage.body = data.parentMessage.body
                    ? markup(data.parentMessage.body)
                    : data.parentMessage.body;
            }
            return this.message.insert(
                Object.assign(data, { body: data.body ? markup(data.body) : data.body }),
                true
            );
        });
        return messages;
    }

    async fetchNewMessages(thread) {
        const min = thread.mostRecentNonTransientMessage?.id;
        const fetchedMsgs = await this.fetchMessages(thread, { min });
        if (fetchedMsgs.length > 0) {
            this.markAsRead(thread);
        }
        Object.assign(thread, {
            isUnread: false,
            loadMore:
                min === undefined && fetchedMsgs.length === FETCH_MSG_LIMIT
                    ? true
                    : thread.loadMore,
        });
    }

    async fetchMoreMessages(thread) {
        const fetchedMsgs = await this.fetchMessages(thread, {
            max: thread.oldestNonTransientMessage?.id,
        });
        if (fetchedMsgs.length < FETCH_MSG_LIMIT) {
            thread.loadMore = false;
        }
    }

    async createChannel(name) {
        const data = await this.orm.call("mail.channel", "channel_create", [
            name,
            this.store.internalUserGroupId,
        ]);
        const channel = this.createChannelThread(data);
        this.sortChannels();
        this.open(channel);
    }

    sortChannels() {
        this.store.discuss.channels.threads.sort((id1, id2) => {
            const thread1 = this.store.threads[id1];
            const thread2 = this.store.threads[id2];
            return String.prototype.localeCompare.call(thread1.name, thread2.name);
        });
    }

    /**
     * @param {Thread} thread
     * @param {boolean} replaceNewMessageChatWindow
     */
    open(thread, replaceNewMessageChatWindow) {
        if (this.store.discuss.isActive && !this.store.isSmall) {
            this.setDiscussThread(thread);
        } else {
            const chatWindow = this.chatWindow.insert({
                folded: false,
                thread,
                replaceNewMessageChatWindow,
            });
            chatWindow.autofocus++;
            if (thread) {
                thread.state = "open";
            }
            this.chatWindow.notifyState(chatWindow);
        }
    }

    async openChat(person) {
        const chat = await this.getChat(person);
        if (chat) {
            this.open(chat);
        }
    }

    async getChat({ userId, partnerId }) {
        if (!partnerId) {
            let user = this.store.users[userId];
            if (!user) {
                this.store.users[userId] = { id: userId };
                user = this.store.users[userId];
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
                this.notification.add(_t("You can only chat with existing users."), {
                    type: "warning",
                });
                return;
            }
            partnerId = user.partner_id;
        }
        let chat = Object.values(this.store.threads).find(
            (thread) => thread.type === "chat" && thread.chatPartnerId === partnerId
        );
        if (!chat || !chat.is_pinned) {
            chat = await this.joinChat(partnerId);
        }
        if (!chat) {
            this.notification.add(
                _t("An unexpected error occurred during the creation of the chat."),
                { type: "warning" }
            );
            return;
        }
        return chat;
    }

    async joinChannel(id, name) {
        await this.orm.call("mail.channel", "add_members", [[id]], {
            partner_ids: [this.store.user.id],
        });
        const thread = this.insert({
            id,
            model: "mail.channel",
            name,
            type: "channel",
            serverData: { channel: { avatarCacheKey: "hello" } },
        });
        this.sortChannels();
        this.store.discuss.threadLocalId = thread.localId;
        return thread;
    }

    async joinChat(id) {
        const data = await this.orm.call("mail.channel", "channel_get", [], {
            partners_to: [id],
        });
        return this.insert({
            id: data.id,
            model: "mail.channel",
            name: undefined,
            type: "chat",
            serverData: data,
        });
    }

    executeCommand(thread, command, body = "") {
        return this.orm.call("mail.channel", command.methodName, [[thread.id]], {
            body,
        });
    }

    async notifyThreadNameToServer(thread, name) {
        if (thread.type === "channel" || thread.type === "group") {
            thread.name = name;
            await this.orm.call("mail.channel", "channel_rename", [[thread.id]], { name });
        } else if (thread.type === "chat") {
            thread.customName = name;
            await this.orm.call("mail.channel", "channel_set_custom_name", [[thread.id]], { name });
        }
    }

    async notifyThreadDescriptionToServer(thread, description) {
        thread.description = description;
        return this.orm.call("mail.channel", "channel_change_description", [[thread.id]], {
            description,
        });
    }

    async leaveChannel(channel) {
        await this.orm.call("mail.channel", "action_unfollow", [channel.id]);
        this.remove(channel);
        this.setDiscussThread(
            this.store.discuss.channels.threads[0]
                ? this.store.threads[this.store.discuss.channels.threads[0]]
                : this.store.discuss.inbox
        );
    }

    setDiscussThread(thread) {
        this.store.discuss.threadLocalId = thread.localId;
        const activeId =
            typeof thread.id === "string" ? `mail.box_${thread.id}` : `mail.channel_${thread.id}`;
        this.router.pushState({ active_id: activeId });
    }

    async createGroupChat({ default_display_mode, partners_to }) {
        const data = await this.orm.call("mail.channel", "create_group", [], {
            default_display_mode,
            partners_to,
        });
        const channel = this.createChannelThread(data);
        this.sortChannels();
        this.open(channel);
    }

    remove(thread) {
        removeFromArray(this.store.discuss.chats.threads, thread.localId);
        removeFromArray(this.store.discuss.channels.threads, thread.localId);
        delete this.store.threads[thread.localId];
    }

    /**
     * @param {import("@mail/new/core/thread_model").Thread} thread
     * @param {Object} data
     */
    update(thread, data) {
        const { attachments, ...remainingData } = data;
        for (const key in remainingData) {
            thread[key] = data[key];
        }
        if (attachments) {
            // smart process to avoid triggering reactives when there is no change between the 2 arrays
            replaceArrayWithCompare(
                thread.attachments,
                attachments.map((attachment) => this.attachments.insert(attachment)),
                (a1, a2) => a1.id === a2.id
            );
        }
        if (data.serverData) {
            const { serverData } = data;
            assignDefined(thread, serverData, [
                "uuid",
                "authorizedGroupFullName",
                "hasWriteAccess",
                "is_pinned",
                "message_needaction_counter",
                "state",
            ]);

            if (serverData.channel && "serverMessageUnreadCounter" in serverData.channel) {
                thread.serverMessageUnreadCounter = serverData.channel.serverMessageUnreadCounter;
            }
            if ("seen_message_id" in serverData) {
                thread.serverLastSeenMsgBySelf = serverData.seen_message_id;
            }
            if ("defaultDisplayMode" in serverData) {
                thread.defaultDisplayMode = serverData.defaultDisplayMode;
            }
            if (thread.type === "chat") {
                for (const elem of serverData.channel.channelMembers[0][1]) {
                    this.persona.insert({ ...elem.persona.partner, type: "partner" });
                    if (
                        elem.persona.partner.id !== thread._store.user.id ||
                        (serverData.channel.channelMembers[0][1].length === 1 &&
                            elem.persona.partner.id === thread._store.user.id)
                    ) {
                        thread.chatPartnerId = elem.persona.partner.id;
                    }
                }
                thread.customName = serverData.channel.custom_channel_name;
            }
            if (
                thread.type === "group" &&
                serverData.channel &&
                serverData.channel.channelMembers
            ) {
                serverData.channel.channelMembers[0][1].forEach((elem) => {
                    if (elem.persona?.partner) {
                        this.persona.insert({ ...elem.persona.partner, type: "partner" });
                    }
                    if (elem.persona?.guest) {
                        this.persona.insert({
                            ...elem.persona.guest,
                            type: "guest",
                            channelId: serverData.channel.id,
                        });
                    }
                });
            }
            if ("rtcSessions" in serverData) {
                // FIXME this prevents cyclic dependencies between mail.thread and mail.rtc
                this.env.bus.trigger("THREAD-SERVICE:UPDATE_RTC_SESSIONS", {
                    thread,
                    data: serverData.rtcSessions[0],
                });
            }
            if ("invitedPartners" in serverData) {
                thread.invitedPartners =
                    serverData.invitedPartners &&
                    serverData.invitedPartners.map((partner) =>
                        this.persona.insert({ ...partner, type: "partner" })
                    );
            }
            if ("seen_partners_info" in serverData) {
                thread.seenInfos = serverData.seen_partners_info.map(
                    ({ fetched_message_id, partner_id, seen_message_id }) => {
                        return {
                            lastFetchedMessage: fetched_message_id
                                ? this.message.insert({ id: fetched_message_id })
                                : undefined,
                            lastSeenMessage: seen_message_id
                                ? this.message.insert({ id: seen_message_id })
                                : undefined,
                            partner: this.persona.insert({ id: partner_id, type: "partner" }),
                        };
                    }
                );
            }
            thread.canLeave =
                ["channel", "group"].includes(thread.type) &&
                !thread.message_needaction_counter &&
                !thread.serverData.group_based_subscription;
        }
        this.insertComposer({ thread });
    }

    /**
     * @param {Object} data
     * @returns {Thread}
     */
    insert(data) {
        if (!("id" in data)) {
            throw new Error("Cannot insert thread: id is missing in data");
        }
        if (!("model" in data)) {
            throw new Error("Cannot insert thread: model is missing in data");
        }
        const localId = createLocalId(data.model, data.id);
        if (localId in this.store.threads) {
            const thread = this.store.threads[localId];
            this.update(thread, data);
            return thread;
        }
        let thread = new Thread(this.store, data);
        thread = this.store.threads[thread.localId] = thread;
        this.update(thread, data);
        return thread;
    }

    /**
     * @param {Object} data
     * @returns {Composer}
     */
    insertComposer(data) {
        const { message, thread } = data;
        if (Boolean(message) === Boolean(thread)) {
            throw new Error("Composer shall have a thread xor a message.");
        }
        let composer = (thread ?? message)?.composer;
        if (!composer) {
            composer = new Composer(this.store, data);
        }
        if ("textInputContent" in data) {
            composer.textInputContent = data.textInputContent;
        }
        if ("selection" in data) {
            Object.assign(composer.selection, data.selection);
        }
        return composer;
    }

    insertChannelMember(data) {
        let channelMember = this.store.channelMembers[data.id];
        if (!channelMember) {
            this.store.channelMembers[data.id] = new ChannelMember();
            channelMember = this.store.channelMembers[data.id];
            channelMember._store = this.store;
        }
        Object.assign(channelMember, {
            id: data.id,
            persona: data.persona,
            threadId: data.threadId ?? channelMember.threadId ?? data?.channel.id,
        });
        if (channelMember.thread && !channelMember.thread.channelMembers.includes(channelMember)) {
            channelMember.thread.channelMembers.push(channelMember);
        }
        return channelMember;
    }

    /**
     * @param {Thread} thread
     * @param {string} body
     */
    async post(thread, body, { attachments = [], isNote = false, parentId, rawMentions }) {
        const command = this.store.user
            ? this.message.getCommandFromText(thread.type, body)
            : undefined;
        if (command) {
            await this.executeCommand(thread, command, body);
            return;
        }
        let tmpMsg;
        const subtype = isNote ? "mail.mt_note" : "mail.mt_comment";
        const validMentions = this.store.user
            ? this.message.getMentionsFromText(rawMentions, body)
            : undefined;
        const partner_ids = validMentions.partners.map((partner) => partner.id);
        if (!isNote) {
            const recipientIds = thread.suggestedRecipients
                .filter((recipient) => recipient.persona && recipient.checked)
                .map((recipient) => recipient.persona.id);
            partner_ids.push(...recipientIds);
        }
        const params = {
            post_data: {
                body: await prettifyMessageContent(body, validMentions),
                attachment_ids: attachments.map(({ id }) => id),
                message_type: "comment",
                partner_ids,
                subtype_xmlid: subtype,
            },
            thread_id: thread.id,
            thread_model: thread.model,
        };
        if (parentId) {
            params.post_data.parent_id = parentId;
        }
        if (thread.type === "chatter") {
            params.thread_id = thread.id;
            params.thread_model = thread.model;
        } else {
            const lastMessageId = this.message.getLastMessageId();
            const tmpId = lastMessageId + 0.01;
            const tmpData = {
                id: tmpId,
                author: { id: this.store.self.id },
                attachments: attachments,
                res_id: thread.id,
                model: "mail.channel",
            };
            if (parentId) {
                tmpData.parentMessage = this.store.messages[parentId];
            }
            tmpMsg = this.message.insert({
                ...tmpData,
                body: markup(await prettifyMessageContent(body, validMentions)),
                res_id: thread.id,
                model: thread.model,
            });
        }
        const data = await this.rpc("/mail/message/post", params);
        if (data.parentMessage) {
            data.parentMessage.body = data.parentMessage.body
                ? markup(data.parentMessage.body)
                : data.parentMessage.body;
        }
        const message = this.message.insert(Object.assign(data, { body: markup(data.body) }));
        if (!message.isEmpty) {
            this.rpc("/mail/link_preview", { message_id: data.id }, { silent: true });
        }
        if (thread.type !== "chatter") {
            removeFromArray(thread.messageIds, tmpMsg.id);
            delete this.store.messages[tmpMsg.id];
        }
        return message;
    }

    /**
     * @param {Thread} thread
     */
    localMessageUnreadCounter(thread) {
        let baseCounter = thread.serverMessageUnreadCounter;
        let countFromId = thread.serverLastSeenMsgBySelf ? thread.serverLastSeenMsgBySelf : 0;
        this.message.sortMessages(thread);
        const lastSeenMessageId = this.lastSeenBySelfMessageId(thread);
        const firstMessage = thread.messages[0];
        if (firstMessage && lastSeenMessageId && lastSeenMessageId >= firstMessage.id) {
            baseCounter = 0;
            countFromId = lastSeenMessageId;
        }
        return thread.messages.reduce((total, message) => {
            if (message.id <= countFromId) {
                return total;
            }
            return total + 1;
        }, baseCounter);
    }

    /**
     * @param {Thread} thread
     */
    lastSeenBySelfMessageId(thread) {
        const firstMessage = thread.messages[0];
        if (firstMessage && thread.serverLastSeenMsgBySelf < firstMessage.id) {
            return thread.serverLastSeenMsgBySelf;
        }
        let lastSeenMessageId = thread.serverLastSeenMsgBySelf;
        for (const message of thread.messages) {
            if (message.id <= thread.serverLastSeenMsgBySelf) {
                continue;
            }
            if (message.isSelfAuthored || message.isTransient) {
                lastSeenMessageId = message.id;
                continue;
            }
            return lastSeenMessageId;
        }
        return lastSeenMessageId;
    }

    getDiscussCategoryCounter(categoryId) {
        return this.store.discuss[categoryId].threads.reduce((acc, threadLocalId) => {
            const channel = this.store.threads[threadLocalId];
            if (categoryId === "channels") {
                return channel.message_needaction_counter > 0 ? acc + 1 : acc;
            } else {
                return this.localMessageUnreadCounter(channel) > 0 ? acc + 1 : acc;
            }
        }, 0);
    }

    /**
     * @param {import("@mail/new/core/thread_model").Thread} thread
     * @param {number} index
     */
    async setMainAttachmentFromIndex(thread, index) {
        thread.mainAttachment = thread.attachmentsInWebClientView[index];
        await this.orm.call("ir.attachment", "register_as_main_attachment", [
            thread.mainAttachment.id,
        ]);
    }

    /**
     * @param {import("@mail/new/composer/composer_model").Composer} composer
     */
    clearComposer(composer) {
        composer.textInputContent = "";
        composer.selection = {
            start: 0,
            end: 0,
            direction: "none",
        };
    }
}

export const threadService = {
    dependencies: [
        "mail.attachment",
        "mail.store",
        "orm",
        "rpc",
        "mail.chat_window",
        "notification",
        "router",
        "mail.persona",
        "mail.message",
    ],
    start(env, services) {
        return new ThreadService(env, services);
    },
};

registry.category("services").add("mail.thread", threadService);
