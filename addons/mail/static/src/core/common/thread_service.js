/* @odoo-module */

import { Composer } from "@mail/core/common/composer_model";
import { loadEmoji } from "@mail/core/common/emoji_picker";
import { DEFAULT_AVATAR } from "@mail/core/common/persona_service";
import { Thread } from "@mail/core/common/thread_model";
import {
    removeFromArray,
    removeFromArrayWithPredicate,
    replaceArrayWithCompare,
} from "@mail/utils/common/arrays";
import { prettifyMessageContent } from "@mail/utils/common/format";
import { assignDefined, createLocalId, onChange, nullifyClearCommands } from "@mail/utils/common/misc";

import { markup } from "@odoo/owl";

import { browser } from "@web/core/browser/browser";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { memoize } from "@web/core/utils/functions";
import { url } from "@web/core/utils/urls";

const FETCH_LIMIT = 30;

export class ThreadService {
    nextId = 0;

    constructor(env, services) {
        this.setup(env, services);
    }

    setup(env, services) {
        this.env = env;
        /** @type {import("@mail/core/common/channel_member_service").ChannelMemberService} */
        this.channelMemberService = services["discuss.channel.member"];
        /** @type {import("@mail/core/common/attachment_service").AttachmentService} */
        this.attachmentsService = services["mail.attachment"];
        /** @type {import("@mail/core/common/store_service").Store} */
        this.store = services["mail.store"];
        this.orm = services.orm;
        this.rpc = services.rpc;
        this.notificationService = services.notification;
        this.router = services.router;
        this.ui = services.ui;
        /** @type {import("@mail/core/common/persona_service").PersonaService} */
        this.personaService = services["mail.persona"];
        /** @type {import("@mail/core/common/message_service").MessageService} */
        this.messageService = services["mail.message"];
        // this prevents cyclic dependencies between mail.thread and other services
        this.env.bus.addEventListener("mail.thread/insert", ({ detail }) => {
            const model = detail.model;
            const id = detail.id;
            const type = detail.type;
            this.insert({ model, id, type });
        });
    }

    /**
     * todo: merge this with this.insert() (?)
     *
     * @returns {Thread}
     */
    createChannelThread(serverData) {
        const thread = this.insert({
            ...serverData,
            model: "discuss.channel",
            type: serverData.channel.channel_type,
            isAdmin:
                serverData.channel.channel_type !== "group" &&
                serverData.create_uid === this.store.user?.user?.id,
        });
        return thread;
    }

