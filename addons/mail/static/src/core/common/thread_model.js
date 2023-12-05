/* @odoo-module */

import { AND, Record } from "@mail/core/common/record";
import { ScrollPosition } from "@mail/core/common/scroll_position";
import { assignDefined, assignIn } from "@mail/utils/common/misc";

import { deserializeDateTime } from "@web/core/l10n/dates";
import { _t } from "@web/core/l10n/translation";
import { Deferred } from "@web/core/utils/concurrency";

/**
 * @typedef SuggestedRecipient
 * @property {string} email
 * @property {import("models").Persona|false} persona
 * @property {string} lang
 * @property {string} reason
 * @property {boolean} checked
 */

export class Thread extends Record {
    static id = AND("model", "id");
    /** @type {Object.<string, import("models").Thread>} */
    static records = {};
    /** @returns {import("models").Thread} */
    static get(data) {
        return super.get(data);
    }
    static new(data) {
        /** @type {import("models").Thread} */
        const thread = super.new(data);
        thread.composer = {};
        Record.onChange(thread, "isLoaded", () => {
            if (thread.isLoaded) {
                thread.isLoadedDeferred.resolve();
            } else {
                const def = thread.isLoadedDeferred;
                thread.isLoadedDeferred = new Deferred();
                thread.isLoadedDeferred.then(() => def.resolve());
            }
        });
        Record.onChange(thread, "channelMembers", () => this.store.updateBusSubscription());
        Record.onChange(thread, "is_pinned", () => {
            if (!thread.is_pinned && thread.eq(this.store.discuss.thread)) {
                this.store.discuss.thread = undefined;
            }
        });
        return thread;
    }
    /**
     * @param {string} localId
     * @returns {string}
     */
    static localIdToActiveId(localId) {
        if (!localId) {
            return undefined;
        }
        // Transform "Thread,<model> AND <id>" to "<model>_<id>""
        return localId.split(",").slice(1).join("_").replace(" AND ", "_");
    }
    /** @returns {import("models").Thread|import("models").Thread[]} */
    static insert(data) {
        return super.insert(...arguments);
    }

    /** @param {Object} data */
    update(data) {
        const { id, name, attachments, description, ...serverData } = data;
        assignDefined(this, { id, name, description });
        if (attachments) {
            this.attachments = attachments;
        }
        if (serverData) {
            assignDefined(this, serverData, [
                "uuid",
                "authorizedGroupFullName",
                "avatarCacheKey",
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
                "custom_notifications",
                "mute_until_dt",
                "is_editable",
                "defaultDisplayMode",
            ]);
            assignIn(this, data, [
                "custom_channel_name",
                "memberCount",
                "channelMembers",
                "invitedMembers",
            ]);
            if ("channel_type" in data) {
                this.type = data.channel_type;
            }
            if ("channelMembers" in data) {
                if (this.type === "chat") {
                    for (const member of this.channelMembers) {
                        if (
                            member.persona.notEq(this._store.user) ||
                            (this.channelMembers.length === 1 &&
                                member.persona?.eq(this._store.user))
                        ) {
                            this.chatPartner = member.persona;
                        }
                    }
                }
            }
            if ("seen_partners_info" in serverData) {
                this._store.ChannelMember.insert(
                    serverData.seen_partners_info.map(
                        ({ id, fetched_message_id, partner_id, guest_id, seen_message_id }) => ({
                            id,
                            persona: {
                                id: partner_id ?? guest_id,
                                type: partner_id ? "partner" : "guest",
                            },
                            lastFetchedMessage: fetched_message_id
                                ? { id: fetched_message_id }
                                : undefined,
                            lastSeenMessage: seen_message_id ? { id: seen_message_id } : undefined,
                        })
                    )
                );
            }
        }
        if (this.type === "channel") {
            this._store.discuss.channels.threads.add(this);
        } else if (this.type === "chat" || this.type === "group") {
            this._store.discuss.chats.threads.add(this);
        }
        if (!this.type && !["mail.box", "discuss.channel"].includes(this.model)) {
            this.type = "chatter";
        }
    }

