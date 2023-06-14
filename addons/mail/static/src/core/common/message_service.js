/* @odoo-module */

import { LinkPreview } from "@mail/core/common/link_preview_model";
import { Message } from "@mail/core/common/message_model";
import { MessageReactions } from "@mail/core/common/message_reactions_model";
import { NotificationGroup } from "@mail/core/common/notification_group_model";
import { Notification } from "@mail/core/common/notification_model";
import { removeFromArrayWithPredicate, replaceArrayWithCompare } from "@mail/utils/common/arrays";
import { convertBrToLineBreak, prettifyMessageContent } from "@mail/utils/common/format";
import { assignDefined, createLocalId } from "@mail/utils/common/misc";

import { registry } from "@web/core/registry";
import { makeFnPatchable } from "@mail/utils/common/patch";
import { insertAttachment } from "@mail/core/common/attachment_service";
import { insertPersona } from "@mail/core/common/persona_service";

const { DateTime } = luxon;

let gEnv;
let orm;
let rpc;
/** @type {import("@mail/core/common/store_service").Store} */
let store;
let userService;

/**
 * Create a transient message, i.e. a message which does not come
 * from a member of the channel. Usually a log message, such as one
 * generated from a command with ('/').
 *
 * @param {Object} data
 */
export function createTransientMessage(data) {
    const { body, res_id, model } = data;
    const lastMessageId = getLastMessageId();
    return insertMessage({
        author: store.odoobot,
        body,
        id: lastMessageId + 0.01,
        is_note: true,
        is_transient: true,
        res_id,
        model,
    });
}

export function dateSimpleOfMessage(message) {
    return message.datetime.toLocaleString(DateTime.TIME_SIMPLE, {
        locale: userService.lang?.replace("_", "-"),
    });
}

export async function deleteMessage(message) {
    if (message.isStarred) {
        store.discuss.starred.counter--;
        removeFromArrayWithPredicate(store.discuss.starred.messages, ({ id }) => id === message.id);
    }
    message.body = "";
    message.attachments = [];
    await rpc("/mail/message/update_content", {
        attachment_ids: [],
        body: "",
        message_id: message.id,
    });
}

export async function editMessage(message, body, attachments = [], rawMentions) {
    if (convertBrToLineBreak(message.body) === body && attachments.length === 0) {
        return;
    }
    const validMentions = getMentionsFromText(rawMentions, body);
    await rpc("/mail/message/update_content", {
        attachment_ids: attachments
            .map(({ id }) => id)
            .concat(message.attachments.map(({ id }) => id)),
        body: await prettifyMessageContent(body, validMentions),
        message_id: message.id,
    });
    if (!message.isEmpty && store.hasLinkPreviewFeature) {
        rpc("/mail/link_preview", { message_id: message.id, clear: true }, { silent: true });
    }
}

/**
 * @returns {number}
 */
function getLastMessageId() {
    return Object.values(store.messages).reduce(
        (lastMessageId, message) => Math.max(lastMessageId, message.id),
        0
    );
}

export function getMentionsFromText(rawMentions, body) {
    if (!store.user) {
        // mentions are not supported for guests
        return {};
    }
    const validMentions = {};
    const partners = [];
    const threads = [];
    const rawMentionedPartnerIds = rawMentions.partnerIds || [];
    const rawMentionedThreadIds = rawMentions.threadIds || [];
    for (const partnerId of rawMentionedPartnerIds) {
        const partner = store.personas[createLocalId("partner", partnerId)];
        const index = body.indexOf(`@${partner.name}`);
        if (index === -1) {
            continue;
        }
        partners.push(partner);
    }
    for (const threadId of rawMentionedThreadIds) {
        const thread = store.threads[createLocalId("discuss.channel", threadId)];
        const index = body.indexOf(`#${thread.displayName}`);
        if (index === -1) {
            continue;
        }
        threads.push(thread);
    }
    validMentions.partners = partners;
    validMentions.threads = threads;
    return validMentions;
}

export function getNextMessageTemporaryId() {
    return getLastMessageId() + 0.01;
}

/**
 * @param {Object} data
 * @returns {LinkPreview}
 */
function insertLinkPreview(data) {
    const linkPreview = data.message.linkPreviews.find((linkPreview) => linkPreview.id === data.id);
    if (linkPreview) {
        return Object.assign(linkPreview, data);
    }
    return new LinkPreview(data);
}

/**
 * @param {Object} data
 * @returns {Message}
 */
export const insertMessage = makeFnPatchable(function (data) {
    let message;
    if (data.res_id) {
        // this prevents cyclic dependencies between insertThread and mail.message
        gEnv.bus.trigger("mail.thread/insert", {
            model: data.model,
            id: data.res_id,
        });
    }
    if (data.id in store.messages) {
        message = store.messages[data.id];
    } else {
        message = new Message();
        message._store = store;
        store.messages[data.id] = message;
        message = store.messages[data.id];
    }
    updateMessage(message, data);
    // return reactive version
    return message;
});

/**
 * @param {Object} data
 * @returns {Notification}
 */