    async fetchChannelMembers(thread) {
        const known_member_ids = thread.channelMembers.map((channelMember) => channelMember.id);
        const results = await this.rpc("/discuss/channel/members", {
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
            if (channelMember.persona || channelMember.partner) {
                this.channelMemberService.insert({ ...channelMember, threadId: thread.id });
            }
        }
    }

    /**
     * @param {Thread} thread
     */
    async markAsRead(thread) {
        if (!thread.isLoaded && thread.status === "loading") {
            await thread.isLoadedDeferred;
            await new Promise(setTimeout);
        }
        const newestPersistentMessage = thread.newestPersistentMessage;
        thread.seen_message_id = newestPersistentMessage?.id ?? false;
        if (
            thread.message_unread_counter > 0 &&
            thread.allowSetLastSeenMessage &&
            newestPersistentMessage
        ) {
            this.rpc("/discuss/channel/set_last_seen_message", {
                channel_id: thread.id,
                last_message_id: newestPersistentMessage.id,
            }).then(() => {
                this.updateSeen(thread, newestPersistentMessage.id);
            });
        } else if (newestPersistentMessage) {
            this.updateSeen(thread);
        }
        if (thread.hasNeedactionMessages) {
            this.markAllMessagesAsRead(thread);
        }
    }

    updateSeen(thread, lastSeenId = thread.newestPersistentMessage?.id) {
        const lastReadIndex = thread.messages.findIndex((message) => message.id === lastSeenId);
        let newNeedactionCounter = 0;
        let newUnreadCounter = 0;
        for (const message of thread.messages.slice(lastReadIndex + 1)) {
            if (message.isNeedaction) {
                newNeedactionCounter++;
            }
            if (Number.isInteger(message.id)) {
                newUnreadCounter++;
            }
        }
        this.update(thread, {
            seen_message_id: lastSeenId,
            message_needaction_counter: newNeedactionCounter,
            message_unread_counter: newUnreadCounter,
        });
    }

    async markAllMessagesAsRead(thread) {
        await this.orm.silent.call("mail.message", "mark_all_as_read", [
            [
                ["model", "=", thread.model],
                ["res_id", "=", thread.id],
            ],
        ]);
        Object.assign(thread, {
            needactionMessages: [],
            message_unread_counter: 0,
            message_needaction_counter: 0,
            seen_message_id: thread.newestPersistentMessage?.id,
        });
    }

    /**
     * @param {Thread} thread
     */
    async markAsFetched(thread) {
        await this.orm.silent.call("discuss.channel", "channel_fetched", [[thread.id]]);
    }

    getFetchRoute(thread) {
        if (thread.model === "discuss.channel") {
            return "/discuss/channel/messages";
        }
        switch (thread.type) {
            case "chatter":
                return "/mail/thread/messages";
            case "mailbox":
                return `/mail/${thread.id}/messages`;
            default:
                throw new Error(`Unknown thread type: ${thread.type}`);
        }
    }

    getFetchParams(thread) {
        if (thread.model === "discuss.channel") {
            return { channel_id: thread.id };
        }
        if (thread.type === "chatter") {
            return {
                thread_id: thread.id,
                thread_model: thread.model,
            };
        }
        return {};
    }

    /**
     * @param {Thread} thread
     * @param {{after: Number, before: Number}}
     */
    async fetchMessages(thread, { after, before } = {}) {
        thread.status = "loading";
        if (thread.type === "chatter" && !thread.id) {
            return [];
        }
        try {
            // ordered messages received: newest to oldest
            const rawMessages = await this.rpc(this.getFetchRoute(thread), {
                ...this.getFetchParams(thread),
                limit: FETCH_LIMIT,
                after,
                before,
            });
            const messages = rawMessages.reverse().map((data) => {
                if (data.parentMessage) {
                    data.parentMessage.body = data.parentMessage.body
                        ? markup(data.parentMessage.body)
                        : data.parentMessage.body;
                }
                return this.messageService.insert(
                    Object.assign(data, { body: data.body ? markup(data.body) : data.body })
                );
            });
            this.update(thread, { isLoaded: true });
            return messages;
        } catch (e) {
            thread.hasLoadingFailed = true;
            throw e;
        } finally {
            thread.status = "ready";
        }
    }

    /**
     * @param {Thread} thread
     */
    async fetchNewMessages(thread) {
        if (
            thread.status === "loading" ||
            (thread.isLoaded && ["discuss.channel", "mail.box"].includes(thread.model))
        ) {
            return;
        }
        const after = thread.isLoaded ? thread.newestPersistentMessage?.id : undefined;
        try {
            const fetched = await this.fetchMessages(thread, { after });
            // feed messages
            // could have received a new message as notification during fetch
            // filter out already fetched (e.g. received as notification in the meantime)
            let startIndex;
            if (after === undefined) {
                startIndex = 0;
            } else {
                const afterIndex = thread.messages.findIndex((message) => message.id === after);
                if (afterIndex === -1) {
                    // there might have been a jump to message during RPC fetch.
                    // Abort feeding messages as to not put holes in message list.
                    return;
                } else {
                    startIndex = afterIndex + 1;
                }
            }
            const alreadyKnownMessages = new Set(thread.messages.map((m) => m.id));
            const filtered = fetched.filter(
                (message) =>
                    !alreadyKnownMessages.has(message.id) &&
                    (thread.persistentMessages.length === 0 ||
                        message.id < thread.oldestPersistentMessage.id ||
                        message.id > thread.newestPersistentMessage.id)
            );
            thread.messages.splice(startIndex, 0, ...filtered);
            // feed needactions
            // same for needaction messages, special case for mailbox:
            // kinda "fetch new/more" with needactions on many origin threads at once
            if (thread === this.store.discuss.inbox) {
                for (const message of fetched) {
                    const thread = message.originThread;
                    if (!thread.needactionMessages.includes(message)) {
                        thread.needactionMessages.unshift(message);
                    }
                }
            } else {
                const startNeedactionIndex =
                    after === undefined
                        ? 0
                        : thread.messages.findIndex((message) => message.id === after);
                const filteredNeedaction = fetched.filter(
                    (message) =>
                        message.isNeedaction &&
                        (thread.needactionMessages.length === 0 ||
                            message.id < thread.oldestNeedactionMessage.id ||
                            message.id > thread.newestNeedactionMessage.id)
                );
                thread.needactionMessages.splice(startNeedactionIndex, 0, ...filteredNeedaction);
            }
            Object.assign(thread, {
                loadOlder:
                    after === undefined && fetched.length === FETCH_LIMIT
                        ? true
                        : after === undefined && fetched.length !== FETCH_LIMIT
                        ? false
                        : thread.loadOlder,
            });
        } catch {
            // handled in fetchMessages
        }
    }

    /**
     * Get ready to jump to a message in a thread. This method will fetch the
     * messages around the message to jump to if required, and update the thread
     * messages accordingly.
     *
     * @param {Message} [messageId] if not provided, load around newest message
     */
    async loadAround(thread, messageId) {
        if (!thread.messages.some(({ id }) => id === messageId)) {
            const messages = await this.rpc(this.getFetchRoute(thread), {
                ...this.getFetchParams(thread),
                around: messageId,
            });
            thread.messages = messages.reverse().map((message) => {
                if (message.parentMessage?.body) {
                    message.parentMessage.body = markup(message.parentMessage.body);
                }
                return this.messageService.insert({
                    ...message,
                    body: message.body ? markup(message.body) : message.body,
                });
            });
            thread.loadNewer = messageId ? true : false;
            thread.loadOlder = true;
            if (messages.length < FETCH_LIMIT) {
                const olderMessagesCount = messages.filter(({ id }) => id < messageId).length;
                if (olderMessagesCount < FETCH_LIMIT / 2) {
                    thread.loadOlder = false;
                } else {
                    thread.loadNewer = false;
                }
            }
            this._enrichMessagesWithTransient(thread);
            // Give some time to the UI to update.
            await new Promise((resolve) => setTimeout(() => requestAnimationFrame(resolve)));
        }
    }

    // This function is like fetchNewMessages but just for a single message at most on all pinned threads
    fetchPreviews = memoize(async () => {
        const ids = [];
        for (const thread of Object.values(this.store.threads)) {
            if (["channel", "group", "chat"].includes(thread.type)) {
                ids.push(thread.id);
            }
        }
        if (ids.length) {
            const previews = await this.orm.call("discuss.channel", "channel_fetch_preview", [ids]);
            for (const preview of previews) {
                const thread = this.store.threads[createLocalId("discuss.channel", preview.id)];
                const data = Object.assign(preview.last_message, {
                    body: markup(preview.last_message.body),
                });
                const message = this.messageService.insert({
                    ...data,
                    res_id: thread.id,
                    model: thread.model,
                });
                if (!thread.isLoaded) {
                    thread.messages.push(message);
                    if (message.isNeedaction && !thread.needactionMessages.includes(message)) {
                        thread.needactionMessages.push(message);
                    }
                }
                thread.isLoaded = true;
                thread.loadOlder = true;
                thread.status = "ready";
            }
        }
    });

    /**
     * @param {Thread} thread
     * @param {"older"|"newer"} epoch
     */
    async fetchMoreMessages(thread, epoch = "older") {
        if (
            thread.status === "loading" ||
            (epoch === "older" && !thread.loadOlder) ||
            (epoch === "newer" && !thread.loadNewer)
        ) {
            return;
        }
        const before = epoch === "older" ? thread.oldestPersistentMessage?.id : undefined;
        const after = epoch === "newer" ? thread.newestPersistentMessage?.id : undefined;
        try {
            const fetched = await this.fetchMessages(thread, { after, before });
            if (
                (after !== undefined && !thread.messages.some((message) => message.id === after)) ||
                (before !== undefined && !thread.messages.some((message) => message.id === before))
            ) {
                // there might have been a jump to message during RPC fetch.
                // Abort feeding messages as to not put holes in message list.
                return;
            }
            const alreadyKnownMessages = new Set(thread.messages.map(({ id }) => id));
            const messagesToAdd = fetched.filter(
                (message) => !alreadyKnownMessages.has(message.id)
            );
            if (epoch === "older") {
                thread.messages.unshift(...messagesToAdd);
            } else {
                thread.messages.push(...messagesToAdd);
            }
            if (fetched.length < FETCH_LIMIT) {
                if (epoch === "older") {
                    thread.loadOlder = false;
                } else if (epoch === "newer") {
                    thread.loadNewer = false;
                    const missingMessages = thread.pendingNewMessages.filter(
                        ({ id }) => !alreadyKnownMessages.has(id)
                    );
                    if (missingMessages.length > 0) {
                        thread.messages.push(...missingMessages);
                        thread.messages.sort((m1, m2) => m1.id - m2.id);
                    }
                }
            }
            this._enrichMessagesWithTransient(thread);
        } catch {
            // handled in fetchMessages
        }
        thread.pendingNewMessages = [];
    }

    async createChannel(name) {
        const data = await this.orm.call("discuss.channel", "channel_create", [
            name,
            this.store.internalUserGroupId,
        ]);
        const channel = this.createChannelThread(data);
        this.sortChannels();
        this.open(channel);
    }

    unpin(thread) {
        if (thread.model !== "discuss.channel") {
            return;
        }
        return this.orm.silent.call("discuss.channel", "channel_pin", [thread.id], {
            pinned: false,
        });
    }

    pin(thread) {
        if (thread.model !== "discuss.channel" || !this.store.user) {
            return;
        }
        thread.is_pinned = true;
        return this.orm.silent.call("discuss.channel", "channel_pin", [thread.id], {
            pinned: true,
        });
    }

    sortChannels() {
        this.store.discuss.channels.threads.sort((id1, id2) => {
            const thread1 = this.store.threads[id1];
            const thread2 = this.store.threads[id2];
            return String.prototype.localeCompare.call(thread1.name, thread2.name);
        });
        this.store.discuss.chats.threads.sort((localId_1, localId_2) => {
            const thread1 = this.store.threads[localId_1];
            const thread2 = this.store.threads[localId_2];
            return thread2.lastInterestDateTime.ts - thread1.lastInterestDateTime.ts;
        });
    }

    /**
     * @param {Thread} thread
     * @param {boolean} replaceNewMessageChatWindow
     */
    open(thread, replaceNewMessageChatWindow) {
        this.setDiscussThread(thread);
    }

    async openChat(person) {
        const chat = await this.getChat(person);
        if (chat) {
            this.open(chat);
        }
    }

    async getChat({ userId, partnerId }) {
        if (userId) {
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
                this.notificationService.add(_t("You can only chat with existing users."), {
                    type: "warning",
                });
                return;
            }
            partnerId = user.partner_id;
        }

        if (partnerId) {
            const partner = this.personaService.insert({ id: partnerId, type: "partner" });
            if (!partner.user) {
                const [userId] = await this.orm.silent.search(
                    "res.users",
                    [["partner_id", "=", partnerId]],
                    { context: { active_test: false } }
                );
                if (!userId) {
                    this.notificationService.add(
                        _t("You can only chat with partners that have a dedicated user."),
                        { type: "info" }
                    );
                    return;
                }
                partner.user = { id: userId };
            }
        }

        let chat = Object.values(this.store.threads).find(
            (thread) => thread.type === "chat" && thread.chatPartnerId === partnerId
        );
        if (!chat || !chat.is_pinned) {
            chat = await this.joinChat(partnerId);
        }
        if (!chat) {
            this.notificationService.add(
                _t("An unexpected error occurred during the creation of the chat."),
                { type: "warning" }
            );
            return;
        }
        return chat;
    }