    /** @type {number} */
    id;
    /** @type {string} */
    uuid;
    /** @type {string} */
    model;
    allMessages = Record.many("Message", {
        inverse: "originThread2",
    });
    /** @type {boolean} */
    areAttachmentsLoaded = false;
    attachments = Record.many("Attachment", {
        /**
         * @param {import("models").Attachment} a1
         * @param {import("models").Attachment} a2
         */
        sort: (a1, a2) => (a1.id < a2.id ? 1 : -1),
    });
    activeRtcSession = Record.one("RtcSession");
    /** @type {object|undefined} */
    channel;
    channelMembers = Record.many("ChannelMember", { onDelete: (r) => r.delete() });
    rtcSessions = Record.many("RtcSession", {
        /** @this {import("models").Thread} */
        onDelete(r) {
            this._store.env.services["discuss.rtc"].deleteSession(r.id);
        },
    });
    rtcInvitingSession = Record.one("RtcSession", {
        /** @this {import("models").Thread} */
        onAdd(r) {
            this.rtcSessions.add(r);
            this._store.discuss.ringingThreads.add(this);
        },
        /** @this {import("models").Thread} */
        onDelete(r) {
            this._store.discuss.ringingThreads.delete(this);
        },
    });
    invitedMembers = Record.many("ChannelMember");
    chatPartner = Record.one("Persona");
    composer = Record.one("Composer", { inverse: "thread", onDelete: (r) => r.delete() });
    counter = 0;
    /** @type {string} */
    custom_channel_name;
    /** @type {string} */
    description;
    followers = Record.many("Follower");
    selfFollower = Record.one("Follower");
    /** @type {integer|undefined} */
    followersCount;
    isAdmin = false;
    loadOlder = false;
    loadNewer = false;
    isLoadingAttachments = false;
    isLoadedDeferred = new Deferred();
    isLoaded = false;
    mainAttachment = Record.one("Attachment");
    memberCount = 0;
    message_needaction_counter = 0;
    message_unread_counter = 0;
    /**
     * Contains continuous sequence of messages to show in message list.
     * Messages are ordered from older to most recent.
     * There should not be any hole in this list: there can be unknown
     * messages before start and after end, but there should not be any
     * unknown in-between messages.
     *
     * Content should be fetched and inserted in a controlled way.
     */
    messages = Record.many("Message");
    /** @type {string} */
    modelName;
    /** @type {string} */
    module_icon;
    /**
     * Contains messages received from the bus that are not yet inserted in
     * `messages` list. This is a temporary storage to ensure nothing is lost
     * when fetching newer messages.
     */
    pendingNewMessages = Record.many("Message");
    /**
     * Contains continuous sequence of needaction messages to show in messaging menu.
     * Messages are ordered from older to most recent.
     * There should not be any hole in this list: there can be unknown
     * messages before start and after end, but there should not be any
     * unknown in-between messages.
     *
     * Content should be fetched and inserted in a controlled way.
     *
     * @type {import("models").Message[]}
     */
    needactionMessages = Record.many("Message");
    /** @type {string} */
    name;
    /** @type {number|false} */
    seen_message_id;
    /** @type {'open' | 'folded' | 'closed'} */
    state;
    status = "new";
    /**
     * @deprecated
     * @type {ScrollPosition}
     */
    scrollPosition = new ScrollPosition();
    /** @type {number|'bottom'} */
    scrollTop = Record.attr("bottom", {
        /** @this {import("models").Thread} */
        compute() {
            return this.type === "chatter" ? 0 : "bottom";
        },
    });
    showOnlyVideo = false;
    transientMessages = Record.many("Message");
    /** @type {'channel'|'chat'|'chatter'|'livechat'|'group'|'mailbox'} */
    type;
    /** @type {string} */
    defaultDisplayMode;
    /** @type {SuggestedRecipient[]} */
    suggestedRecipients = [];
    hasLoadingFailed = false;
    canPostOnReadonly;
    /** @type {String} */
    last_interest_dt;
    /** @type {Boolean} */
    is_editable;
    /** @type {false|'mentions'|'no_notif'} */
    custom_notifications = false;
    /** @type {String} */
    mute_until_dt;

