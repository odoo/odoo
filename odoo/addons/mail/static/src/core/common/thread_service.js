/* @odoo-module */

import { loadEmoji } from "@web/core/emoji_picker/emoji_picker";
import { DEFAULT_AVATAR } from "@mail/core/common/persona_service";
import { Record } from "@mail/core/common/record";
import { prettifyMessageContent } from "@mail/utils/common/format";

import { browser } from "@web/core/browser/browser";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { memoize } from "@web/core/utils/functions";
import { url } from "@web/core/utils/urls";
import { compareDatetime } from "@mail/utils/common/misc";

const FETCH_LIMIT = 30;

export class ThreadService {
    nextId = 0;
    /**
     * @param {import("@web/env").OdooEnv} env
     * @param {Partial<import("services").Services>} services
     */
    constructor(env, services) {
        this.setup(env, services);
    }

    /**
     * @param {import("@web/env").OdooEnv} env
     * @param {Partial<import("services").Services>} services
     */
    setup(env, services) {
        this.env = env;
        this.store = services["mail.store"];
        this.orm = services.orm;
        this.rpc = services.rpc;
        this.notificationService = services.notification;
        this.router = services.router;
        this.ui = services.ui;
        this.user = services.user;
        this.messageService = services["mail.message"];
        this.personaService = services["mail.persona"];
        this.outOfFocusService = services["mail.out_of_focus"];
    }

    /**
     * @param {import("models).Thread} thread
     * @param {number} id
     * @returns {Promise<import("models").Thread|undefined>}
     */
    async fetchChannel(id) {
        const channelData = await this.rpc("/discuss/channel/info", { channel_id: id });
        if (!channelData) {
            return;
        }
        return this.store.Thread.insert({
            ...channelData,
            model: "discuss.channel",
            type: channelData.channel_type,
        });
    }

    async fetchChannelMembers(thread) {
        if (thread.fetchMembersState === "pending") {
            return;
        }
        const previousState = thread.fetchMembersState;
        thread.fetchMembersState = "pending";
        const known_member_ids = thread.channelMembers.map((channelMember) => channelMember.id);
        let results;
        try {
            results = await this.rpc("/discuss/channel/members", {
                channel_id: thread.id,
                known_member_ids: known_member_ids,
            });
        } catch (e) {
            thread.fetchMembersState = previousState;
            throw e;
        }
        thread.fetchMembersState = "fetched";
        let channelMembers = [];
        if (
            results["channelMembers"] &&
            results["channelMembers"][0] &&
            results["channelMembers"][0][1]
        ) {
            channelMembers = results["channelMembers"][0][1];
        }
        thread.memberCount = results["memberCount"];
        Record.MAKE_UPDATE(() => {
            for (const channelMember of channelMembers) {
                if (channelMember.persona || channelMember.partner) {
                    thread.channelMembers.add({ ...channelMember, thread });
                }
            }
        });
    }

    /**
     * @param {import("models").Thread} thread
     */
    markAsRead(thread) {
        const newestPersistentMessage = thread.newestPersistentOfAllMessage;
        if (!newestPersistentMessage && !thread.isLoaded) {
            thread.isLoadedDeferred
                .then(() => new Promise(setTimeout))
                .then(() => this.markAsRead(thread));
        }
        thread.seen_message_id = newestPersistentMessage?.id ?? false;
        const alreadySeenBySelf = newestPersistentMessage?.isSeenBySelf;
        if (thread.selfMember) {
            thread.selfMember.lastSeenMessage = newestPersistentMessage;
        }
        if (newestPersistentMessage && thread.selfMember && !alreadySeenBySelf) {
            this.rpc("/discuss/channel/set_last_seen_message", {
                channel_id: thread.id,
                last_message_id: newestPersistentMessage.id,
            }).catch((e) => {
                if (e.code !== 404) {
                    throw e;
                }
            });
        }
        if (thread.needactionMessages.length > 0) {
            this.markAllMessagesAsRead(thread);
        }
    }

