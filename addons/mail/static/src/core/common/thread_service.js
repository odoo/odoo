/* @odoo-module */

import { insertAttachment } from "@mail/core/common/attachment_service";
import { insertChannelMember } from "@mail/core/common/channel_member_service";
import { Composer } from "@mail/core/common/composer_model";
import { loadEmoji } from "@mail/core/common/emoji_picker";
import {
    getMentionsFromText,
    getNextMessageTemporaryId,
    insertMessage,
} from "@mail/core/common/message_service";
import { DEFAULT_AVATAR, insertPersona } from "@mail/core/common/persona_service";
import { Thread } from "@mail/core/common/thread_model";
import {
    removeFromArray,
    removeFromArrayWithPredicate,
    replaceArrayWithCompare,
} from "@mail/utils/common/arrays";
import { prettifyMessageContent } from "@mail/utils/common/format";
import { assignDefined, createLocalId, onChange } from "@mail/utils/common/misc";
import { makeFnPatchable } from "@mail/utils/common/patch";

import { markup } from "@odoo/owl";

import { browser } from "@web/core/browser/browser";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { memoize } from "@web/core/utils/functions";
import { url } from "@web/core/utils/urls";

const FETCH_LIMIT = 30;

let gEnv;
let notificationService;
let orm;
let router;
let rpc;
/** @type {import("@mail/core/common/store_service").Store} */
let store;
let ui;

/**
 * @param {import("@mail/core/common/persona_model").Persona} persona
 * @param {import("@mail/core/common/thread_model").Thread} [thread]
 */
export const avatarUrl = makeFnPatchable(function (persona, thread) {
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
});

/**
 * @param {Thread} thread
 */
export const canLeaveThread = makeFnPatchable(function (thread) {
    return (
        ["channel", "group"].includes(thread.type) &&
        !thread.message_needaction_counter &&
        !thread.group_based_subscription
    );
});

/**
 * @param {Thread} thread
 */
export const canUnpinThread = makeFnPatchable(function (thread) {
    return thread.type === "chat" && getThreadCounter(thread) === 0;
});

/**
 * @param {import("@mail/core/common/composer_model").Composer} composer
 */
export function clearComposer(composer) {
    composer.attachments.length = 0;
    composer.textInputContent = "";
    Object.assign(composer.selection, {
        start: 0,
        end: 0,
        direction: "none",
    });
}

export async function createChannel(name) {
    const data = await orm.call("discuss.channel", "channel_create", [
        name,
        store.internalUserGroupId,
    ]);
    const channel = createChannelThread(data);
    sortChannels();
    openThread(channel);
}

export async function createGroupChat({ default_display_mode, partners_to }) {
    const data = await orm.call("discuss.channel", "create_group", [], {
        default_display_mode,
        partners_to,
    });
    const channel = createChannelThread(data);
    sortChannels();
    openThread(channel);
    return channel;
}

/**
 * todo: merge this with insertThread() (?)
 *
 * @returns {Thread}
 */
export function createChannelThread(serverData) {
    const thread = insertThread({
        ...serverData,
        model: "discuss.channel",
        type: serverData.channel.channel_type,
        isAdmin:
            serverData.channel.channel_type !== "group" &&
            serverData.create_uid === store.user?.user?.id,
    });
    return thread;
}

export function executeChannelCommand(thread, command, body = "") {
    return orm.call("discuss.channel", command.methodName, [[thread.id]], {
        body,
    });
}

export async function fetchChannelMembers(thread) {
    const known_member_ids = thread.channelMembers.map((channelMember) => channelMember.id);
    const results = await rpc("/discuss/channel/members", {
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
            insertChannelMember({ ...channelMember, threadId: thread.id });
        }
    }
}

/**
 * @param {Thread} thread
 * @param {{after: Number, before: Number}}
 */