    get accessRestrictedToGroupText() {
        if (!this.authorizedGroupFullName) {
            return false;
        }
        return _t('Access restricted to group "%(groupFullName)s"', {
            groupFullName: this.authorizedGroupFullName,
        });
    }

    get areAllMembersLoaded() {
        return this.memberCount === this.channelMembers.length;
    }

    get followersFullyLoaded() {
        return (
            this.followersCount ===
            (this.selfFollower ? this.followers.length + 1 : this.followers.length)
        );
    }

    get attachmentsInWebClientView() {
        const attachments = this.attachments.filter(
            (attachment) => (attachment.isPdf || attachment.isImage) && !attachment.uploading
        );
        attachments.sort((a1, a2) => {
            return a2.id - a1.id;
        });
        return attachments;
    }

    get isUnread() {
        return this.message_unread_counter > 0 || this.needactionMessages.length > 0;
    }

    get typesAllowingCalls() {
        return ["chat", "channel", "group"];
    }

    get allowCalls() {
        return (
            this.typesAllowingCalls.includes(this.type) &&
            !this.correspondent?.eq(this._store.odoobot)
        );
    }

    get hasMemberList() {
        return ["channel", "group"].includes(this.type);
    }

    get hasAttachmentPanel() {
        return this.model === "discuss.channel";
    }

    get isChatChannel() {
        return ["chat", "group"].includes(this.type);
    }

    get displayName() {
        if (this.type === "chat" && this.chatPartner) {
            return this.custom_channel_name || this.chatPartner.nameOrDisplayName;
        }
        if (this.type === "group" && !this.name) {
            const listFormatter = new Intl.ListFormat(
                this._store.env.services["user"].lang?.replace("_", "-"),
                { type: "conjunction", style: "long" }
            );
            return listFormatter.format(
                this.channelMembers.map((channelMember) => channelMember.persona.name)
            );
        }
        return this.name;
    }

    get displayToSelf() {
        return this.is_pinned || (["channel", "group"].includes(this.type) && this.hasSelfAsMember);
    }

    /** @type {import("models").Persona[]} */
    get correspondents() {
        return this.channelMembers
            .map((member) => member.persona)
            .filter((persona) => !!persona)
            .filter((p) => p.notEq(this._store.self));
    }

    /** @type {import("models").Persona|undefined} */
    get correspondent() {
        if (this.type === "channel") {
            return undefined;
        }
        const correspondents = this.correspondents;
        if (correspondents.length === 1) {
            // 2 members chat.
            return correspondents[0];
        }
        if (correspondents.length === 0 && this.channelMembers.length === 1) {
            // Self-chat.
            return this._store.user;
        }
        return undefined;
    }

    get imgUrl() {
        return this.module_icon ?? "/mail/static/src/img/smiley/avatar.jpg";
    }

    get allowDescription() {
        return ["channel", "group"].includes(this.type);
    }

    get isTransient() {
        return !this.id;
    }

    get lastEditableMessageOfSelf() {
        const editableMessagesBySelf = this.nonEmptyMessages.filter(
            (message) => message.isSelfAuthored && message.editable
        );
        if (editableMessagesBySelf.length > 0) {
            return editableMessagesBySelf.at(-1);
        }
        return null;
    }

    get needactionCounter() {
        return this.isChatChannel ? this.message_unread_counter : this.message_needaction_counter;
    }

    /** @returns {import("models").Message | undefined} */
    get newestMessage() {
        return [...this.messages].reverse().find((msg) => !msg.isEmpty);
    }

    get newestPersistentMessage() {
        return [...this.messages].reverse().find((msg) => Number.isInteger(msg.id));
    }

    get newestPersistentNotEmptyOfAllMessage() {
        const allPersistentMessages = this.allMessages.filter(
            (message) => Number.isInteger(message.id) && !message.isEmpty
        );
        allPersistentMessages.sort((m1, m2) => m2.id - m1.id);
        return allPersistentMessages[0];
    }

