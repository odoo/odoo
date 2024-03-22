import { prettifyMessageContent } from "@mail/utils/common/format";
import { rpcWithEnv } from "@mail/utils/common/misc";

import { router } from "@web/core/browser/router";
import { _t } from "@web/core/l10n/translation";
/** @type {ReturnType<import("@mail/utils/common/misc").rpcWithEnv>} */
let rpc;
import { registry } from "@web/core/registry";
import { user } from "@web/core/user";
import { escape } from "@web/core/utils/strings";

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
        rpc = rpcWithEnv(env);
        this.env = env;
        this.store = services["mail.store"];
        this.orm = services.orm;
        this.notificationService = services.notification;
        this.ui = services.ui;
        this.messageService = services["mail.message"];
        this.personaService = services["mail.persona"];
        this.outOfFocusService = services["mail.out_of_focus"];
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
            results = await rpc("/discuss/channel/members", {
                channel_id: thread.id,
                known_member_ids: known_member_ids,
            });
        } catch (e) {
            thread.fetchMembersState = previousState;
            throw e;
        }
        thread.fetchMembersState = "fetched";
        thread.update(results);
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
        if (thread.selfMember) {
            thread.selfMember.seen_message_id = newestPersistentMessage;
        }
        if (
            thread.message_unread_counter > 0 &&
            thread.model === "discuss.channel" &&
            newestPersistentMessage
        ) {
            rpc("/discuss/channel/set_last_seen_message", {
                channel_id: thread.id,
                last_message_id: newestPersistentMessage.id,
            })
                .then(() => {
                    this.updateSeen(thread, newestPersistentMessage);
                })
                .catch((e) => {
                    if (e.code !== 404) {
                        throw e;
                    }
                });
        } else if (newestPersistentMessage) {
            this.updateSeen(thread);
        }
        if (thread.needactionMessages.length > 0) {
            this.markAllMessagesAsRead(thread);
        }
    }

    updateSeen(thread, lastSeen = thread.newestPersistentOfAllMessage) {
        const lastReadIndex = thread.messages.findIndex((message) => message.eq(lastSeen));
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
        if (thread.selfMember) {
            thread.selfMember.seen_message_id = lastSeen;
        }
        Object.assign(thread, {
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
        if (thread.selfMember) {
            thread.selfMember.seen_message_id = thread.newestPersistentNotEmptyOfAllMessage;
        }
        Object.assign(thread, {
            message_unread_counter: 0,
            message_needaction_counter: 0,
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
        if (thread.model === "mail.box") {
            return `/mail/${thread.id}/messages`;
        }
        return "/mail/thread/messages";
    }

    getFetchParams(thread) {
        if (thread.model === "discuss.channel") {
            return { channel_id: thread.id };
        }
        if (thread.model === "mail.box") {
            return {};
        }
        return {
            thread_id: thread.id,
            thread_model: thread.model,
        };
    }

    /**
     * @param {import("models").Thread} thread
     * @param {{after: Number, before: Number}}
     */
    async fetchMessages(thread, { after, before } = {}) {
        thread.status = "loading";
        if (!["mail.box", "discuss.channel"].includes(thread.model) && !thread.id) {
            thread.isLoaded = true;
            return [];
        }
        try {
            // ordered messages received: newest to oldest
            const { messages: rawMessages } = await rpc(this.getFetchRoute(thread), {
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
            const { messages } = await rpc(this.getFetchRoute(thread), {
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
            router.replaceState({ active_id: undefined });
        }
        if (thread.model === "discuss.channel" && thread.is_pinned) {
            return this.orm.silent.call("discuss.channel", "channel_pin", [thread.id], {
                pinned: false,
            });
        }
    }

    pin(thread) {
        if (thread.model !== "discuss.channel" || this.store.self.type !== "partner") {
            return;
        }
        thread.is_pinned = true;
        return this.orm.silent.call("discuss.channel", "channel_pin", [thread.id], {
            pinned: true,
        });
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
            if (!partner.userId) {
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
                partner.userId = userId;
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
            (thread) => thread.channel_type === "chat" && thread.correspondent?.eq(partner)
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
        await this.orm.call("discuss.channel", "add_members", [[id]], {
            partner_ids: [this.store.self.id],
        });
        const thread = this.store.Thread.insert({
            channel_type: "channel",
            id,
            model: "discuss.channel",
            name,
        });
        if (!thread.avatarCacheKey) {
            thread.avatarCacheKey = "hello";
        }
        this.open(thread);
        return thread;
    }

    async joinChat(id, forceOpen = false) {
        const data = await this.orm.call("discuss.channel", "channel_get", [], {
            partners_to: [id],
            force_open: forceOpen,
        });
        const thread = this.store.Thread.insert(data);
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
            ((newName && thread.channel_type === "channel") ||
                thread.channel_type === "chat" ||
                thread.channel_type === "group")
        ) {
            if (thread.channel_type === "channel" || thread.channel_type === "group") {
                thread.name = newName;
                await this.orm.call("discuss.channel", "channel_rename", [[thread.id]], {
                    name: newName,
                });
            } else if (thread.channel_type === "chat") {
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
                : ["chat", "group"].includes(thread.channel_type)
                ? "chat"
                : "channel";
        if (pushState) {
            router.pushState({ active_id: activeId });
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
        params.context = { ...user.context, ...params.context, temporary_id: tmpId };
        if (parentId) {
            params.post_data.parent_id = parentId;
        }
        if (thread.model !== "discuss.channel") {
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
            tmpMsg = this.store.Message.insert(
                {
                    ...tmpData,
                    body: prettyContent,
                    thread,
                    temporary_id: tmpId,
                },
                { html: true }
            );
            thread.messages.push(tmpMsg);
            if (thread.selfMember) {
                thread.selfMember.seen_message_id = tmpMsg;
            }
        }
        const data = await rpc("/mail/message/post", params);
        if (!data) {
            tmpMsg?.delete();
            return;
        }
        if (data.id in this.store.Message.records) {
            data.temporary_id = null;
        }
        const message = this.store.Message.insert(data, { html: true });
        thread.messages.add(message);
        if (thread.selfMember?.seen_message_id?.id < message.id) {
            thread.selfMember.seen_message_id = message;
        }
        // Only delete the temporary message now that seen_message_id is updated
        // to avoid flickering.
        tmpMsg?.delete();
        if (message.hasLink && this.store.hasLinkPreviewFeature) {
            rpc("/mail/link_preview", { message_id: data.id }, { silent: true });
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
        const validMentions =
            this.store.self.type === "partner"
                ? this.messageService.getMentionsFromText(body, {
                      mentionedChannels,
                      mentionedPartners,
                  })
                : undefined;
        const partner_ids = validMentions?.partners.map((partner) => partner.id) ?? [];
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
                    recipientAdditionalValues[recipient.email] = recipient.create_values;
                });
            partner_ids.push(...recipientIds);
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

    getDiscussSidebarCategoryCounter(categoryId) {
        return this.store.DiscussAppCategory.get({ id: categoryId }).threads.reduce(
            (acc, channel) => {
                if (categoryId === "channels") {
                    return channel.message_needaction_counter > 0 ? acc + 1 : acc;
                } else {
                    return channel.message_unread_counter > 0 ? acc + 1 : acc;
                }
            },
            0
        );
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
     * @param {number} threadId
     * @param {string} data base64 representation of the binary
     */
    async notifyThreadAvatarToServer(threadId, data) {
        await rpc("/discuss/channel/update_avatar", {
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
        let notify = thread.channel_type !== "channel";
        if (thread.channel_type === "channel" && message.recipients?.includes(this.store.self)) {
            notify = true;
        }
        if (
            thread.correspondent?.eq(this.store.odoobot) ||
            thread.mute_until_dt ||
            thread.custom_notifications === "no_notif" ||
            (thread.custom_notifications === "mentions" &&
                !message.recipients?.includes(this.store.self))
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
        const { messages, count } = await rpc(this.getFetchRoute(thread), {
            ...this.getFetchParams(thread),
            search_term: escape(searchTerm),
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
        "notification",
        "mail.message",
        "mail.persona",
        "mail.out_of_focus",
        "ui",
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