    async joinChannel(id, name) {
        await this.orm.call("discuss.channel", "add_members", [[id]], {
            partner_ids: [this.store.user.id],
        });
        const thread = this.insert({
            id,
            model: "discuss.channel",
            name,
            type: "channel",
            channel: { avatarCacheKey: "hello" },
        });
        this.sortChannels();
        this.open(thread);
        return thread;
    }

    async joinChat(id) {
        const data = await this.orm.call("discuss.channel", "channel_get", [], {
            partners_to: [id],
        });
        return this.insert({
            ...data,
            model: "discuss.channel",
            type: "chat",
        });
    }

    executeCommand(thread, command, body = "") {
        return this.orm.call("discuss.channel", command.methodName, [[thread.id]], {
            body,
        });
    }

    async notifyThreadNameToServer(thread, name) {
        if (thread.type === "channel" || thread.type === "group") {
            thread.name = name;
            await this.orm.call("discuss.channel", "channel_rename", [[thread.id]], { name });
        } else if (thread.type === "chat") {
            thread.customName = name;
            await this.orm.call("discuss.channel", "channel_set_custom_name", [[thread.id]], {
                name,
            });
        }
    }

    async notifyThreadDescriptionToServer(thread, description) {
        thread.description = description;
        return this.orm.call("discuss.channel", "channel_change_description", [[thread.id]], {
            description,
        });
    }