    get oldestPersistentMessage() {
        return this.messages.find((msg) => Number.isInteger(msg.id));
    }

    get hasSelfAsMember() {
        return this.channelMembers.some((channelMember) =>
            channelMember.persona?.eq(this._store.self)
        );
    }

    get invitationLink() {
        if (!this.uuid || this.type === "chat") {
            return undefined;
        }
        return `${window.location.origin}/chat/${this.id}/${this.uuid}`;
    }

    get isEmpty() {
        return !this.messages.some((message) => !message.isEmpty);
    }

    get offlineMembers() {
        const orderedOnlineMembers = [];
        for (const member of this.channelMembers) {
            if (member.persona.im_status !== "online") {
                orderedOnlineMembers.push(member);
            }
        }
        return orderedOnlineMembers.sort((m1, m2) => (m1.persona.name < m2.persona.name ? -1 : 1));
    }

    get nonEmptyMessages() {
        return this.messages.filter((message) => !message.isEmpty);
    }

    get persistentMessages() {
        return this.messages.filter((message) => !message.isTransient);
    }

    get prefix() {
        return this.isChatChannel ? "@" : "#";
    }

    get lastSelfMessageSeenByEveryone() {
        const otherMembers = this.channelMembers.filter((member) =>
            member.persona.notEq(this._store.self)
        );
        if (otherMembers.length === 0) {
            return false;
        }
        const otherLastSeenMessageIds = otherMembers
            .filter((member) => member.lastSeenMessage)
            .map((member) => member.lastSeenMessage.id);
        if (otherLastSeenMessageIds.length === 0) {
            return false;
        }
        const lastMessageSeenByAllId = Math.min(...otherLastSeenMessageIds);
        const orderedSelfSeenMessages = this.persistentMessages.filter((message) => {
            return message.author?.eq(this._store.self) && message.id <= lastMessageSeenByAllId;
        });
        if (!orderedSelfSeenMessages || orderedSelfSeenMessages.length === 0) {
            return false;
        }
        return orderedSelfSeenMessages.slice().pop();
    }

    get onlineMembers() {
        const orderedOnlineMembers = [];
        for (const member of this.channelMembers) {
            if (member.persona.im_status === "online") {
                orderedOnlineMembers.push(member);
            }
        }
        return orderedOnlineMembers.sort((m1, m2) => {
            const m1HasRtc = Boolean(m1.rtcSession);
            const m2HasRtc = Boolean(m2.rtcSession);
            if (m1HasRtc === m2HasRtc) {
                /**
                 * If raisingHand is falsy, it gets an Infinity value so that when
                 * we sort by [oldest/lowest-value]-first, falsy values end up last.
                 */
                const m1RaisingValue = m1.rtcSession?.raisingHand || Infinity;
                const m2RaisingValue = m2.rtcSession?.raisingHand || Infinity;
                if (m1HasRtc && m1RaisingValue !== m2RaisingValue) {
                    return m1RaisingValue - m2RaisingValue;
                } else {
                    return m1.persona.name?.localeCompare(m2.persona.name) ?? 1;
                }
            } else {
                return m2HasRtc - m1HasRtc;
            }
        });
    }

    get unknownMembersCount() {
        return this.memberCount - this.channelMembers.length;
    }

    get videoCount() {
        return Object.values(this._store.RtcSession.records).filter((session) => session.hasVideo)
            .length;
    }

    get lastInterestDateTime() {
        if (!this.last_interest_dt) {
            return undefined;
        }
        return deserializeDateTime(this.last_interest_dt);
    }

    get muteUntilDateTime() {
        if (!this.mute_until_dt) {
            return undefined;
        }
        return deserializeDateTime(this.mute_until_dt);
    }

    /** @param {import("models").Persona} persona */
    getMemberName(persona) {
        return persona.name;
    }

    getPreviousMessage(message) {
        const previousMessages = this.nonEmptyMessages.filter(({ id }) => id < message.id);
        if (previousMessages.length === 0) {
            return false;
        }
        return this._store.Message.get(Math.max(...previousMessages.map((m) => m.id)));
    }
}

Thread.register();
