/** @odoo-module */

import { markup } from "@odoo/owl";
import { Message } from "./message_model";
import { removeFromArray } from "../utils/arrays";
import { convertBrToLineBreak, prettifyMessageContent } from "../utils/format";
import { registry } from "@web/core/registry";
import { MessageReactions } from "./message_reactions_model";
import { Notification } from "./notification_model";
import { LinkPreview } from "./link_preview_model";
import { NotificationGroup } from "./notification_group_model";
import { assignDefined, createLocalId } from "../utils/misc";

const commandRegistry = registry.category("mail.channel_commands");

export class MessageService {
    constructor(env, services) {
        this.env = env;
        /** @type {import("@mail/new/core/store_service").Store} */
        this.store = services["mail.store"];
        this.rpc = services.rpc;
        this.orm = services.orm;
        this.presence = services.presence;
        /** @type {import("@mail/new/core/persona_service").PersonaService} */
        this.persona = services["mail.persona"];
        /** @type {import("@mail/new/attachments/attachment_service").AttachmentService} */
        this.attachment = services["mail.attachment"];
    }

    async update(message, body, attachments = [], rawMentions) {
        if (convertBrToLineBreak(message.body) === body && attachments.length === 0) {
            return;
        }
        const validMentions = this.getMentionsFromText(rawMentions, body);
        const data = await this.rpc("/mail/message/update_content", {
            attachment_ids: attachments
                .map(({ id }) => id)
                .concat(message.attachments.map(({ id }) => id)),
            body: await prettifyMessageContent(body, validMentions),
            message_id: message.id,
        });
        message.body = markup(data.body);
        message.attachments.push(...attachments);
    }

    async delete(message) {
        if (message.isStarred) {
            this.store.discuss.starred.counter--;
            removeFromArray(this.store.discuss.starred.messageIds, message.id);
        }
        message.body = "";
        message.attachments = [];
        return this.rpc("/mail/message/update_content", {
            attachment_ids: [],
            body: "",
            message_id: message.id,
        });
    }

    getCommandFromText(thread, content) {
        if (content.startsWith("/")) {
            const firstWord = content.substring(1).split(/\s/)[0];
            const command = commandRegistry.get(firstWord, false);
            if (command) {
                return command.channel_types?.includes(thread.type) || thread.isChannel
                    ? command
                    : false;
            }
        }
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
            const thread = this.store.threads[createLocalId("mail.channel", threadId)];
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
        this.insert({
            author: this.store.partnerRoot,
            body,
            id: lastMessageId + 0.01,
            is_note: true,
            is_transient: true,
            res_id,
            model,
        });
    }

    async toggleStar(message) {
        await this.orm.call("mail.message", "toggle_message_starred", [[message.id]]);
    }

    async setDone(message) {
        await this.orm.call("mail.message", "set_message_done", [[message.id]]);
    }

    async unstarAll() {
        // apply the change immediately for faster feedback
        this.store.discuss.starred.counter = 0;
        this.store.discuss.starred.messageIds = [];
        await this.orm.call("mail.message", "unstar_all");
    }

    async react(message, content) {
        const messageData = await this.rpc("/mail/message/add_reaction", {
            content,
            message_id: message.id,
        });
        this.insert(messageData);
    }

    async removeReaction(reaction) {
        const messageData = await this.rpc("/mail/message/remove_reaction", {
            content: reaction.content,
            message_id: reaction.messageId,
        });
        this.insert(messageData);
    }

    updateStarred(message, isStarred) {
        message.isStarred = isStarred;
        if (isStarred) {
            this.store.discuss.starred.counter++;
            if (this.store.discuss.starred.messages.length > 0) {
                this.store.discuss.starred.messageIds.push(message.id);
            }
        } else {
            this.store.discuss.starred.counter--;
            removeFromArray(this.store.discuss.starred.messageIds, message.id);
        }
    }