    async leaveChannel(channel) {
        await this.orm.call("discuss.channel", "action_unfollow", [channel.id]);
        this.remove(channel);
        this.setDiscussThread(
            this.store.discuss.channels.threads[0]
                ? this.store.threads[this.store.discuss.channels.threads[0]]
                : this.store.discuss.inbox
        );
    }

    /**
     * @param {import("@mail/core/common/thread_model").Thread} thread
     * @param {boolean} pushState
     */
    setDiscussThread(thread, pushState = true) {
        this.store.discuss.threadLocalId = thread.localId;
        const activeId =
            typeof thread.id === "string"
                ? `mail.box_${thread.id}`
                : `discuss.channel_${thread.id}`;
        this.store.discuss.activeTab = !this.ui.isSmall
            ? "all"
            : thread.model === "mail.box"
            ? "mailbox"
            : ["chat", "group"].includes(thread.type)
            ? "chat"
            : "channel";
        if (pushState) {
            this.router.pushState({ active_id: activeId });
        }
    }

    async createGroupChat({ default_display_mode, partners_to }) {
        const data = await this.orm.call("discuss.channel", "create_group", [], {
            default_display_mode,
            partners_to,
        });
        const channel = this.createChannelThread(data);
        this.sortChannels();
        this.open(channel);
        return channel;
    }

