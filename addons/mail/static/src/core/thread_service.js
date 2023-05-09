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
        const channelMemberService = services["discuss.channel.member"];
        const messageService = services["mail.message"];
        const orm = services.orm;
        const rpc = services.rpc;
        const self = this;
        const store = services["mail.store"];

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

        Object.assign(Composer.prototype, {
            clear() {
                this.attachments.length = 0;
                this.textInputContent = "";
                Object.assign(this.selection, {
                    start: 0,
                    end: 0,
                    direction: "none",
                });
            },
        });
        Object.assign(Thread.prototype, {
            get canLeave() {
                return (
                    ["channel", "group"].includes(this.type) &&
                    !this.message_needaction_counter &&
                    !this.group_based_subscription
                );
            },
            canUnpin() {
                return this.type === "chat" && this.getCounter() === 0;
            },
            executeCommand(command, body = "") {
                return orm.call("discuss.channel", command.methodName, [[this.id]], {
                    body,
                });
            },
            async fetchChannelMembers() {
                const known_member_ids = this.channelMembers.map(
                    (channelMember) => channelMember.id
                );
                const results = await rpc("/discuss/channel/members", {
                    channel_id: this.id,
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
                this.memberCount = results["memberCount"];
                for (const channelMember of channelMembers) {
                    if (channelMember.persona || channelMember.partner) {
                        channelMemberService.insert({ ...channelMember, threadId: this.id });
                    }
                }
            },
            /**
             * @param {{after: Number, before: Number}}
             */
            async fetchMessages({ after, before } = {}) {
                this.status = "loading";
                if (this.type === "chatter" && !this.id) {
                    return [];
                }
                try {
                    // ordered messages received: newest to oldest
                    const rawMessages = await rpc(this.getFetchRoute(), {
                        ...this.getFetchParams(),
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
                        return messageService.insert(
                            Object.assign(data, { body: data.body ? markup(data.body) : data.body })
                        );
                    });
                    self.update(this, { isLoaded: true });
                    return messages;
                } catch (e) {
                    this.hasLoadingFailed = true;
                    throw e;
                } finally {
                    this.status = "ready";
                }
            },
            /**
             * @param {"older"|"newer"} epoch
             */
            async fetchMoreMessages(epoch = "older") {
                if (
                    this.status === "loading" ||
                    (epoch === "older" && !this.loadOlder) ||
                    (epoch === "newer" && !this.loadNewer)
                ) {
                    return;
                }
                const before = epoch === "older" ? this.oldestPersistentMessage?.id : undefined;
                const after = epoch === "newer" ? this.newestPersistentMessage?.id : undefined;
                try {
                    const fetched = await this.fetchMessages({ after, before });
                    if (
                        (after !== undefined &&
                            !this.messages.some((message) => message.id === after)) ||
                        (before !== undefined &&
                            !this.messages.some((message) => message.id === before))
                    ) {
                        // there might have been a jump to message during RPC fetch.
                        // Abort feeding messages as to not put holes in message list.
                        return;
                    }
                    const alreadyKnownMessages = new Set(this.messages.map(({ id }) => id));
                    const messagesToAdd = fetched.filter(
                        (message) => !alreadyKnownMessages.has(message.id)
                    );
                    if (epoch === "older") {
                        this.messages.unshift(...messagesToAdd);
                    } else {
                        this.messages.push(...messagesToAdd);
                    }
                    if (fetched.length < FETCH_LIMIT) {
                        if (epoch === "older") {
                            this.loadOlder = false;
                        } else if (epoch === "newer") {
                            this.loadNewer = false;
                            const missingMessages = this.pendingNewMessages.filter(
                                ({ id }) => !alreadyKnownMessages.has(id)
                            );
                            if (missingMessages.length > 0) {
                                this.messages.push(...missingMessages);
                                this.messages.sort((m1, m2) => m1.id - m2.id);
                            }
                        }
                    }
                } catch {
                    // handled in fetchMessages
                }
                this.pendingNewMessages = [];
            },
            async fetchNewMessages() {
                if (
                    this.status === "loading" ||
                    (this.isLoaded && ["discuss.channel", "mail.box"].includes(this.model))
                ) {
                    return;
                }
                const after = this.isLoaded ? this.newestPersistentMessage?.id : undefined;
                try {
                    const fetched = await this.fetchMessages({ after });
                    // feed messages
                    // could have received a new message as notification during fetch
                    // filter out already fetched (e.g. received as notification in the meantime)
                    let startIndex;
                    if (after === undefined) {
                        startIndex = 0;
                    } else {
                        const afterIndex = this.messages.findIndex(
                            (message) => message.id === after
                        );
                        if (afterIndex === -1) {
                            // there might have been a jump to message during RPC fetch.
                            // Abort feeding messages as to not put holes in message list.
                            return;
                        } else {
                            startIndex = afterIndex + 1;
                        }
                    }
                    const alreadyKnownMessages = new Set(this.messages.map((m) => m.id));
                    const filtered = fetched.filter(
                        (message) =>
                            !alreadyKnownMessages.has(message.id) &&
                            (this.persistentMessages.length === 0 ||
                                message.id < this.oldestPersistentMessage.id ||
                                message.id > this.newestPersistentMessage.id)
                    );
                    this.messages.splice(startIndex, 0, ...filtered);
                    // feed needactions
                    // same for needaction messages, special case for mailbox:
                    // kinda "fetch new/more" with needactions on many origin threads at once
                    if (this === store.discuss.inbox) {
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
                                : this.messages.findIndex((message) => message.id === after);
                        const filteredNeedaction = fetched.filter(
                            (message) =>
                                message.isNeedaction &&
                                (this.needactionMessages.length === 0 ||
                                    message.id < this.oldestNeedactionMessage.id ||
                                    message.id > this.newestNeedactionMessage.id)
                        );
                        this.needactionMessages.splice(
                            startNeedactionIndex,
                            0,
                            ...filteredNeedaction
                        );
                    }
                    Object.assign(this, {
                        loadOlder:
                            after === undefined && fetched.length === FETCH_LIMIT
                                ? true
                                : after === undefined && fetched.length !== FETCH_LIMIT
                                ? false
                                : this.loadOlder,
                    });
                } catch {
                    // handled in fetchMessages
                }
            },
            async fetchPinnedMessages() {
                if (
                    this.model !== "discuss.channel" ||
                    ["loaded", "loading"].includes(this.pinLoadState)
                ) {
                    return;
                }
                this.pinLoadState = "loading";
                try {
                    const messages = await rpc("/discuss/channel/pinned_messages", {
                        channel_id: this.id,
                    });
                    const pinnedMessages = messages.map((message) => {
                        if (message.parentMessage) {
                            message.parentMessage.body = markup(message.parentMessage.body);
                        }
                        message.body = markup(message.body);
                        return this.messageService.insert(message);
                    });
                    this.pinnedMessages = pinnedMessages;
                } finally {
                    this.pinLoadState = "loaded";
                }
            },
            getCounter() {
                if (this.type === "mailbox") {
                    return this.counter;
                }
                if (this.type === "chat" || this.type === "group") {
                    return this.message_unread_counter || this.message_needaction_counter;
                }
                return this.message_needaction_counter;
            },
            getFetchParams() {
                if (this.model === "discuss.channel") {
                    return { channel_id: this.id };
                }
                if (this.type === "chatter") {
                    return {
                        thread_id: this.id,
                        thread_model: this.model,
                    };
                }
                return {};
            },
            getFetchRoute() {
                if (this.model === "discuss.channel") {
                    return "/discuss/channel/messages";
                }
                switch (this.type) {
                    case "chatter":
                        return "/mail/thread/messages";
                    case "mailbox":
                        return `/mail/${this.id}/messages`;
                    default:
                        throw new Error(`Unknown thread type: ${this.type}`);
                }
            },
            async leave() {
                await orm.call("discuss.channel", "action_unfollow", [this.id]);
                self.remove(this);
                self.setDiscussThread(
                    store.discuss.channels.threads[0]
                        ? store.threads[store.discuss.channels.threads[0]]
                        : store.discuss.inbox
                );
            },
            /**
             * Get ready to jump to a message in a thread. This method will fetch the
             * messages around the message to jump to if required, and update the thread
             * messages accordingly.
             *
             * @param {Message} [messageId] if not provided, load around newest message
             */
            async loadAround(messageId) {
                if (!this.messages.some(({ id }) => id === messageId)) {
                    const messages = await rpc(this.getFetchRoute(), {
                        ...this.getFetchParams(),
                        around: messageId,
                    });
                    this.messages = messages.reverse().map((message) =>
                        messageService.insert({
                            ...message,
                            body: message.body ? markup(message.body) : message.body,
                        })
                    );
                    this.loadNewer = true;
                    this.loadOlder = true;
                    if (messages.length < FETCH_LIMIT) {
                        const olderMessagesCount = messages.filter(
                            ({ id }) => id < messageId
                        ).length;
                        if (olderMessagesCount < FETCH_LIMIT / 2) {
                            this.loadOlder = false;
                        } else {
                            this.loadNewer = false;
                        }
                    }
                    // Give some time to the UI to update.
                    await new Promise((resolve) =>
                        setTimeout(() => requestAnimationFrame(resolve))
                    );
                }
            },
            async markAllMessagesAsRead() {
                await orm.silent.call("mail.message", "mark_all_as_read", [
                    [
                        ["model", "=", this.model],
                        ["res_id", "=", this.id],
                    ],
                ]);
                Object.assign(this, {
                    needactionMessages: [],
                    message_unread_counter: 0,
                    message_needaction_counter: 0,
                    seen_message_id: this.newestPersistentMessage?.id,
                });
            },
            async markAsFetched() {
                await orm.silent.call("discuss.channel", "channel_fetched", [[this.id]]);
            },
            async markAsRead() {
                if (!this.isLoaded && this.status === "loading") {
                    await this.isLoadedDeferred;
                    await new Promise(setTimeout);
                }
                const newestPersistentMessage = this.newestPersistentMessage;
                this.seen_message_id = this.newestPersistentMessage?.id ?? false;
                if (
                    this.message_unread_counter > 0 &&
                    this.allowSetLastSeenMessage &&
                    newestPersistentMessage
                ) {
                    rpc("/discuss/channel/set_last_seen_message", {
                        channel_id: this.id,
                        last_message_id: newestPersistentMessage.id,
                    }).then(() => {
                        self.updateSeen(this, newestPersistentMessage.id);
                    });
                }
                if (this.hasNeedactionMessages) {
                    this.markAllMessagesAsRead();
                }
            },
            async notifyDescriptionToServer(description) {
                this.description = description;
                return orm.call("discuss.channel", "channel_change_description", [[this.id]], {
                    description,
                });
            },
            async notifyNameToServer(name) {
                if (this.type === "channel" || this.type === "group") {
                    this.name = name;
                    await orm.call("discuss.channel", "channel_rename", [[this.id]], {
                        name,
                    });
                } else if (this.type === "chat") {
                    this.customName = name;
                    await orm.call("discuss.channel", "channel_set_custom_name", [[this.id]], {
                        name,
                    });
                }
            },
            /**
             * @param {boolean} replaceNewMessageChatWindow
             */
            open(replaceNewMessageChatWindow) {
                self.setDiscussThread(this);
            },
            pin() {
                if (this.model !== "discuss.channel" || store.guest) {
                    return;
                }
                this.is_pinned = true;
                return orm.silent.call("discuss.channel", "channel_pin", [this.id], {
                    pinned: true,
                });
            },
            /**
             * @param {string} body
             */
            async post(body, { attachments = [], isNote = false, parentId, rawMentions }) {
                let tmpMsg;
                const subtype = isNote ? "mail.mt_note" : "mail.mt_comment";
                const validMentions = store.user
                    ? messageService.getMentionsFromText(rawMentions, body)
                    : undefined;
                const partner_ids = validMentions?.partners.map((partner) => partner.id);
                if (!isNote) {
                    const recipientIds = this.suggestedRecipients
                        .filter((recipient) => recipient.persona && recipient.checked)
                        .map((recipient) => recipient.persona.id);
                    partner_ids?.push(...recipientIds);
                }
                const lastMessageId = messageService.getLastMessageId();
                const tmpId = lastMessageId + 0.01;
                const params = {
                    context: {
                        mail_post_autofollow: !isNote && this.hasWriteAccess,
                        temporary_id: tmpId,
                    },
                    post_data: {
                        body: await prettifyMessageContent(body, validMentions),
                        attachment_ids: attachments.map(({ id }) => id),
                        message_type: "comment",
                        partner_ids,
                        subtype_xmlid: subtype,
                    },
                    thread_id: this.id,
                    thread_model: this.model,
                };
                if (parentId) {
                    params.post_data.parent_id = parentId;
                }
                if (this.type === "chatter") {
                    params.thread_id = this.id;
                    params.thread_model = this.model;
                } else {
                    const tmpData = {
                        id: tmpId,
                        attachments: attachments,
                        res_id: this.id,
                        model: "discuss.channel",
                    };
                    if (store.user) {
                        tmpData.author = store.self;
                    }
                    if (store.guest) {
                        tmpData.guestAuthor = store.self;
                    }
                    if (parentId) {
                        tmpData.parentMessage = store.messages[parentId];
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
                    browser.localStorage.setItem(
                        "mail.emoji.frequent",
                        JSON.stringify(recentEmojis)
                    );
                    tmpMsg = messageService.insert({
                        ...tmpData,
                        body: markup(prettyContent),
                        res_id: this.id,
                        model: this.model,
                        temporary_id: tmpId,
                    });
                    this.messages.push(tmpMsg);
                    this.seen_message_id = tmpMsg.id;
                }
                const data = await rpc("/mail/message/post", params);
                if (data.parentMessage) {
                    data.parentMessage.body = data.parentMessage.body
                        ? markup(data.parentMessage.body)
                        : data.parentMessage.body;
                }
                if (data.id in store.messages) {
                    data.temporary_id = null;
                }
                const message = messageService.insert(
                    Object.assign(data, { body: markup(data.body) })
                );
                if (!this.messages.some(({ id }) => id === message.id)) {
                    this.messages.push(message);
                }
                if (!message.isEmpty && store.hasLinkPreviewFeature) {
                    rpc("/mail/link_preview", { message_id: data.id }, { silent: true });
                }
                if (this.type !== "chatter") {
                    removeFromArrayWithPredicate(this.messages, ({ id }) => id === tmpMsg.id);
                    delete store.messages[tmpMsg.id];
                }
                return message;
            },
            remove() {
                removeFromArray(store.discuss.chats.threads, this.localId);
                removeFromArray(store.discuss.channels.threads, this.localId);
                delete store.threads[this.localId];
            },
            /**
             * @param {number} index
             */
            async setMainAttachmentFromIndex(index) {
                this.mainAttachment = this.attachmentsInWebClientView[index];
                await orm.call("ir.attachment", "register_as_main_attachment", [
                    this.mainAttachment.id,
                ]);
            },
            unpin() {
                if (this.model !== "discuss.channel") {
                    return;
                }
                return orm.silent.call("discuss.channel", "channel_pin", [this.id], {
                    pinned: false,
                });
            },
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

    async createChannel(name) {
        const data = await this.orm.call("discuss.channel", "channel_create", [
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
        this.store.discuss.chats.threads.sort((localId_1, localId_2) => {
            const thread1 = this.store.threads[localId_1];
            const thread2 = this.store.threads[localId_2];
            return thread2.lastInterestDateTime.ts - thread1.lastInterestDateTime.ts;
        });
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
