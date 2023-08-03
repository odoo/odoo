/* @odoo-module */

import {
    DiscussModel,
    DiscussModelManager,
    discussModelRegistry,
} from "@mail/core/common/discuss_model";
import { ScrollPosition } from "@mail/core/common/scroll_position_model";
import { replaceArrayWithCompare } from "@mail/utils/common/arrays";
import {
    assignDefined,
    createObjectId,
    nullifyClearCommands,
    onChange,
} from "@mail/utils/common/misc";

import { _t } from "@web/core/l10n/translation";
import { Deferred } from "@web/core/utils/concurrency";
import { sprintf } from "@web/core/utils/strings";

/**
 * @typedef SeenInfo
 * @property {{id: number|undefined}} lastFetchedMessage
 * @property {{id: number|undefined}} lastSeenMessage
 * @property {{id: number}} partner
 * @typedef SuggestedRecipient
 * @property {string} email
 * @property {import("@mail/core/common/persona_model").Persona|false} persona
 * @property {string} lang
 * @property {string} reason
 * @property {boolean} checked
 */

export class Thread extends DiscussModel {
    static id = ["model", "id"];

    /** @type {number} */
    id;
    /** @type {string} */
    uuid;
    /** @type {string} */
    model;
    /** @type {boolean} */
    areAttachmentsLoaded = false;
    /** @type {import("@mail/core/common/attachment_model").Attachment[]} */
    attachments = [];
    /** @type {integer} */
    activeRtcSessionId;
    /** @type {object|undefined} */
    channel;
    /** @type {import("@mail/core/common/channel_member_model").ChannelMember[]} */
    channelMembers = [];
    /** @type {RtcSession{}} */
    rtcSessions = {};
    invitingRtcSessionId;
    /** @type {Set<number>} */
    invitedMemberIds = new Set();
    /** @type {integer} */
    chatPartnerId;
    /** @type {import("@mail/core/common/composer_model").Composer} */
    composer;
    counter = 0;
    /** @type {string} */
    customName;
    /** @type {string} */
    description;
    /** @type {Set<import("@mail/core/common/follower_model").Follower>} */
    followers = new Set();
    /** @type {import("@mail/core/common/follower_model").Follower} */
    selfFollower;
    /** @type {integer|undefined} */
    followersCount;
    isAdmin = false;
    loadOlder = false;
    loadNewer = false;
    isLoadingAttachments = false;
    isLoadedDeferred = new Deferred();
    isLoaded = false;
    /** @type {import("@mail/core/common/attachment_model").Attachment} */
    mainAttachment;
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
     *
     * @type {import("@mail/core/common/message_model").Message[]}
     */
    messages = [];
    /** @type {string} */
    modelName;
    /** @type {string} */
    module_icon;
    /**
     * Contains messages received from the bus that are not yet inserted in
     * `messages` list. This is a temporary storage to ensure nothing is lost
     * when fetching newer messages.
     *
     * @type {import("@mail/core/common/message_model").Message[]}
     */
    pendingNewMessages = [];
    /**
     * Contains continuous sequence of needaction messages to show in messaging menu.
     * Messages are ordered from older to most recent.
     * There should not be any hole in this list: there can be unknown
     * messages before start and after end, but there should not be any
     * unknown in-between messages.
     *
     * Content should be fetched and inserted in a controlled way.
     *
     * @type {import("@mail/core/common/message_model").Message[]}
     */
    needactionMessages = [];
    /** @type {string} */
    name;
    /** @type {number|false} */
    seen_message_id;
    /** @type {'open' | 'folded' | 'closed'} */
    state;
    status = "new";
    /** @type {ScrollPosition} */
    scrollPosition = new ScrollPosition();
    showOnlyVideo = false;
    transientMessages = [];
    /** @type {import("@mail/core/common/store_service").Store} */
    _store;
    /** @type {string} */
    defaultDisplayMode;
    /** @type {SeenInfo[]} */
    seenInfos = [];
    /** @type {SuggestedRecipient[]} */
    suggestedRecipients = [];
    hasLoadingFailed = false;
    canPostOnReadonly;
    /** @type {String} */
    last_interest_dt;
    /** @type {number} */
    lastServerMessageId;
    /** @type {Boolean} */
    is_editable;