    remove(thread) {
        removeFromArray(this.store.discuss.chats.threads, thread.localId);
        removeFromArray(this.store.discuss.channels.threads, thread.localId);
        delete this.store.threads[thread.localId];
    }

    /**
     * @param {import("@mail/core/common/thread_model").Thread} thread
     * @param {Object} data
     */
    update(thread, data) {
        const { id, name, attachments: attachmentsData, description, ...serverData } = data;
        assignDefined(thread, { id, name, description });
        if (attachmentsData) {
            replaceArrayWithCompare(
                thread.attachments,
                attachmentsData.map((attachmentData) =>
                    this.attachmentsService.insert(attachmentData)
                )
            );
        }
        if (serverData) {
            assignDefined(thread, serverData, [
                "uuid",
                "authorizedGroupFullName",
                "description",
                "hasWriteAccess",
                "is_pinned",
                "isLoaded",
                "isLoadingAttachments",
                "mainAttachment",
                "message_unread_counter",
                "message_needaction_counter",
                "name",
                "seen_message_id",
                "state",
                "type",
                "status",
                "group_based_subscription",
                "last_interest_dt",
                "is_editable",
                "defaultDisplayMode",
            ]);
            if (serverData.channel && "message_unread_counter" in serverData.channel) {
                thread.message_unread_counter = serverData.channel.message_unread_counter;
            }
            thread.lastServerMessageId = serverData.last_message_id ?? thread.lastServerMessageId;
            if (thread.model === "discuss.channel" && serverData.channel) {
                nullifyClearCommands(serverData.channel);
                thread.channel = assignDefined(thread.channel ?? {}, serverData.channel);
            }

            thread.memberCount = serverData.channel?.memberCount ?? thread.memberCount;
            if (thread.type === "chat" && serverData.channel) {
                thread.customName = serverData.channel.custom_channel_name;
            }
            if (serverData.channel?.channelMembers) {
                for (const [command, membersData] of serverData.channel.channelMembers) {
                    const members = Array.isArray(membersData) ? membersData : [membersData];
                    for (const memberData of members) {
                        const member = this.channelMemberService.insert([command, memberData]);
                        if (thread.type !== "chat") {
                            continue;
                        }
                        if (
                            member.persona.id !== thread._store.user?.id ||
                            (serverData.channel.channelMembers[0][1].length === 1 &&
                                member.persona.id === thread._store.user?.id)
                        ) {
                            thread.chatPartnerId = member.persona.id;
                        }
                    }
                }
            }
            if ("invitedMembers" in serverData) {
                if (!serverData.invitedMembers) {
                    thread.invitedMemberIds.clear();
                    return;
                }
                const command = serverData.invitedMembers[0][0];
                const members = serverData.invitedMembers[0][1];
                switch (command) {
                    case "insert":
                        if (members) {
                            for (const member of members) {
                                const record = this.channelMemberService.insert(member);
                                thread.invitedMemberIds.add(record.id);
                            }
                        }
                        break;
                    case "unlink":
                    case "insert-and-unlink":
                        // eslint-disable-next-line no-case-declarations
                        for (const member of members) {
                            thread.invitedMemberIds.delete(member.id);
                        }
                        break;
                }
            }
            if ("seen_partners_info" in serverData) {
                thread.seenInfos = serverData.seen_partners_info.map(
                    ({ fetched_message_id, partner_id, seen_message_id }) => {
                        return {
                            lastFetchedMessage: fetched_message_id
                                ? this.messageService.insert({ id: fetched_message_id })
                                : undefined,
                            lastSeenMessage: seen_message_id
                                ? this.messageService.insert({ id: seen_message_id })
                                : undefined,
                            partner: this.personaService.insert({
                                id: partner_id,
                                type: "partner",
                            }),
                        };
                    }
                );
            }
        }
        if (
            thread.type === "channel" &&
            !this.store.discuss.channels.threads.includes(thread.localId)
        ) {
            this.store.discuss.channels.threads.push(thread.localId);
        } else if (
            (thread.type === "chat" || thread.type === "group") &&
            !this.store.discuss.chats.threads.includes(thread.localId)
        ) {
            this.store.discuss.chats.threads.push(thread.localId);
        }
        if (!thread.type && !["mail.box", "discuss.channel"].includes(thread.model)) {
            thread.type = "chatter";
        }
        this.env.bus.trigger("mail.thread/onUpdate", { thread, data });
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
        const thread = new Thread(this.store, data);
        onChange(thread, "message_unread_counter", () => {
            if (thread.channel) {
                thread.channel.message_unread_counter = thread.message_unread_counter;
            }
        });
        onChange(thread, "isLoaded", () => thread.isLoadedDeferred.resolve());
        onChange(thread, "channelMembers", () => this.store.updateBusSubscription());
        onChange(thread, "is_pinned", () => {
            if (!thread.is_pinned && this.store.discuss.threadLocalId === thread.localId) {
                this.store.discuss.threadLocalId = null;
            }
        });
        this.update(thread, data);
        this.insertComposer({ thread });
        // return reactive version.
        return this.store.threads[thread.localId];
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
        if ("mentions" in data) {
            for (const mention of data.mentions) {
                if (mention.type === "partner") {
                    composer.rawMentions.partnerIds.add(mention.id);
                }
            }
        }
        return composer;
    }