    /** @deprecated */
    updateSeen(thread, lastSeenId = thread.newestPersistentOfAllMessage?.id) {}

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
            seen_message_id: thread.newestPersistentNotEmptyOfAllMessage?.id,
        });
    }

    /**
     * @param {import("models").Thread} thread
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
     * @param {import("models").Thread} thread
     * @param {{after: Number, before: Number}}
     */
    async fetchMessages(thread, { after, before } = {}) {
        thread.status = "loading";
        if (thread.type === "chatter" && !thread.id) {
            thread.isLoaded = true;
            return [];
        }
        try {
            // ordered messages received: newest to oldest
            const { messages: rawMessages } = await this.rpc(this.getFetchRoute(thread), {
                ...this.getFetchParams(thread),
                limit: FETCH_LIMIT,
                after,
                before,
            });
            const messages = this.store.Message.insert(rawMessages.reverse(), { html: true });
            thread.isLoaded = true;
            return messages;
        } catch (e) {
            thread.hasLoadingFailed = true;
            throw e;
        } finally {
            thread.status = "ready";
        }
    }

    /**
     * @param {import("models").Thread} thread
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
            if (thread.eq(this.store.discuss.inbox)) {
                Record.MAKE_UPDATE(() => {
                    for (const message of fetched) {
                        const thread = message.originThread;
                        if (thread && message.notIn(thread.needactionMessages)) {
                            thread.needactionMessages.unshift(message);
                        }
                    }
                });
            } else {
                const startNeedactionIndex =
                    after === undefined
                        ? 0
                        : thread.messages.findIndex((message) => message.id === after);
                const filteredNeedaction = fetched.filter(
                    (message) =>
                        message.isNeedaction &&
                        (thread.needactionMessages.length === 0 ||
                            message.id < thread.needactionMessages[0].id ||
                            message.id > thread.needactionMessages.at(-1).id)
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
     * @param {import("models").Message} [messageId] if not provided, load around newest message
     */
    async loadAround(thread, messageId) {
        if (!thread.messages.some(({ id }) => id === messageId)) {
            thread.isLoaded = false;
            thread.scrollTop = undefined;
            const { messages } = await this.rpc(this.getFetchRoute(thread), {
                ...this.getFetchParams(thread),
                around: messageId,
            });
            thread.isLoaded = true;
            thread.messages = this.store.Message.insert(messages.reverse(), { html: true });
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
        }
    }

    // This function is like fetchNewMessages but just for a single message at most on all pinned threads
    fetchPreviews = memoize(async () => {
        const ids = [];
        for (const thread of Object.values(this.store.Thread.records)) {
            if (["channel", "group", "chat"].includes(thread.type)) {
                ids.push(thread.id);
            }
        }
        if (ids.length) {
            const previews = await this.orm.call("discuss.channel", "channel_fetch_preview", [ids]);
            Record.MAKE_UPDATE(() => {
                for (const preview of previews) {
                    const thread = this.store.Thread.get({
                        model: "discuss.channel",
                        id: preview.id,
                    });
                    const message = this.store.Message.insert(preview.last_message, { html: true });
                    if (message.isNeedaction) {
                        thread.needactionMessages.add(message);
                    }
                }
            });
        }
    });

    /**
     * @param {import("models").Thread} thread
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

    async unpin(thread) {
        thread.isLocallyPinned = false;
        if (thread.eq(this.store.discuss.thread)) {
            this.router.replaceState({ active_id: undefined });
        }
        if (thread.model === "discuss.channel" && thread.is_pinned) {
            return this.orm.silent.call("discuss.channel", "channel_pin", [thread.id], {
                pinned: false,
            });
        }
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

    /** @deprecated */
    sortChannels() {
        this.store.discuss.channels.threads.sort((t1, t2) =>
            String.prototype.localeCompare.call(t1.name, t2.name)
        );
        this.store.discuss.chats.threads.sort(
            (t1, t2) =>
                compareDatetime(t2.lastInterestDateTime, t1.lastInterestDateTime) || t2.id - t1.id
        );
    }

    /**
     * @param {import("models").Thread} thread
     * @param {boolean} replaceNewMessageChatWindow
     * @param {Object} [options]
     */
    open(thread, replaceNewMessageChatWindow, options) {
        this.setDiscussThread(thread);
    }

    async openChat(person) {
        const chat = await this.getChat(person);
        if (chat) {
            this.open(chat);
        }
    }

    /**
     * Search and fetch for a partner with a given user or partner id.
     * @param {Object} param0
     * @param {number} param0.userId
     * @param {number} param0.partnerId
     * @returns {Promise<import("models").Persona> | undefined}
     */
    async getPartner({ userId, partnerId }) {
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
            const partner = this.store.Persona.insert({ id: partnerId, type: "partner" });
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
            return partner;
        }
    }

    /**
     * @param {import("model ").Persona} partner
     * @returns {import("models").Thread | undefined}
     */
    searchChat(partner) {
        if (!partner) {
            return;
        }
        return Object.values(this.store.Thread.records).find(
            (thread) => thread.type === "chat" && thread.chatPartner?.eq(partner)
        );
    }

    /**
     * Search and fetch for a partner with a given user or partner id.
     * @param {Object} param0
     * @param {number} param0.userId
     * @param {number} param0.partnerId
     * @returns {Promise<import("models").Thread | undefined>}
     */
    async getChat({ userId, partnerId }) {
        const partner = await this.getPartner({ userId, partnerId });
        let chat = this.searchChat(partner);
        if (!chat || !chat.is_pinned) {
            chat = await this.joinChat(partnerId || partner?.id);
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
        await this.env.services["mail.messaging"].isReady;
        await this.orm.call("discuss.channel", "add_members", [[id]], {
            partner_ids: [this.store.user.id],
        });
        const thread = this.store.Thread.insert({
            id,
            model: "discuss.channel",
            name,
            type: "channel",
            channel: { avatarCacheKey: "hello" },
        });
        this.open(thread);
        return thread;
    }

    async joinChat(id) {
        const data = await this.orm.call("discuss.channel", "channel_get", [], {
            partners_to: [id],
        });
        const thread = this.store.Thread.insert({
            ...data,
            model: "discuss.channel",
            type: "chat",
        });
        return thread;
    }

    executeCommand(thread, command, body = "") {
        return this.orm.call("discuss.channel", command.methodName, [[thread.id]], {
            body,
        });
    }

    /**
     * @param {import("models).Thread} thread
     * @param {string} name
     */
    async renameThread(thread, name) {
        if (!thread) {
            return;
        }
        const newName = name.trim();
        if (
            newName !== thread.displayName &&
            ((newName && thread.type === "channel") ||
                thread.type === "chat" ||
                thread.type === "group")
        ) {
            if (thread.type === "channel" || thread.type === "group") {
                thread.name = newName;
                await this.orm.call("discuss.channel", "channel_rename", [[thread.id]], {
                    name: newName,
                });
            } else if (thread.type === "chat") {
                thread.custom_channel_name = newName;
                await this.orm.call("discuss.channel", "channel_set_custom_name", [[thread.id]], {
                    name: newName,
                });
            }
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
        channel.delete();
        this.setDiscussThread(
            this.store.discuss.channels.threads[0]
                ? this.store.discuss.channels.threads[0]
                : this.store.discuss.inbox
        );
    }

    /**
     * @param {import("models").Thread} thread
     * @param {boolean} pushState
     */
    setDiscussThread(thread, pushState) {
        if (pushState === undefined) {
            pushState = thread.localId !== this.store.discuss.thread?.localId;
        }
        this.store.discuss.thread = thread;
        const activeId =
            typeof thread.id === "string"
                ? `mail.box_${thread.id}`
                : `discuss.channel_${thread.id}`;
        this.store.discuss.activeTab =
            !this.ui.isSmall || thread.model === "mail.box"
                ? "main"
                : ["chat", "group"].includes(thread.type)
                ? "chat"
                : "channel";
        if (pushState) {
            this.router.pushState({ active_id: activeId });
        }
    }

    /**
     * @param {import("models").Thread} thread
     * @param {string} body
     */
    async post(
        thread,
        body,
        {
            attachments = [],
            isNote = false,
            parentId,
            mentionedChannels = [],
            mentionedPartners = [],
            cannedResponseIds,
        } = {}
    ) {
        let tmpMsg;
        const params = await this.getMessagePostParams({
            attachments,
            body,
            cannedResponseIds,
            isNote,
            mentionedChannels,
            mentionedPartners,
            thread,
        });
        const tmpId = this.messageService.getNextTemporaryId();
        params.context = { ...this.user.context, ...params.context, temporary_id: tmpId };
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
            tmpData.author = this.store.self;
            if (parentId) {
                tmpData.parentMessage = this.store.Message.get(parentId);
            }
            const prettyContent = await prettifyMessageContent(
                body,
                this.messageService.getMentionsFromText(body, {
                    mentionedChannels,
                    mentionedPartners,
                })
            );
            const { emojis } = await loadEmoji();
            const recentEmojis = JSON.parse(
                browser.localStorage.getItem("web.emoji.frequent") || "{}"
            );
            const emojisInContent =
                prettyContent.match(/\p{Emoji_Presentation}|\p{Emoji}\uFE0F/gu) ?? [];
            for (const codepoints of emojisInContent) {
                if (emojis.some((emoji) => emoji.codepoints === codepoints)) {
                    recentEmojis[codepoints] ??= 0;
                    recentEmojis[codepoints]++;
                }
            }
            browser.localStorage.setItem("web.emoji.frequent", JSON.stringify(recentEmojis));
            tmpMsg = this.store.Message.insert(
                {
                    ...tmpData,
                    body: prettyContent,
                    res_id: thread.id,
                    model: thread.model,
                    temporary_id: tmpId,
                },
                { html: true }
            );
            thread.messages.push(tmpMsg);
            thread.seen_message_id = tmpMsg.id;
            if (thread.selfMember) {
                thread.selfMember.lastSeenMessage = tmpMsg;
            }
        }
        const data = await this.rpc(this.getMessagePostRoute(thread), params);
        tmpMsg?.delete();
        if (!data) {
            return;
        }
        if (data.id in this.store.Message.records) {
            data.temporary_id = null;
        }
        const message = this.store.Message.insert(data, { html: true });
        thread.messages.add(message);
        if (thread.selfMember && !message.isSeenBySelf) {
            thread.seen_message_id = message.id;
            thread.selfMember.lastSeenMessage = message;
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
        mentionedChannels,
        mentionedPartners,
        thread,
    }) {
        const subtype = isNote ? "mail.mt_note" : "mail.mt_comment";
        const validMentions = this.store.user
            ? this.messageService.getMentionsFromText(body, {
                  mentionedChannels,
                  mentionedPartners,
              })
            : undefined;
        const partner_ids = validMentions?.partners.map((partner) => partner.id);
        const recipientEmails = [];
        const recipientAdditionalValues = {};
        if (!isNote) {
            const recipientIds = thread.suggestedRecipients
                .filter((recipient) => recipient.persona && recipient.checked)
                .map((recipient) => recipient.persona.id);
            thread.suggestedRecipients
                .filter((recipient) => recipient.checked && !recipient.persona)
                .forEach((recipient) => {
                    recipientEmails.push(recipient.email);
                    recipientAdditionalValues[recipient.email] = recipient.defaultCreateValues;
                });
            partner_ids?.push(...recipientIds);
        }
        return {
            context: {
                mail_post_autofollow: !isNote && thread.hasWriteAccess,
            },
            post_data: {
                body: await prettifyMessageContent(body, validMentions),
                attachment_ids: attachments.map(({ id }) => id),
                attachment_tokens: attachments.map((attachment) => attachment.accessToken),
                canned_response_ids: cannedResponseIds,
                message_type: "comment",
                partner_ids,
                subtype_xmlid: subtype,
                partner_emails: recipientEmails,
                partner_additional_values: recipientAdditionalValues,
            },
            thread_id: thread.id,
            thread_model: thread.model,
        };
    }

    /**
     * @param {import("models").Thread} thread
     */
    getMessagePostRoute(thread) {
        return "/mail/message/post";
    }

    /**
     * @param {import("models").Thread} thread
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
     * @param {import("models").Thread} thread
     */
    canUnpin(thread) {
        return thread.type === "chat" && this.getCounter(thread) === 0;
    }

    /**
     * @param {import("models").Thread} thread
     */
    getCounter(thread) {
        if (thread.type === "mailbox") {
            return thread.counter;
        }
        if (thread.isChatChannel) {
            return thread.message_unread_counter || thread.message_needaction_counter;
        }
        return thread.message_needaction_counter;
    }

    getDiscussSidebarCategoryCounter(categoryId) {
        return this.store.discuss[categoryId].threads.reduce((acc, channel) => {
            if (categoryId === "channels") {
                return channel.message_needaction_counter > 0 ? acc + 1 : acc;
            } else {
                return channel.message_unread_counter > 0 ? acc + 1 : acc;
            }
        }, 0);
    }

    /**
     * @param {import("models").Thread} thread
     * @param {number} index
     */
    async setMainAttachmentFromIndex(thread, index) {
        thread.mainAttachment = thread.attachmentsInWebClientView[index];
        await this.orm.call("ir.attachment", "register_as_main_attachment", [
            thread.mainAttachment.id,
        ]);
    }

    /**
     * @param {import("models").Composer} composer
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
     * @param {import("models").Persona} persona
     * @param {import("models").Thread} [thread]
     */
    avatarUrl(persona, thread) {
        if (!persona) {
            return DEFAULT_AVATAR;
        }
        const urlParams = {};
        if (persona.write_date) {
            urlParams.unique = persona.write_date;
        }
        if (persona.is_company === undefined && this.store.self?.user?.isInternalUser) {
            this.personaService.fetchIsCompany(persona);
        }
        if (thread?.model === "discuss.channel") {
            if (persona.type === "partner") {
                return url(
                    `/discuss/channel/${thread.id}/partner/${persona.id}/avatar_128`,
                    urlParams
                );
            }
            if (persona.type === "guest") {
                return url(
                    `/discuss/channel/${thread.id}/guest/${persona.id}/avatar_128`,
                    urlParams
                );
            }
        }
        if (persona.type === "partner" && persona?.id) {
            const avatar = url("/web/image", {
                field: "avatar_128",
                id: persona.id,
                model: "res.partner",
                ...urlParams,
            });
            return avatar;
        }
        if (persona.user?.id) {
            const avatar = url("/web/image", {
                field: "avatar_128",
                id: persona.user.id,
                model: "res.users",
                ...urlParams,
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
     * Handle the notification of a new message based on the notification setting of the user.
     * Thread on mute:
     * 1. No longer see the unread status: the bold text disappears and the channel name fades out.
     * 2. Without sound + need action counter.

     * Thread Notification Type:
     * All messages:All messages sound + need action counter
     * Mentions:Only mention sounds + need action counter
     * Nothing: No sound + need action counter

     * @param {Thread} thread
     * @param {Message} message
     */
    notifyMessageToUser(thread, message) {
        let notify = thread.type !== "channel";
        if (thread.type === "channel" && message.recipients?.includes(this.store.user)) {
            notify = true;
        }
        if (
            thread.chatPartner?.eq(this.store.odoobot) ||
            thread.muteUntilDateTime ||
            thread.custom_notifications === "no_notif" ||
            (thread.custom_notifications === "mentions" &&
                !message.recipients?.includes(this.store.user))
        ) {
            return;
        }
        if (notify) {
            this.store.ChatWindow.insert({ thread });
            this.outOfFocusService.notify(message, thread);
        }
    }

    /**
     * Following a load more or load around, listing of messages contains persistent messages.
     * Transient messages are missing, so this function puts known transient messages at the
     * right place in message list of thread.
     *
     * @param {import("models").Thread} thread
     */
    _enrichMessagesWithTransient(thread) {
        for (const message of thread.transientMessages) {
            if (message.id < thread.oldestPersistentMessage && !thread.loadOlder) {
                thread.messages.unshift(message);
            } else if (message.id > thread.newestPersistentMessage && !thread.loadNewer) {
                thread.messages.push(message);
            } else {
                let afterIndex = thread.messages.findIndex((msg) => msg.id > message.id);
                if (afterIndex === -1) {
                    afterIndex = thread.messages.length + 1;
                }
                thread.messages.splice(afterIndex - 1, 0, message);
            }
        }
    }

    /**
     * @param {string} searchTerm
     * @param {Thread} thread
     * @param {number|false} [before]
     */
    async search(searchTerm, thread, before = false) {
        const { messages, count } = await this.rpc(this.getFetchRoute(thread), {
            ...this.getFetchParams(thread),
            search_term: await prettifyMessageContent(searchTerm), // formatted like message_post
            before,
        });
        return {
            count,
            loadMore: messages.length === FETCH_LIMIT,
            messages: this.store.Message.insert(messages, { html: true }),
        };
    }
}

export const threadService = {
    dependencies: [
        "mail.store",
        "orm",
        "rpc",
        "notification",
        "router",
        "mail.message",
        "mail.persona",
        "mail.out_of_focus",
        "ui",
        "user",
    ],
    /**
     * @param {import("@web/env").OdooEnv} env
     * @param {Partial<import("services").Services>} services
     */
    start(env, services) {
        return new ThreadService(env, services);
    },
};

registry.category("services").add("mail.thread", threadService);