    constructor(store, data) {
        super(store, data);
        Object.assign(this, {
            id: data.id,
            model: data.model,
            type: data.type,
            _store: store,
        });
    }

    get accessRestrictedToGroupText() {
        if (!this.authorizedGroupFullName) {
            return false;
        }
        return sprintf(_t('Access restricted to group "%(groupFullName)s"'), {
            groupFullName: this.authorizedGroupFullName,
        });
    }

    get activeRtcSession() {
        return this._store.RtcSession.records[this.activeRtcSessionId];
    }

    set activeRtcSession(session) {
        this.activeRtcSessionId = session?.id;
    }

    get areAllMembersLoaded() {
        return this.memberCount === this.channelMembers.length;
    }

    get followersFullyLoaded() {
        return (
            this.followersCount ===
            (this.selfFollower ? this.followers.size + 1 : this.followers.size)
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
        return this.message_unread_counter > 0 || this.hasNeedactionMessages;
    }

    get isChannel() {
        return ["chat", "channel", "group"].includes(this.type);
    }

    get allowCalls() {
        return (
            ["chat", "channel", "group"].includes(this.type) &&
            this.correspondent !== this._store.odoobot
        );
    }

    get hasMemberList() {
        return ["channel", "group"].includes(this.type);
    }

    get isChatChannel() {
        return ["chat", "group"].includes(this.type);
    }

    get allowSetLastSeenMessage() {
        return ["chat", "group", "channel"].includes(this.type);
    }

    get allowReactions() {
        return true;
    }

    get allowReplies() {
        return true;
    }

    get displayName() {
        if (this.type === "chat" && this.chatPartnerId) {
            return (
                this.customName ||
                this._store.Persona.findById({ type: "partner", id: this.chatPartnerId })
                    .nameOrDisplayName
            );
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

    /** @type {import("@mail/core/common/persona_model").Persona[]} */
    get correspondents() {
        return this.channelMembers
            .map((member) => member.persona)
            .filter((persona) => !!persona)
            .filter(
                ({ id, type }) =>
                    id !== (type === "partner" ? this._store.user?.id : this._store.guest?.id)
            );
    }

    /** @type {import("@mail/core/common/persona_model").Persona|undefined} */
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

    /** @returns {import("@mail/core/common/message_model").Message | undefined} */
    get newestMessage() {
        return [...this.messages].reverse().find((msg) => !msg.isEmpty);
    }

    get newestNeedactionMessage() {
        return this.needactionMessages[this.needactionMessages.length - 1];
    }

    get oldestNeedactionMessage() {
        return this.needactionMessages[0];
    }

    get newestPersistentMessage() {
        return [...this.messages].reverse().find((msg) => Number.isInteger(msg.id));
    }

    get oldestPersistentMessage() {
        return this.messages.find((msg) => Number.isInteger(msg.id));
    }

    get hasSelfAsMember() {
        return this.channelMembers.some((channelMember) =>
            channelMember.persona.equals(this._store.self)
        );
    }

    /**
     * @param {import("@mail/core/common/message_model").Message} message
     */
    hasMessage(message) {
        return this.messages.some(({ id }) => id === message.id);
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
        const otherSeenInfos = [...this.seenInfos].filter(
            (seenInfo) => seenInfo.partner.id !== this._store.self?.id
        );
        if (otherSeenInfos.length === 0) {
            return false;
        }
        const otherLastSeenMessageIds = otherSeenInfos
            .filter((seenInfo) => seenInfo.lastSeenMessage)
            .map((seenInfo) => seenInfo.lastSeenMessage.id);
        if (otherLastSeenMessageIds.length === 0) {
            return false;
        }
        const lastMessageSeenByAllId = Math.min(...otherLastSeenMessageIds);
        const orderedSelfSeenMessages = this.persistentMessages.filter((message) => {
            return this._store.self.equals(message.author) && message.id <= lastMessageSeenByAllId;
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

    get rtcInvitingSession() {
        return this._store.RtcSession.records[this.invitingRtcSessionId];
    }

    get hasNeedactionMessages() {
        return this.needactionMessages.length > 0;
    }

    get videoCount() {
        return Object.values(this._store.RtcSession.records).filter(
            (session) => session.videoStream
        ).length;
    }

    get lastInterestDateTime() {
        if (!this.last_interest_dt) {
            return undefined;
        }
        return luxon.DateTime.fromISO(new Date(this.last_interest_dt).toISOString());
    }

    /**
     *
     * @param {import("@mail/core/common/persona_model").Persona} persona
     */
    getMemberName(persona) {
        return persona.name;
    }

    getPreviousMessage(message) {
        const previousMessages = this.nonEmptyMessages.filter(({ id }) => id < message.id);
        if (previousMessages.length === 0) {
            return false;
        }
        return this._store.Message.records[Math.max(...previousMessages.map((m) => m.id))];
    }
}

export class ThreadManager extends DiscussModelManager {
    /** @type {typeof Thread} */
    class;
    /** @type {Object.<string, Thread>} */
    records = {};

    /**
     * @param {Object} data
     * @returns {Thread}
     */
    getRecord(data) {
        return this.records[createObjectId(data)];
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
        const objectId = createObjectId(this.class.name, data.model, data.id);
        if (objectId in this.records) {
            const thread = this.records[objectId];
            this.update(thread, data);
            return thread;
        }
        let thread = new Thread(this.store, data);
        thread.objectId = objectId;
        this.records[objectId] = thread;
        // return reactive version.
        thread = this.records[thread.objectId];
        onChange(thread, "message_unread_counter", () => {
            if (thread.channel) {
                thread.channel.message_unread_counter = thread.message_unread_counter;
            }
        });
        onChange(thread, "isLoaded", () => thread.isLoadedDeferred.resolve());
        onChange(thread, "channelMembers", () => this.store.updateBusSubscription());
        onChange(thread, "is_pinned", () => {
            if (!thread.is_pinned && this.store.discuss.threadObjectId === thread.objectId) {
                this.store.discuss.threadObjectId = null;
            }
        });
        this.update(thread, data);
        this.store.Composer.insert({ thread });
        return thread;
    }

    /**
     * @param {Thread} thread
     * @param {Object} data
     */
    update(thread, data) {
        const { id, name, attachments: attachmentsData, description, ...serverData } = data;
        assignDefined(thread, { id, name, description });
        if (attachmentsData) {
            replaceArrayWithCompare(
                thread.attachments,
                attachmentsData.map((attachmentData) =>
                    this.store.Attachment.insert(attachmentData)
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
                        const member = this.store.ChannelMember.insert([command, memberData]);
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
                                const record = this.store.ChannelMember.insert(member);
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
                                ? this.store.Message.insert({ id: fetched_message_id })
                                : undefined,
                            lastSeenMessage: seen_message_id
                                ? this.store.Message.insert({ id: seen_message_id })
                                : undefined,
                            partner: this.store.Persona.insert({
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
            !this.store.discuss.channels.threads.includes(thread.objectId)
        ) {
            this.store.discuss.channels.threads.push(thread.objectId);
        } else if (
            (thread.type === "chat" || thread.type === "group") &&
            !this.store.discuss.chats.threads.includes(thread.objectId)
        ) {
            this.store.discuss.chats.threads.push(thread.objectId);
        }
        if (!thread.type && !["mail.box", "discuss.channel"].includes(thread.model)) {
            thread.type = "chatter";
        }
        this.env.bus.trigger("mail.thread/onUpdate", { thread, data });
    }

    // FIXME: should not be here (required by Thread.insert() in livechat)
    sortChannels() {
        this.store.discuss.channels.threads.sort((id1, id2) => {
            const thread1 = this.records[id1];
            const thread2 = this.records[id2];
            return String.prototype.localeCompare.call(thread1.name, thread2.name);
        });
        this.store.discuss.chats.threads.sort((objectId_1, objectId_2) => {
            const thread1 = this.records[objectId_1];
            const thread2 = this.records[objectId_2];
            return thread2.lastInterestDateTime.ts - thread1.lastInterestDateTime.ts;
        });
    }
}

discussModelRegistry.add("Thread", [Thread, ThreadManager]);