    /**
     * @param {Thread} thread
     * @param {string} body
     */
    async post(
        thread,
        body,
        { attachments = [], isNote = false, parentId, rawMentions, cannedResponseIds }
    ) {
        let tmpMsg;
        const params = await this.getMessagePostParams({
            attachments,
            body,
            cannedResponseIds,
            isNote,
            rawMentions,
            thread,
        });
        const tmpId = this.messageService.getNextTemporaryId();
        params.context = { ...params.context, temporary_id: tmpId };
        if (parentId) {
            params.post_data.parent_id = parentId;
        }
        if (thread.type === "chatter") {
            params.thread_id = thread.id;
            params.thread_model = thread.model;
        } else {
            const tmpData = {
                id: tmpId,
                attachments: attachments,
                res_id: thread.id,
                model: "discuss.channel",
            };
            if (this.store.user) {
                tmpData.author = this.store.self;
            }
            if (this.store.guest) {
                tmpData.guestAuthor = this.store.self;
            }
            if (parentId) {
                tmpData.parentMessage = this.store.messages[parentId];
            }
            const prettyContent = await prettifyMessageContent(body, params.validMentions);
            const { emojis } = await loadEmoji();
            const recentEmojis = JSON.parse(
                browser.localStorage.getItem("mail.emoji.frequent") || "{}"
            );
            const emojisInContent =
                prettyContent.match(/\p{Emoji_Presentation}|\p{Emoji}\uFE0F/gu) ?? [];
            for (const codepoints of emojisInContent) {
                if (emojis.some((emoji) => emoji.codepoints === codepoints)) {
                    recentEmojis[codepoints] ??= 0;
                    recentEmojis[codepoints]++;
                }
            }
            browser.localStorage.setItem("mail.emoji.frequent", JSON.stringify(recentEmojis));
            tmpMsg = this.messageService.insert({
                ...tmpData,
                body: markup(prettyContent),
                res_id: thread.id,
                model: thread.model,
                temporary_id: tmpId,
            });
            thread.messages.push(tmpMsg);
            thread.seen_message_id = tmpMsg.id;
        }
        const data = await this.rpc(this.getMessagePostRoute(thread), params);
        if (thread.type !== "chatter") {
            removeFromArrayWithPredicate(thread.messages, ({ id }) => id === tmpMsg.id);
            delete this.store.messages[tmpMsg.id];
        }
        if (!data) {
            return;
        }
        if (data.parentMessage) {
            data.parentMessage.body = data.parentMessage.body
                ? markup(data.parentMessage.body)
                : data.parentMessage.body;
        }
        if (data.id in this.store.messages) {
            data.temporary_id = null;
        }
        const message = this.messageService.insert(
            Object.assign(data, { body: markup(data.body) })
        );
        if (!thread.messages.some(({ id }) => id === message.id)) {
            thread.messages.push(message);
        }
        if (!message.isEmpty && this.store.hasLinkPreviewFeature) {
            this.rpc("/mail/link_preview", { message_id: data.id }, { silent: true });
        }
        return message;
    }