    /**
     * @param {Object} data
     * @param {boolean} [fromFetch=false]
     * @returns {Message}
     */
    insert(data, fromFetch = false) {
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
        }
        this._update(message, data, fromFetch);
        this.store.messages[message.id] = message;
        this.updateNotifications(message);
        // return reactive version
        return this.store.messages[message.id];
    }

    /**
     * @param {import("@mail/new/core/message_model").Message} message
     * @param {Object} data
     * @param {boolean} [fromFetch=false]
     */
    _update(message, data, fromFetch = false) {
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
            attachments: attachments.map((attachment) => this.attachment.insert(attachment)),
            defaultSubject,
            isDiscussion,
            isNote,
            isStarred: message.starred_partner_ids.includes(this.store.self.id),
            isTransient,
            linkPreviews: linkPreviews.map((data) => new LinkPreview(data)),
            parentMessage: message.parentMessage ? this.insert(message.parentMessage) : undefined,
            resId,
            resModel,
            subtypeDescription,
            type,
        });
        if (data.author?.id) {
            message.author = this.persona.insert({
                ...data.author,
                type: "partner",
            });
        }
        if (data.guestAuthor?.id) {
            message.author = this.persona.insert({
                ...data.guestAuthor,
                type: "guest",
                channelId: message.originThread.id,
            });
        }
        if (data.recipients) {
            message.recipients = data.recipients.map((recipient) =>
                this.persona.insert({ ...recipient, type: "partner" })
            );
        }
        if (data.record_name) {
            message.originThread.name = data.record_name;
        }
        if (data.res_model_name) {
            message.originThread.modelName = data.res_model_name;
        }
        this._updateReactions(message, data.messageReactionGroups);
        this.store.messages[message.id] = message;
        if (message.originThread && !message.originThread.messages.includes(message)) {
            message.originThread.messageIds.push(message.id);
            this.sortMessages(message.originThread);
        }
        if (message.isNeedaction && !this.store.discuss.inbox.messages.includes(message)) {
            if (!fromFetch) {
                this.store.discuss.inbox.counter++;
                if (message.originThread) {
                    message.originThread.message_needaction_counter++;
                }
            }
            this.store.discuss.inbox.messageIds.push(message.id);
            this.sortMessages(this.store.discuss.inbox);
        }
        if (message.isStarred && !this.store.discuss.starred.messages.includes(message)) {
            this.store.discuss.starred.messageIds.push(message.id);
            this.sortMessages(this.store.discuss.starred);
        }
        if (message.isHistory && !this.store.discuss.history.messages.includes(message)) {
            this.store.discuss.history.messageIds.push(message.id);
            this.sortMessages(this.store.discuss.history);
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
            const persona = this.persona.insert({ ...partnerData, type: "partner" });
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
            partner: data.res_partner_id
                ? this.persona.insert({
                      id: data.res_partner_id[0],
                      name: data.res_partner_id[1],
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
                (group.resModel !== "mail.channel" || group.resIds.has(data.resId))
            );
        });
        if (!group) {
            group = new NotificationGroup(this.store);
        }
        this.updateNotificationGroup(group, data);
        if (group.notifications.length === 0) {
            removeFromArray(this.store.notificationGroups, group);
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

    /**
     * @param {import("@mail/new/core/thread_model").Thread} thread
     */
    sortMessages(thread) {
        thread.messageIds.sort((msgId1, msgId2) => {
            const msg1 = this.store.messages[msgId1];
            const msg2 = this.store.messages[msgId2];
            const indicator = msg1.datetime - msg2.datetime;
            if (indicator) {
                return indicator;
            } else {
                return msg1.id - msg2.id;
            }
        });
    }
}

export const messageService = {
    dependencies: ["mail.store", "rpc", "orm", "presence", "mail.persona", "mail.attachment"],
    start(env, services) {
        return new MessageService(env, services);
    },
};

registry.category("services").add("mail.message", messageService);
