/** @odoo-module */

import { Message } from "./message_model";
import { removeFromArrayWithPredicate } from "../utils/arrays";
import { convertBrToLineBreak, prettifyMessageContent } from "../utils/format";
import { registry } from "@web/core/registry";
import { MessageReactions } from "./message_reactions_model";
import { Notification } from "./notification_model";
import { LinkPreview } from "./link_preview_model";
import { NotificationGroup } from "./notification_group_model";
import { assignDefined, createLocalId } from "../utils/misc";

const { DateTime } = luxon;

export class MessageService {
    constructor(env, services) {
        this.env = env;
        /** @type {import("@mail/core/store_service").Store} */
        this.store = services["mail.store"];
        this.rpc = services.rpc;
        this.orm = services.orm;
        this.userService = services.user;
        /** @type {import("@mail/core/persona_service").PersonaService} */
        this.personaService = services["mail.persona"];
        /** @type {import("@mail/attachments/attachment_service").AttachmentService} */
        this.attachmentService = services["mail.attachment"];
    }

    async edit(message, body, attachments = [], rawMentions) {
        if (convertBrToLineBreak(message.body) === body && attachments.length === 0) {
            return;
        }
        const validMentions = this.getMentionsFromText(rawMentions, body);
        await this.rpc("/mail/message/update_content", {
            attachment_ids: attachments
                .map(({ id }) => id)
                .concat(message.attachments.map(({ id }) => id)),
            body: await prettifyMessageContent(body, validMentions),
            message_id: message.id,
        });
        if (!message.isEmpty && this.store.hasLinkPreviewFeature) {
            this.rpc(
                "/mail/link_preview",
                { message_id: message.id, clear: true },
                { silent: true }
            );
        }
    }

    async delete(message) {
        if (message.isStarred) {
            this.store.discuss.starred.counter--;
            removeFromArrayWithPredicate(
                this.store.discuss.starred.messages,
                ({ id }) => id === message.id
            );
        }
        message.body = "";
        message.attachments = [];
        await this.rpc("/mail/message/update_content", {
            attachment_ids: [],
            body: "",
            message_id: message.id,
        });
    }

    /**
     * @returns {number}
     */
    getLastMessageId() {
        return Object.values(this.store.messages).reduce(
            (lastMessageId, message) => Math.max(lastMessageId, message.id),
            0
        );
    }