    /**
     * Get the parameters to pass to the message post route.
     */
    async getMessagePostParams({
        attachments,
        body,
        cannedResponseIds,
        isNote,
        rawMentions,
        thread,
    }) {
        const subtype = isNote ? "mail.mt_note" : "mail.mt_comment";
        const validMentions = this.store.user
            ? this.messageService.getMentionsFromText(rawMentions, body)
            : undefined;
        const partner_ids = validMentions?.partners.map((partner) => partner.id);
        if (!isNote) {
            const recipientIds = thread.suggestedRecipients
                .filter((recipient) => recipient.persona && recipient.checked)
                .map((recipient) => recipient.persona.id);
            partner_ids?.push(...recipientIds);
        }
        return {
            context: {
                mail_post_autofollow: !isNote && thread.hasWriteAccess,
            },
            post_data: {
                body: await prettifyMessageContent(body, validMentions),
                attachment_ids: attachments.map(({ id }) => id),
                canned_response_ids: cannedResponseIds,
                message_type: "comment",
                partner_ids,
                subtype_xmlid: subtype,
            },
            thread_id: thread.id,
            thread_model: thread.model,
        };
    }

    /**
     * @param {Thread} thread
     */
    getMessagePostRoute(thread) {
        return "/mail/message/post";
    }