async function fetchMessages(thread, { after, before } = {}) {
    thread.status = "loading";
    if (thread.type === "chatter" && !thread.id) {
        return [];
    }
    try {
        // ordered messages received: newest to oldest
        const rawMessages = await rpc(getFetchRoute(thread), {
            ...getFetchParams(thread),
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
            return insertMessage(
                Object.assign(data, { body: data.body ? markup(data.body) : data.body })
            );
        });
        updateThread(thread, { isLoaded: true });
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
 * @param {"older"|"newer"} epoch
 */
export async function fetchMoreMessages(thread, epoch = "older") {
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
        const fetched = await fetchMessages(thread, { after, before });
        if (
            (after !== undefined && !thread.messages.some((message) => message.id === after)) ||
            (before !== undefined && !thread.messages.some((message) => message.id === before))
        ) {
            // there might have been a jump to message during RPC fetch.
            // Abort feeding messages as to not put holes in message list.
            return;
        }
        const alreadyKnownMessages = new Set(thread.messages.map(({ id }) => id));
        const messagesToAdd = fetched.filter((message) => !alreadyKnownMessages.has(message.id));
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
        _enrichMessagesWithTransient(thread);
    } catch {
        // handled in fetchMessages
    }
    thread.pendingNewMessages = [];
}

// This function is like fetchNewMessages but just for a single message at most on all pinned threads
export const fetchPreviews = memoize(async () => {
    const ids = [];
    for (const thread of Object.values(store.threads)) {
        if (["channel", "group", "chat"].includes(thread.type)) {
            ids.push(thread.id);
        }
    }
    if (ids.length) {
        const previews = await orm.call("discuss.channel", "channel_fetch_preview", [ids]);
        for (const preview of previews) {
            const thread = store.threads[createLocalId("discuss.channel", preview.id)];
            const data = Object.assign(preview.last_message, {
                body: markup(preview.last_message.body),
            });
            const message = insertMessage({
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
 */
export const fetchNewMessages = makeFnPatchable(async function (thread) {
    if (
        thread.status === "loading" ||
        (thread.isLoaded && ["discuss.channel", "mail.box"].includes(thread.model))
    ) {
        return;
    }
    const after = thread.isLoaded ? thread.newestPersistentMessage?.id : undefined;
    try {
        const fetched = await fetchMessages(thread, { after });
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
        if (thread === store.discuss.inbox) {
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
});

export const getChat = makeFnPatchable(async function ({ userId, partnerId }) {
    if (userId) {
        let user = store.users[userId];
        if (!user) {
            store.users[userId] = { id: userId };
            user = store.users[userId];
        }
        if (!user.partner_id) {
            const [userData] = await orm.silent.read("res.users", [user.id], ["partner_id"], {
                context: { active_test: false },
            });
            if (userData) {
                user.partner_id = userData.partner_id[0];
            }
        }
        if (!user.partner_id) {
            notificationService.add(_t("You can only chat with existing users."), {
                type: "warning",
            });
            return;
        }
        partnerId = user.partner_id;
    }
    if (partnerId) {
        const partner = insertPersona({ id: partnerId, type: "partner" });
        if (!partner.user) {
            const [userId] = await orm.silent.search(
                "res.users",
                [["partner_id", "=", partnerId]],
                { context: { active_test: false } }
            );
            if (!userId) {
                notificationService.add(
                    _t("You can only chat with partners that have a dedicated user."),
                    { type: "info" }
                );
                return;
            }
            partner.user = { id: userId };
        }
    }
    let chat = Object.values(store.threads).find(
        (thread) => thread.type === "chat" && thread.chatPartnerId === partnerId
    );
    if (!chat || !chat.is_pinned) {
        chat = await joinChat(partnerId);
    }
    if (!chat) {
        notificationService.add(
            _t("An unexpected error occurred during the creation of the chat."),
            { type: "warning" }
        );
        return;
    }
    return chat;
});

export function getDiscussCategoryCounter(categoryId) {
    return store.discuss[categoryId].threads.reduce((acc, threadLocalId) => {
        const channel = store.threads[threadLocalId];
        if (categoryId === "channels") {
            return channel.message_needaction_counter > 0 ? acc + 1 : acc;
        } else {
            return channel.message_unread_counter > 0 ? acc + 1 : acc;
        }
    }, 0);
}

/**
 * @param {Thread} thread
 */
export const getMessagePostRoute = makeFnPatchable(function (thread) {
    return "/mail/message/post";
});

function getFetchParams(thread) {
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

function getFetchRoute(thread) {
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

/**
 * Get the parameters to pass to the message post route.
 */
export const getMessagePostParams = makeFnPatchable(async function ({
    attachments,
    body,
    isNote,
    rawMentions,
    thread,
}) {
    const subtype = isNote ? "mail.mt_note" : "mail.mt_comment";
    const validMentions = store.user ? getMentionsFromText(rawMentions, body) : undefined;
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
            message_type: "comment",
            partner_ids,
            subtype_xmlid: subtype,
        },
        thread_id: thread.id,
        thread_model: thread.model,
    };
});

/**
 * @param {Thread} thread
 */
export const getThreadCounter = makeFnPatchable(function (thread) {
    if (thread.type === "mailbox") {
        return thread.counter;
    }
    if (thread.type === "chat" || thread.type === "group") {
        return thread.message_unread_counter || thread.message_needaction_counter;
    }
    return thread.message_needaction_counter;
});

/**
 * @param {Object} data
 * @returns {Composer}
 */
export function insertComposer(data) {
    const { message, thread } = data;
    if (Boolean(message) === Boolean(thread)) {
        throw new Error("Composer shall have a thread xor a message.");
    }
    let composer = (thread ?? message)?.composer;
    if (!composer) {
        composer = new Composer(store, data);
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
 * @param {Object} data
 * @returns {Thread}
 */
export const insertThread = makeFnPatchable(function (data) {
    if (!("id" in data)) {
        throw new Error("Cannot insert thread: id is missing in data");
    }
    if (!("model" in data)) {
        throw new Error("Cannot insert thread: model is missing in data");
    }
    const localId = createLocalId(data.model, data.id);
    if (localId in store.threads) {
        const thread = store.threads[localId];
        updateThread(thread, data);
        return thread;
    }
    const thread = new Thread(store, data);
    onChange(thread, "message_unread_counter", () => {
        if (thread.channel) {
            thread.channel.message_unread_counter = thread.message_unread_counter;
        }
    });
    onChange(thread, "isLoaded", () => thread.isLoadedDeferred.resolve());
    onChange(thread, "channelMembers", () => store.updateBusSubscription());
    onChange(thread, "is_pinned", () => {
        if (!thread.is_pinned && store.discuss.threadLocalId === thread.localId) {
            store.discuss.threadLocalId = null;
        }
    });
    updateThread(thread, data);
    insertComposer({ thread });
    // return reactive version.
    return store.threads[thread.localId];
});

export async function joinChannel(id, name) {
    await orm.call("discuss.channel", "add_members", [[id]], {
        partner_ids: [store.user.id],
    });
    const thread = insertThread({
        id,
        model: "discuss.channel",
        name,
        type: "channel",
        channel: { avatarCacheKey: "hello" },
    });
    sortChannels();
    openThread(thread);
    return thread;
}

export async function joinChat(id) {
    const data = await orm.call("discuss.channel", "channel_get", [], {
        partners_to: [id],
    });
    return insertThread({
        ...data,
        model: "discuss.channel",
        type: "chat",
    });
}

export async function leaveChannel(channel) {
    await orm.call("discuss.channel", "action_unfollow", [channel.id]);
    removeThread(channel);
    setDiscussThread(
        store.discuss.channels.threads[0]
            ? store.threads[store.discuss.channels.threads[0]]
            : store.discuss.inbox
    );
}

/**
 * Get ready to jump to a message in a thread. This method will fetch the
 * messages around the message to jump to if required, and update the thread
 * messages accordingly.
 *
 * @param {Message} [messageId] if not provided, load around newest message
 */
export const loadAround = makeFnPatchable(async function (thread, messageId) {
    if (!thread.messages.some(({ id }) => id === messageId)) {
        const messages = await rpc(getFetchRoute(thread), {
            ...getFetchParams(thread),
            around: messageId,
        });
        thread.messages = messages.reverse().map((message) => {
            if (message.parentMessage?.body) {
                message.parentMessage.body = markup(message.parentMessage.body);
            }
            return insertMessage({
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
        _enrichMessagesWithTransient(thread);
        // Give some time to the UI to update.
        await new Promise((resolve) => setTimeout(() => requestAnimationFrame(resolve)));
    }
});

export async function markAllMessagesAsRead(thread) {
    await orm.silent.call("mail.message", "mark_all_as_read", [
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
export async function markThreadAsFetched(thread) {
    await orm.silent.call("discuss.channel", "channel_fetched", [[thread.id]]);
}

/**
 * @param {Thread} thread
 */
export async function markThreadAsRead(thread) {
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
        rpc("/discuss/channel/set_last_seen_message", {
            channel_id: thread.id,
            last_message_id: newestPersistentMessage.id,
        }).then(() => {
            updateThreadSeen(thread, newestPersistentMessage.id);
        });
    } else if (newestPersistentMessage) {
        updateThreadSeen(thread);
    }
    if (thread.hasNeedactionMessages) {
        markAllMessagesAsRead(thread);
    }
}

/**
 * @param {number} threadId
 * @param {string} data base64 representation of the binary
 */
export async function notifyThreadAvatarToServer(threadId, data) {
    await rpc("/discuss/channel/update_avatar", {
        channel_id: threadId,
        data,
    });
}

export async function notifyThreadDescriptionToServer(thread, description) {
    thread.description = description;
    return orm.call("discuss.channel", "channel_change_description", [[thread.id]], {
        description,
    });
}

export async function notifyThreadNameToServer(thread, name) {
    if (thread.type === "channel" || thread.type === "group") {
        thread.name = name;
        await orm.call("discuss.channel", "channel_rename", [[thread.id]], { name });
    } else if (thread.type === "chat") {
        thread.customName = name;
        await orm.call("discuss.channel", "channel_set_custom_name", [[thread.id]], {
            name,
        });
    }
}

export const openChat = makeFnPatchable(async function (person) {
    const chat = await getChat(person);
    if (chat) {
        openThread(chat);
    }
});

/**
 * @param {Thread} thread
 * @param {boolean} replaceNewMessageChatWindow
 */
export const openThread = makeFnPatchable(function (thread, replaceNewMessageChatWindow) {
    setDiscussThread(thread);
});

export function pinThread(thread) {
    if (thread.model !== "discuss.channel" || !store.user) {
        return;
    }
    thread.is_pinned = true;
    return orm.silent.call("discuss.channel", "channel_pin", [thread.id], {
        pinned: true,
    });
}

export function unpinThread(thread) {
    if (thread.model !== "discuss.channel") {
        return;
    }
    return orm.silent.call("discuss.channel", "channel_pin", [thread.id], {
        pinned: false,
    });
}

/**
 * @param {Thread} thread
 * @param {string} body
 */
export const postMessage = makeFnPatchable(async function (
    thread,
    body,
    { attachments = [], isNote = false, parentId, rawMentions }
) {
    let tmpMsg;
    const params = await getMessagePostParams({
        attachments,
        body,
        isNote,
        rawMentions,
        thread,
    });
    const tmpId = getNextMessageTemporaryId();
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
        if (store.user) {
            tmpData.author = store.self;
        }
        if (store.guest) {
            tmpData.guestAuthor = store.self;
        }
        if (parentId) {
            tmpData.parentMessage = store.messages[parentId];
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
        tmpMsg = insertMessage({
            ...tmpData,
            body: markup(prettyContent),
            res_id: thread.id,
            model: thread.model,
            temporary_id: tmpId,
        });
        thread.messages.push(tmpMsg);
        thread.seen_message_id = tmpMsg.id;
    }
    const data = await rpc(getMessagePostRoute(thread), params);
    if (thread.type !== "chatter") {
        removeFromArrayWithPredicate(thread.messages, ({ id }) => id === tmpMsg.id);
        delete store.messages[tmpMsg.id];
    }
    if (!data) {
        return;
    }
    if (data.parentMessage) {
        data.parentMessage.body = data.parentMessage.body
            ? markup(data.parentMessage.body)
            : data.parentMessage.body;
    }
    if (data.id in store.messages) {
        data.temporary_id = null;
    }
    const message = insertMessage(Object.assign(data, { body: markup(data.body) }));
    if (!thread.messages.some(({ id }) => id === message.id)) {
        thread.messages.push(message);
    }
    if (!message.isEmpty && store.hasLinkPreviewFeature) {
        rpc("/mail/link_preview", { message_id: data.id }, { silent: true });
    }
    return message;
});

export const removeThread = makeFnPatchable(function (thread) {
    removeFromArray(store.discuss.chats.threads, thread.localId);
    removeFromArray(store.discuss.channels.threads, thread.localId);
    delete store.threads[thread.localId];
});

/**
 * @param {import("@mail/core/common/thread_model").Thread} thread
 * @param {boolean} pushState
 */
export const setDiscussThread = makeFnPatchable(function (thread, pushState = true) {
    store.discuss.threadLocalId = thread.localId;
    const activeId =
        typeof thread.id === "string" ? `mail.box_${thread.id}` : `discuss.channel_${thread.id}`;
    store.discuss.activeTab = !ui.isSmall
        ? "all"
        : thread.model === "mail.box"
        ? "mailbox"
        : ["chat", "group"].includes(thread.type)
        ? "chat"
        : "channel";
    if (pushState) {
        router.pushState({ active_id: activeId });
    }
});

/**
 * @param {import("@mail/core/common/thread_model").Thread} thread
 * @param {number} index
 */
export const setMainAttachmentFromIndex = async function (thread, index) {
    thread.mainAttachment = thread.attachmentsInWebClientView[index];
    await orm.call("ir.attachment", "register_as_main_attachment", [thread.mainAttachment.id]);
};

export const sortChannels = makeFnPatchable(function () {
    store.discuss.channels.threads.sort((id1, id2) => {
        const thread1 = store.threads[id1];
        const thread2 = store.threads[id2];
        return String.prototype.localeCompare.call(thread1.name, thread2.name);
    });
    store.discuss.chats.threads.sort((localId_1, localId_2) => {
        const thread1 = store.threads[localId_1];
        const thread2 = store.threads[localId_2];
        return thread2.lastInterestDateTime.ts - thread1.lastInterestDateTime.ts;
    });
});

/**
 * @param {import("@mail/core/common/thread_model").Thread} thread
 * @param {Object} data
 */
export const updateThread = makeFnPatchable(function (thread, data) {
    const { id, name, attachments: attachmentsData, description, ...serverData } = data;
    assignDefined(thread, { id, name, description });
    if (attachmentsData) {
        replaceArrayWithCompare(
            thread.attachments,
            attachmentsData.map((attachmentData) => insertAttachment(attachmentData))
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
                    const member = insertChannelMember([command, memberData]);
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
                            const record = insertChannelMember(member);
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
                            ? insertMessage({ id: fetched_message_id })
                            : undefined,
                        lastSeenMessage: seen_message_id
                            ? insertMessage({ id: seen_message_id })
                            : undefined,
                        partner: insertPersona({
                            id: partner_id,
                            type: "partner",
                        }),
                    };
                }
            );
        }
    }
    if (thread.type === "channel" && !store.discuss.channels.threads.includes(thread.localId)) {
        store.discuss.channels.threads.push(thread.localId);
    } else if (
        (thread.type === "chat" || thread.type === "group") &&
        !store.discuss.chats.threads.includes(thread.localId)
    ) {
        store.discuss.chats.threads.push(thread.localId);
    }
    if (!thread.type && !["mail.box", "discuss.channel"].includes(thread.model)) {
        thread.type = "chatter";
    }
    gEnv.bus.trigger("mail.thread/onUpdate", { thread, data });
});

export function updateThreadSeen(thread, lastSeenId = thread.newestPersistentMessage?.id) {
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
    updateThread(thread, {
        seen_message_id: lastSeenId,
        message_needaction_counter: newNeedactionCounter,
        message_unread_counter: newUnreadCounter,
    });
}

/**
 * Following a load more or load around, listing of messages contains persistent messages.
 * Transient messages are missing, so this function puts known transient messages at the
 * right place in message list of thread.
 *
 * @param {Thread} thread
 */
function _enrichMessagesWithTransient(thread) {
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

export class ThreadService {
    constructor(env, services) {
        this.setup(env, services);
    }

    setup(env, services) {
        gEnv = env;
        notificationService = services.notification;
        orm = services.orm;
        router = services.router;
        rpc = services.rpc;
        store = services["mail.store"];
        ui = services.ui;
        // this prevents cyclic dependencies between insertThread and other services
        gEnv.bus.addEventListener("mail.thread/insert", ({ detail }) => {
            const model = detail.model;
            const id = detail.id;
            const type = detail.type;
            insertThread({ model, id, type });
        });
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