function insertNotification(data) {
    let notification = store.notifications[data.id];
    if (!notification) {
        store.notifications[data.id] = new Notification(store, data);
        notification = store.notifications[data.id];
    }
    updateNotification(notification, data);
    return notification;
}

function insertNotificationGroups(data) {
    let group = store.notificationGroups.find((group) => {
        return (
            group.resModel === data.resModel &&
            group.type === data.type &&
            (group.resModel !== "discuss.channel" || group.resIds.has(data.resId))
        );
    });
    if (!group) {
        group = new NotificationGroup(store);
    }
    updateNotificationGroup(group, data);
    if (group.notifications.length === 0) {
        removeFromArrayWithPredicate(store.notificationGroups, (gr) => gr.id === group.id);
    }
    return group;
}

/**
 * @param {Object} data
 * @returns {MessageReactions}
 */
function insertReactions(data) {
    let reaction = store.messages[data.message.id]?.reactions.find(
        ({ content }) => content === data.content
    );
    if (!reaction) {
        reaction = new MessageReactions();
        reaction._store = store;
    }
    const personasToUnlink = new Set();
    const alreadyKnownPersonaIds = new Set(reaction.personaLocalIds);
    for (const rawPartner of data.partners) {
        const [command, partnerData] = Array.isArray(rawPartner)
            ? rawPartner
            : ["insert", rawPartner];
        const persona = insertPersona({ ...partnerData, type: "partner" });
        if (command === "insert" && !alreadyKnownPersonaIds.has(persona.localId)) {
            reaction.personaLocalIds.push(persona.localId);
        } else if (command !== "insert") {
            personasToUnlink.add(persona.localId);
        }
    }
    for (const rawGuest of data.guests) {
        const [command, guestData] = Array.isArray(rawGuest) ? rawGuest : ["insert", rawGuest];
        const persona = insertPersona({ ...guestData, type: "guest" });
        if (command === "insert" && !alreadyKnownPersonaIds.has(persona.localId)) {
            reaction.personaLocalIds.push(persona.localId);
        } else if (command !== "insert") {
            personasToUnlink.add(persona.localId);
        }
    }
    Object.assign(reaction, {
        count: data.count,
        content: data.content,
        messageId: data.message.id,
        personaLocalIds: reaction.personaLocalIds.filter(
            (localId) => !personasToUnlink.has(localId)
        ),
    });
    return reaction;
}

export async function reactToMessage(message, content) {
    await rpc(
        "/mail/message/reaction",
        {
            action: "add",
            content,
            message_id: message.id,
        },
        { silent: true }
    );
}

export async function removeReaction(reaction) {
    await rpc(
        "/mail/message/reaction",
        {
            action: "remove",
            content: reaction.content,
            message_id: reaction.messageId,
        },
        { silent: true }
    );
}

export function scheduledDateSimple(message) {
    return message.scheduledDate.toLocaleString(DateTime.TIME_SIMPLE, {
        locale: userService.lang?.replace("_", "-"),
    });
}

export async function setMessageDone(message) {
    await orm.silent.call("mail.message", "set_message_done", [[message.id]]);
}

export async function toggleMessageStar(message) {
    await orm.silent.call("mail.message", "toggle_message_starred", [[message.id]]);
}

export async function unstarAllMessages() {
    // apply the change immediately for faster feedback
    store.discuss.starred.counter = 0;
    store.discuss.starred.messages = [];
    await orm.call("mail.message", "unstar_all");
}

/**
 * @param {import("@mail/core/common/message_model").Message} message
 * @param {Object} data
 */
export function updateMessage(message, data) {
    const {
        attachment_ids: attachments = message.attachments,
        default_subject: defaultSubject = message.defaultSubject,
        is_discussion: isDiscussion = message.isDiscussion,
        is_note: isNote = message.isNote,
        is_transient: isTransient = message.isTransient,
        linkPreviews = message.linkPreviews,
        message_type: type = message.type,
        model: resModel = message.resModel,
        module_icon,
        notifications = message.notifications,
        parentMessage,
        recipients = message.recipients,
        record_name,
        res_id: resId = message.resId,
        res_model_name,
        subtype_description: subtypeDescription = message.subtypeDescription,
        ...remainingData
    } = data;
    assignDefined(message, remainingData);
    assignDefined(message, {
        defaultSubject,
        isDiscussion,
        isNote,
        isStarred: store.user ? message.starred_partner_ids.includes(store.user.id) : false,
        isTransient,
        parentMessage: parentMessage ? insertMessage(parentMessage) : undefined,
        resId,
        resModel,
        subtypeDescription,
        type,
    });
    // origin thread before other information (in particular notification insert uses it)
    if (data.record_name) {
        message.originThread.name = data.record_name;
    }
    if (data.res_model_name) {
        message.originThread.modelName = data.res_model_name;
    }
    replaceArrayWithCompare(
        message.attachments,
        attachments.map((attachment) => insertAttachment({ message, ...attachment }))
    );
    if (message.originThread) {
        assignDefined(message.originThread, {
            modelName: res_model_name || undefined,
            module_icon: module_icon || undefined,
            name: record_name || undefined,
        });
    }
    if (data.author?.id) {
        message.author = insertPersona({
            ...data.author,
            type: "partner",
        });
    }
    if (data.guestAuthor?.id) {
        message.author = insertPersona({
            ...data.guestAuthor,
            type: "guest",
            channelId: message.originThread.id,
        });
    }
    replaceArrayWithCompare(
        message.linkPreviews,
        linkPreviews.map((data) => insertLinkPreview({ ...data, message }))
    );
    replaceArrayWithCompare(
        message.notifications,
        notifications.map((notification) =>
            insertNotification({ ...notification, messageId: message.id })
        )
    );
    replaceArrayWithCompare(
        message.recipients,
        recipients.map((recipient) => insertPersona({ ...recipient, type: "partner" }))
    );
    if ("user_follower_id" in data && data.user_follower_id && store.self) {
        // this prevents cyclic dependencies between message service and insertFollower
        gEnv.bus.trigger("core/web/thread_service.insertFollower", {
            followedThread: message.originThread,
            id: data.user_follower_id,
            isActive: true,
            partner: store.self,
        });
    }
    if (data.messageReactionGroups) {
        _updateReactions(message, data.messageReactionGroups);
    }
    if (message.isNotification && !message.notificationType) {
        const parser = new DOMParser();
        const htmlBody = parser.parseFromString(message.body, "text/html");
        message.notificationType = htmlBody.querySelector(".o_mail_notification")?.dataset.oeType;
    }
    gEnv.bus.trigger("mail.message/onUpdate", { message, data });
}