    /**
     * @param {Thread} thread
     */
    canLeave(thread) {
        return (
            ["channel", "group"].includes(thread.type) &&
            !thread.message_needaction_counter &&
            !thread.group_based_subscription
        );
    }
    /**
     *
     * @param {Thread} thread
     */
    canUnpin(thread) {
        return thread.type === "chat" && this.getCounter(thread) === 0;
    }

    /**
     * @param {Thread} thread
     */
    getCounter(thread) {
        if (thread.type === "mailbox") {
            return thread.counter;
        }
        if (thread.type === "chat" || thread.type === "group") {
            return thread.message_unread_counter || thread.message_needaction_counter;
        }
        return thread.message_needaction_counter;
    }

    getDiscussCategoryCounter(categoryId) {
        return this.store.discuss[categoryId].threads.reduce((acc, threadLocalId) => {
            const channel = this.store.threads[threadLocalId];
            if (categoryId === "channels") {
                return channel.message_needaction_counter > 0 ? acc + 1 : acc;
            } else {
                return channel.message_unread_counter > 0 ? acc + 1 : acc;
            }
        }, 0);
    }

    /**
     * @param {import("@mail/core/common/thread_model").Thread} thread
     * @param {number} index
     */
    async setMainAttachmentFromIndex(thread, index) {
        thread.mainAttachment = thread.attachmentsInWebClientView[index];
        await this.orm.call("ir.attachment", "register_as_main_attachment", [
            thread.mainAttachment.id,
        ]);
    }

    /**
     * @param {import("@mail/core/common/composer_model").Composer} composer
     */
    clearComposer(composer) {
        composer.attachments.length = 0;
        composer.textInputContent = "";
        Object.assign(composer.selection, {
            start: 0,
            end: 0,
            direction: "none",
        });
    }

    /**
     * @param {import("@mail/core/common/persona_model").Persona} persona
     * @param {import("@mail/core/common/thread_model").Thread} [thread]
     */
    avatarUrl(persona, thread) {
        if (!persona) {
            return DEFAULT_AVATAR;
        }
        if (thread?.model === "discuss.channel") {
            if (persona.type === "partner") {
                return url(`/discuss/channel/${thread.id}/partner/${persona.id}/avatar_128`);
            }
            if (persona.type === "guest") {
                return url(`/discuss/channel/${thread.id}/guest/${persona.id}/avatar_128`);
            }
        }
        if (persona.type === "partner" && persona?.id) {
            const avatar = url("/web/image", {
                field: "avatar_128",
                id: persona.id,
                model: "res.partner",
            });
            return avatar;
        }
        if (persona.user?.id) {
            const avatar = url("/web/image", {
                field: "avatar_128",
                id: persona.user.id,
                model: "res.users",
            });
            return avatar;
        }
        return DEFAULT_AVATAR;
    }

    /**
     * @param {number} threadId
     * @param {string} data base64 representation of the binary
     */
    async notifyThreadAvatarToServer(threadId, data) {
        await this.rpc("/discuss/channel/update_avatar", {
            channel_id: threadId,
            data,
        });
    }

    /**
     * Following a load more or load around, listing of messages contains persistent messages.
     * Transient messages are missing, so this function puts known transient messages at the
     * right place in message list of thread.
     *
     * @param {Thread} thread
     */
    _enrichMessagesWithTransient(thread) {
        for (const message of thread.transientMessages) {
            if (message.id < thread.oldestPersistentMessage && !thread.loadOlder) {
                thread.messages.unshift(message);
            } else if (message.id > thread.newestPersistentMessage && !thread.loadNewer) {
                thread.messages.push(message);
            } else {
                const afterIndex = thread.messages.findIndex(
                    (msg) => msg.id > message.id && !msg.isTransient
                );
                thread.messages.splice(afterIndex - 1, 0, message);
            }
        }
    }
}

export const threadService = {
    dependencies: [
        "discuss.channel.member",
        "mail.attachment",
        "mail.store",
        "orm",
        "rpc",
        "notification",
        "router",
        "mail.persona",
        "mail.message",
        "ui",
    ],
    start(env, services) {
        return new ThreadService(env, services);
    },
};

registry.category("services").add("mail.thread", threadService);