    getMentionsFromText(rawMentions, body) {
        if (!this.store.user) {
            // mentions are not supported for guests
            return {};
        }
        const validMentions = {};
        const partners = [];
        const threads = [];
        const rawMentionedPartnerIds = rawMentions.partnerIds || [];
        const rawMentionedThreadIds = rawMentions.threadIds || [];
        for (const partnerId of rawMentionedPartnerIds) {
            const partner = this.store.personas[createLocalId("partner", partnerId)];
            const index = body.indexOf(`@${partner.name}`);
            if (index === -1) {
                continue;
            }
            partners.push(partner);
        }
        for (const threadId of rawMentionedThreadIds) {
            const thread = this.store.threads[createLocalId("discuss.channel", threadId)];
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

    /**
     * Create a transient message, i.e. a message which does not come
     * from a member of the channel. Usually a log message, such as one
     * generated from a command with ('/').
     *
     * @param {Object} data
     */
    createTransient(data) {
        const { body, res_id, model } = data;
        const lastMessageId = this.getLastMessageId();
        return this.insert({
            author: this.store.odoobot,
            body,
            id: lastMessageId + 0.01,
            is_note: true,
            is_transient: true,
            res_id,
            model,
        });
    }

    async toggleStar(message) {
        await this.orm.silent.call("mail.message", "toggle_message_starred", [[message.id]]);
    }

    async setDone(message) {
        await this.orm.silent.call("mail.message", "set_message_done", [[message.id]]);
    }

    setPin(message, pinned) {
        return this.orm.call("discuss.channel", "set_message_pin", [message.originThread.id], {
            message_id: message.id,
            pinned,
        });
    }

    async unstarAll() {
        // apply the change immediately for faster feedback
        this.store.discuss.starred.counter = 0;
        this.store.discuss.starred.messages = [];
        await this.orm.call("mail.message", "unstar_all");
    }

    async react(message, content) {
        await this.rpc(
            "/mail/message/reaction",
            {
                action: "add",
                content,
                message_id: message.id,
            },
            { silent: true }
        );
    }

    async removeReaction(reaction) {
        await this.rpc(
            "/mail/message/reaction",
            {
                action: "remove",
                content: reaction.content,
                message_id: reaction.messageId,
            },
            { silent: true }
        );
    }

    updateStarred(message, isStarred) {
        message.isStarred = isStarred;
        const starred = this.store.discuss.starred;
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

    /**
     * @param {Object} data
     * @returns {Message}
     */
    insert(data) {
        let message;
        if (data.res_id) {
            // FIXME this prevents cyclic dependencies between mail.thread and mail.message
            this.env.bus.trigger("MESSAGE-SERVICE:INSERT_THREAD", {
                model: data.model,
                id: data.res_id,
            });
        }
        if (data.id in this.store.messages) {
            message = this.store.messages[data.id];
        } else {
            message = new Message();
            message._store = this.store;
            message = this.store.messages[data.id] = message;
        }
        this.update(message, data);
        this.updateNotifications(message);
        // return reactive version
        return message;
    }

    /**
     * @param {import("@mail/core/message_model").Message} message
     * @param {Object} data
     */
    update(message, data) {
        if (message.pinned_at && data.pinned_at === false) {
            removeFromArrayWithPredicate(
                message.originThread.pinnedMessages,
                ({ id }) => id === message.id
            );
        }
        const {
            attachment_ids: attachments = message.attachments,
            default_subject: defaultSubject = message.defaultSubject,
            is_discussion: isDiscussion = message.isDiscussion,
            is_note: isNote = message.isNote,
            is_transient: isTransient = message.isTransient,
            linkPreviews = message.linkPreviews,
            message_type: type = message.type,
            model: resModel = message.resModel,
            res_id: resId = message.resId,
            subtype_description: subtypeDescription = message.subtypeDescription,
            ...remainingData
        } = data;
        assignDefined(message, remainingData);
        assignDefined(message, {
            attachments: attachments.map((attachment) =>
                this.attachmentService.insert({ message, ...attachment })
            ),
            defaultSubject,
            isDiscussion,
            isNote,
            isStarred: this.store.user
                ? message.starred_partner_ids.includes(this.store.user.id)
                : false,
            isTransient,
            linkPreviews: linkPreviews.map((data) => new LinkPreview(data)),
            parentMessage: message.parentMessage ? this.insert(message.parentMessage) : undefined,
            resId,
            resModel,
            subtypeDescription,
            type,
        });
        if (
            Array.isArray(message.author) &&
            message.author.some((command) => command.includes("clear"))
        ) {
            message.author = undefined;
        }
        if (data.author?.id) {
            message.author = this.personaService.insert({
                ...data.author,
                type: "partner",
            });
        }
        if (data.guestAuthor?.id) {
            message.author = this.personaService.insert({
                ...data.guestAuthor,
                type: "guest",
                channelId: message.originThread.id,
            });
        }
        if (data.recipients) {
            message.recipients = data.recipients.map((recipient) =>
                this.personaService.insert({ ...recipient, type: "partner" })
            );
        }
        if (data.record_name) {
            message.originThread.name = data.record_name;
        }
        if (data.res_model_name) {
            message.originThread.modelName = data.res_model_name;
        }
        this._updateReactions(message, data.messageReactionGroups);
        if (message.isNotification && !message.notificationType) {
            const parser = new DOMParser();
            const htmlBody = parser.parseFromString(message.body, "text/html");
            message.notificationType =
                htmlBody.querySelector(".o_mail_notification")?.dataset.oeType;
        }
    }

    updateNotifications(message) {
        message.notifications = message.notifications.map((notification) =>
            this.insertNotification({ ...notification, messageId: message.id })
        );
    }

    _updateReactions(message, reactionGroups = []) {
        const reactionContentToUnlink = new Set();
        const reactionsToInsert = [];
        for (const rawReaction of reactionGroups) {
            const [command, reactionData] = Array.isArray(rawReaction)
                ? rawReaction
                : ["insert", rawReaction];
            const reaction = this.insertReactions(reactionData);
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

    /**
     * @param {Object} data
     * @returns {MessageReactions}
     */
    insertReactions(data) {
        let reaction = this.store.messages[data.message.id]?.reactions.find(
            ({ content }) => content === data.content
        );
        if (!reaction) {
            reaction = new MessageReactions();
            reaction._store = this.store;
        }
        const personasToUnlink = new Set();
        const alreadyKnownPersonaIds = new Set(reaction.personaLocalIds);
        for (const rawPartner of data.partners) {
            const [command, partnerData] = Array.isArray(rawPartner)
                ? rawPartner
                : ["insert", rawPartner];
            const persona = this.personaService.insert({ ...partnerData, type: "partner" });
            if (command === "insert" && !alreadyKnownPersonaIds.has(persona.localId)) {
                reaction.personaLocalIds.push(persona.localId);
            } else if (command !== "insert") {
                personasToUnlink.add(persona.localId);
            }
        }
        for (const rawGuest of data.guests) {
            const [command, guestData] = Array.isArray(rawGuest) ? rawGuest : ["insert", rawGuest];
            const persona = this.personaService.insert({ ...guestData, type: "guest" });
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

    /**
     * @param {Object} data
     * @returns {Notification}
     */
    insertNotification(data) {
        let notification;
        if (data.id in this.store.notifications) {
            notification = this.store.notifications[data.id];
            this.updateNotification(notification, data);
            return notification;
        }
        notification = new Notification(this.store, data);
        this.updateNotification(notification, data);
        // return reactive version
        return this.store.notifications[data.id];
    }

    updateNotification(notification, data) {
        Object.assign(notification, {
            messageId: data.messageId,
            notification_status: data.notification_status,
            notification_type: data.notification_type,
            failure_type: data.failure_type,
            persona: data.res_partner_id
                ? this.personaService.insert({
                      id: data.res_partner_id[0],
                      displayName: data.res_partner_id[1],
                      type: "partner",
                  })
                : undefined,
        });
        if (notification.message.author !== this.store.self) {
            return;
        }
        const thread = notification.message.originThread;
        this.insertNotificationGroups({
            modelName: thread?.modelName,
            resId: thread?.id,
            resModel: thread?.model,
            status: notification.notification_status,
            type: notification.notification_type,
            notifications: [
                [notification.isFailure ? "insert" : "insert-and-unlink", notification],
            ],
        });
    }

    insertNotificationGroups(data) {
        let group = this.store.notificationGroups.find((group) => {
            return (
                group.resModel === data.resModel &&
                group.type === data.type &&
                (group.resModel !== "discuss.channel" || group.resIds.has(data.resId))
            );
        });
        if (!group) {
            group = new NotificationGroup(this.store);
        }
        this.updateNotificationGroup(group, data);
        if (group.notifications.length === 0) {
            removeFromArrayWithPredicate(this.store.notificationGroups, (gr) => gr.id === group.id);
        }
        return group;
    }

    updateNotificationGroup(group, data) {
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
        group.notifications = group.notifications.filter(
            ({ id }) => !notificationIdsToRemove.has(id)
        );
        group.lastMessageId = group.notifications[0]?.message.id;
        for (const notification of group.notifications) {
            if (group.lastMessageId < notification.message.id) {
                group.lastMessageId = notification.message.id;
            }
        }
        group.resIds.add(data.resId);
    }

    scheduledDateSimple(message) {
        return message.scheduledDate.toLocaleString(DateTime.TIME_SIMPLE, {
            locale: this.userService.lang.replace("_", "-"),
        });
    }

    dateSimple(message) {
        return message.datetime.toLocaleString(DateTime.TIME_SIMPLE, {
            locale: this.userService.lang.replace("_", "-"),
        });
    }
}

export const messageService = {
    dependencies: ["mail.store", "rpc", "orm", "user", "mail.persona", "mail.attachment"],
    start(env, services) {
        return new MessageService(env, services);
    },
};

registry.category("services").add("mail.message", messageService);
