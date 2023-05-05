/** @odoo-module */

import { markup } from "@odoo/owl";
import { Thread } from "../core/thread_model";
import { _t } from "@web/core/l10n/translation";
import {
    removeFromArray,
    removeFromArrayWithPredicate,
    replaceArrayWithCompare,
} from "@mail/utils/arrays";
import { assignDefined, createLocalId, onChange } from "../utils/misc";
import { Composer } from "../composer/composer_model";
import { prettifyMessageContent } from "../utils/format";
import { registry } from "@web/core/registry";
import { url } from "@web/core/utils/urls";
import { memoize } from "@web/core/utils/functions";
import { DEFAULT_AVATAR } from "@mail/core/persona_service";
import { loadEmoji } from "@mail/emoji_picker/emoji_picker";
import { browser } from "@web/core/browser/browser";

const FETCH_LIMIT = 30;

export class ThreadService {
    nextId = 0;

    constructor(env, services) {
        this.setup(env, services);
    }

    setup(env, services) {
        this.env = env;
        /** @type {import("@mail/core/channel_member_service").ChannelMemberService} */
        this.channelMemberService = services["discuss.channel.member"];
        /** @type {import("@mail/attachments/attachment_service").AttachmentService} */
        this.attachmentsService = services["mail.attachment"];
        /** @type {import("@mail/core/store_service").Store} */
        this.store = services["mail.store"];
        this.orm = services.orm;
        this.rpc = services.rpc;
        this.notificationService = services.notification;
        this.router = services.router;
        /** @type {import("@mail/core/persona_service").PersonaService} */
        this.personaService = services["mail.persona"];
        /** @type {import("@mail/core/message_service").MessageService} */
        this.messageService = services["mail.message"];
        // FIXME this prevents cyclic dependencies between mail.thread and mail.message
        this.env.bus.addEventListener("MESSAGE-SERVICE:INSERT_THREAD", ({ detail }) => {
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
        const { id, name, description, channel, uuid, authorizedGroupFullName } = serverData;
        const type = channel.channel_type;
        const channelType = serverData.channel.channel_type;
        const isAdmin =
            channelType !== "group" && serverData.create_uid === this.store.user?.user?.id;
        const thread = this.insert({
            id,
            model: "discuss.channel",
            name,
            type,
            description,
            serverData: serverData,
            isAdmin,
            uuid,
            authorizedGroupFullName,
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
        thread.seen_message_id = thread.newestPersistentMessage?.id ?? false;
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

    async fetchPinnedMessages(thread) {
        if (
            thread.model !== "discuss.channel" ||
            ["loaded", "loading"].includes(thread.pinLoadState)
        ) {
            return;
        }
        thread.pinLoadState = "loading";
        try {
            const messages = await this.rpc("/discuss/channel/pinned_messages", {
                channel_id: thread.id,
            });
            const pinnedMessages = messages.map((message) => {
                if (message.parentMessage) {
                    message.parentMessage.body = markup(message.parentMessage.body);
                }
                message.body = markup(message.body);
                return this.messageService.insert(message);
            });
            thread.pinnedMessages = pinnedMessages;
        } finally {
            thread.pinLoadState = "loaded";
        }
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
            thread.messages = messages.reverse().map((message) =>
                this.messageService.insert({
                    ...message,
                    body: message.body ? markup(message.body) : message.body,
                })
            );
            thread.loadNewer = true;
            thread.loadOlder = true;
            if (messages.length < FETCH_LIMIT) {
                const olderMessagesCount = messages.filter(({ id }) => id < messageId).length;
                if (olderMessagesCount < FETCH_LIMIT / 2) {
                    thread.loadOlder = false;
                } else {
                    thread.loadNewer = false;
                }
            }
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
        if (thread.model !== "discuss.channel" || this.store.guest) {
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
            const localId = createLocalId("partner", partnerId);
            let user = this.store.personas[localId]?.user;
            if (!user) {
                [user] = await this.orm.silent.searchRead(
                    "res.users",
                    [["partner_id", "=", partnerId]],
                    [],
                    { context: { active_test: false } }
                );
                if (!user) {
                    this.notificationService.add(
                        _t("You can only chat with partners that have a dedicated user."),
                        { type: "info" }
                    );
                    return;
                }
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
            serverData: { channel: { avatarCacheKey: "hello" } },
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
            id: data.id,
            model: "discuss.channel",
            name: undefined,
            type: "chat",
            serverData: data,
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
     * @param {import("@mail/core/thread_model").Thread} thread
     * @param {boolean} pushState
     */
    setDiscussThread(thread, pushState = true) {
        this.store.discuss.threadLocalId = thread.localId;
        const activeId =
            typeof thread.id === "string"
                ? `mail.box_${thread.id}`
                : `discuss.channel_${thread.id}`;
        this.store.discuss.activeTab = !this.store.isSmall
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
     * @param {import("@mail/core/thread_model").Thread} thread
     * @param {Object} data
     */
    update(thread, data) {
        const { attachments, serverData, ...remainingData } = data;
        assignDefined(thread, remainingData);
        if (attachments) {
            // smart process to avoid triggering reactives when there is no change between the 2 arrays
            replaceArrayWithCompare(
                thread.attachments,
                attachments.map((attachment) => this.attachmentsService.insert(attachment)),
                (a1, a2) => a1.id === a2.id
            );
        }
        if (serverData) {
            assignDefined(thread, serverData, [
                "uuid",
                "authorizedGroupFullName",
                "description",
                "hasWriteAccess",
                "is_pinned",
                "message_needaction_counter",
                "name",
                "seen_message_id",
                "state",
                "group_based_subscription",
                "last_interest_dt",
                "defaultDisplayMode",
            ]);
            if (serverData.channel && "message_unread_counter" in serverData.channel) {
                thread.message_unread_counter = serverData.channel.message_unread_counter;
            }
            thread.lastServerMessageId = serverData.last_message_id ?? thread.lastServerMessageId;
            if (thread.model === "discuss.channel" && serverData.channel) {
                thread.channel = assignDefined(thread.channel ?? {}, serverData.channel);
            }

            thread.memberCount = serverData.channel?.memberCount ?? thread.memberCount;
            if ("rtc_inviting_session" in serverData) {
                this.env.bus.trigger("THREAD-SERVICE:UPDATE_RTC_SESSIONS", {
                    thread,
                    record: serverData.rtc_inviting_session,
                });
                thread.invitingRtcSessionId = serverData.rtc_inviting_session.id;
                if (!this.store.ringingThreads.includes(thread.localId)) {
                    this.store.ringingThreads.push(thread.localId);
                }
            }
            if ("rtcInvitingSession" in serverData) {
                if (Array.isArray(serverData.rtcInvitingSession)) {
                    if (serverData.rtcInvitingSession[0][0] === "unlink") {
                        thread.invitingRtcSessionId = undefined;
                        removeFromArray(this.store.ringingThreads, thread.localId);
                    }
                    return;
                }
                this.env.bus.trigger("THREAD-SERVICE:UPDATE_RTC_SESSIONS", {
                    thread,
                    record: serverData.rtcInvitingSession,
                });
                thread.invitingRtcSessionId = serverData.rtcInvitingSession.id;
                this.store.ringingThreads.push(thread.localId);
            }
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
            if ("rtcSessions" in serverData) {
                // FIXME this prevents cyclic dependencies between mail.thread and mail.rtc
                this.env.bus.trigger("THREAD-SERVICE:UPDATE_RTC_SESSIONS", {
                    thread,
                    commands: serverData.rtcSessions,
                });
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
        onChange(thread, "isLoaded", () => thread.isLoadedDeferred.resolve());
        onChange(thread, "channelMembers", () => this.store.updateBusSubscription());
        onChange(thread, "is_pinned", () => {
            if (!thread.is_pinned && this.store.discuss.threadLocalId === thread.localId) {
                this.store.discuss.threadLocalId = null;
            }
        });
        thread = this.store.threads[thread.localId] = thread;
        this.update(thread, data);
        this.insertComposer({ thread });
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
    async post(thread, body, { attachments = [], isNote = false, parentId, rawMentions }) {
        let tmpMsg;
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
        const lastMessageId = this.messageService.getLastMessageId();
        const tmpId = lastMessageId + 0.01;
        const params = {
            context: {
                mail_post_autofollow: !isNote && thread.hasWriteAccess,
                temporary_id: tmpId,
            },
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
            const prettyContent = await prettifyMessageContent(body, validMentions);
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
        const data = await this.rpc("/mail/message/post", params);
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
        if (thread.type !== "chatter") {
            removeFromArrayWithPredicate(thread.messages, ({ id }) => id === tmpMsg.id);
            delete this.store.messages[tmpMsg.id];
        }
        return message;
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
     * @param {import("@mail/core/thread_model").Thread} thread
     * @param {number} index
     */
    async setMainAttachmentFromIndex(thread, index) {
        thread.mainAttachment = thread.attachmentsInWebClientView[index];
        await this.orm.call("ir.attachment", "register_as_main_attachment", [
            thread.mainAttachment.id,
        ]);
    }

    /**
     * @param {import("@mail/composer/composer_model").Composer} composer
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
     * @param {import('@mail/core/persona_model').Persona} persona
     * @param {import("@mail/core/thread_model").Thread} [thread]
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
    ],
    start(env, services) {
        return new ThreadService(env, services);
    },
};

registry.category("services").add("mail.thread", threadService);