function updateNotification(notification, data) {
    Object.assign(notification, {
        messageId: data.messageId,
        notification_status: data.notification_status,
        notification_type: data.notification_type,
        failure_type: data.failure_type,
        persona: data.res_partner_id
            ? insertPersona({
                  id: data.res_partner_id[0],
                  displayName: data.res_partner_id[1],
                  type: "partner",
              })
            : undefined,
    });
    if (notification.message.author !== store.self) {
        return;
    }
    const thread = notification.message.originThread;
    insertNotificationGroups({
        modelName: thread?.modelName,
        resId: thread?.id,
        resModel: thread?.model,
        status: notification.notification_status,
        type: notification.notification_type,
        notifications: [[notification.isFailure ? "insert" : "insert-and-unlink", notification]],
    });
}

function updateNotificationGroup(group, data) {
    Object.assign(group, {
        modelName: data.modelName ?? group.modelName,
        resModel: data.resModel ?? group.resModel,
        type: data.type ?? group.type,
        status: data.status ?? group.status,
    });
    const notifications = data.notifications ?? [];
    const alreadyKnownNotifications = new Set(group.notifications.map(({ id }) => id));
    const notificationIdsToRemove = new Set();
    for (const [commandName, notification] of notifications) {
        if (commandName === "insert" && !alreadyKnownNotifications.has(notification.id)) {
            group.notifications.push(notification);
        } else if (commandName === "insert-and-unlink") {
            notificationIdsToRemove.add(notification.id);
        }
    }
    group.notifications = group.notifications.filter(({ id }) => !notificationIdsToRemove.has(id));
    group.lastMessageId = group.notifications[0]?.message.id;
    for (const notification of group.notifications) {
        if (group.lastMessageId < notification.message.id) {
            group.lastMessageId = notification.message.id;
        }
    }
    group.resIds.add(data.resId);
}

export function updateStarred(message, isStarred) {
    message.isStarred = isStarred;
    const starred = store.discuss.starred;
    if (isStarred) {
        starred.counter++;
        if (!starred.messages.includes(message)) {
            starred.messages.push(message);
        }
    } else {
        starred.counter--;
        removeFromArrayWithPredicate(starred.messages, ({ id }) => id === message.id);
    }
}

function _updateReactions(message, reactionGroups) {
    const reactionContentToUnlink = new Set();
    const reactionsToInsert = [];
    for (const rawReaction of reactionGroups) {
        const [command, reactionData] = Array.isArray(rawReaction)
            ? rawReaction
            : ["insert", rawReaction];
        const reaction = insertReactions(reactionData);
        if (command === "insert") {
            reactionsToInsert.push(reaction);
        } else {
            reactionContentToUnlink.add(reaction.content);
        }
    }
    message.reactions = message.reactions.filter(
        ({ content }) => !reactionContentToUnlink.has(content)
    );
    reactionsToInsert.forEach((reaction) => {
        const idx = message.reactions.findIndex(({ content }) => reaction.content === content);
        if (idx !== -1) {
            message.reactions[idx] = reaction;
        } else {
            message.reactions.push(reaction);
        }
    });
}

export class MessageService {
    constructor(env, services) {
        gEnv = env;
        store = services["mail.store"];
        rpc = services.rpc;
        orm = services.orm;
        userService = services.user;
    }
}

export const messageService = {
    dependencies: [
        "mail.store",
        "rpc",
        "orm",
        "user",
        "mail.persona",
        "mail.attachment",
        "notification",
    ],
    start(env, services) {
        return new MessageService(env, services);
    },
};

registry.category("services").add("mail.message", messageService);
