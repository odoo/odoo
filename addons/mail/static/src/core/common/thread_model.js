/* @odoo-module */

import { AND, Record } from "@mail/core/common/record";

import { user } from "@web/core/user";
import { deserializeDateTime } from "@web/core/l10n/dates";
import { _t } from "@web/core/l10n/translation";
import { Deferred } from "@web/core/utils/concurrency";
import { DEFAULT_AVATAR } from "@mail/core/common/persona_service";

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
    static new(data) {
        const thread = super.new(data);
        Record.onChange(thread, ["state"], () => {
            if (thread.state !== "closed" && !this.store.env.services.ui.isSmall) {
                this.store.ChatWindow.insert({
                    folded: thread.state === "folded",
                    thread,
                });
            }
        });
        return thread;
    }

    /** @type {number} */
    id;
    /** @type {string} */
    uuid;
    /** @type {string} */
    model;
    allMessages = Record.many("Message", {
        inverse: "originThread",
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
    get canLeave() {
        return (
            ["channel", "group"].includes(this.type) &&
            !this.message_needaction_counter &&
            !this.group_based_subscription
        );
    }
    get canUnpin() {
        return this.type === "chat" && this.importantCounter === 0;
    }
    channelMembers = Record.many("ChannelMember", {
        onDelete: (r) => r.delete(),
        /** @this {import("models").Thread} */
        onUpdate() {
            this._store.updateBusSubscription();
        },
    });
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
    composer = Record.one("Composer", {
        compute: () => ({}),
        inverse: "thread",
        onDelete: (r) => r.delete(),
    });
    correspondent = Record.one("Persona", {
        compute() {
            return this.computeCorrespondent();
        },
    });
    counter = 0;
    /** @type {string} */
    custom_channel_name;
    /** @type {string} */
    description;
    followers = Record.many("Follower");
    selfFollower = Record.one("Follower", {
        /** @this {import("models").Thread} */
        onAdd(r) {
            r.followedThread = this;
        },
        onDelete: (r) => (r.followedThread = undefined),
    });
    /** @type {integer|undefined} */
    followersCount;
    isAdmin = false;
    loadOlder = false;
    loadNewer = false;
    get importantCounter() {
        if (this.type === "mailbox") {
            return this.counter;
        }
        if (this.isChatChannel) {
            return this.message_unread_counter || this.message_needaction_counter;
        }
        return this.message_needaction_counter;
    }
    isLoadingAttachments = false;
    isLoadedDeferred = new Deferred();
    isLoaded = Record.attr(false, {
        /** @this {import("models").Thread} */
        onUpdate() {
            if (this.isLoaded) {
                this.isLoadedDeferred.resolve();
            } else {
                const def = this.isLoadedDeferred;
                this.isLoadedDeferred = new Deferred();
                this.isLoadedDeferred.then(() => def.resolve());
            }
        },
    });
    is_pinned = Record.attr(undefined, {
        /** @this {import("models").Thread} */
        onUpdate() {
            if (!this.is_pinned && this.eq(this._store.discuss.thread)) {
                this._store.discuss.thread = undefined;
            }
        },
    });
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
    type = Record.attr("", {
        /** @this {import("models").Thread} */
        compute() {
            if (this.model === "discuss.channel") {
                return this.channel_type;
            }
            if (this.model === "mail.box") {
                return "mailbox";
            }
            return "chatter";
        },
        eager: true,
    });
    discussAppCategory = Record.one("DiscussAppCategory", {
        compute() {
            return this._computeDiscussAppCategory();
        },
    });
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
    /** @type {Boolean} */
    isLocallyPinned = false;
    /** @type {"not_fetched"|"pending"|"fetched"} */
    fetchMembersState = "not_fetched";

    _computeDiscussAppCategory() {
        if (["group", "chat"].includes(this.type)) {
            return this._store.discuss.chats;
        }
        if (this.type === "channel") {
            return this._store.discuss.channels;
        }
    }

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
        if (this.type === "chat" && this.correspondent) {
            return this.custom_channel_name || this.correspondent.nameOrDisplayName;
        }
        if (this.type === "group" && !this.name) {
            const listFormatter = new Intl.ListFormat(user.lang?.replace("_", "-"), {
                type: "conjunction",
                style: "long",
            });
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
        const members = [];
        for (const channelMember of this.channelMembers) {
            if (channelMember.persona.notEq(this._store.self)) {
                members.push(channelMember.persona);
            }
        }
        return members;
    }

    computeCorrespondent() {
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
            return this._store.self;
        }
        return undefined;
    }

    get avatarUrl() {
        return this.module_icon ?? DEFAULT_AVATAR;
    }

    get allowDescription() {
        return ["channel", "group"].includes(this.type);
    }

    get isTransient() {
        return !this.id || this.id < 0;
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

    offlineMembers = Record.many("ChannelMember", {
        /** @this {import("models").Thread} */
        compute() {
            return this.channelMembers.filter((member) => member.persona?.im_status !== "online");
        },
        sort: (m1, m2) => (m1.persona?.name < m2.persona?.name ? -1 : 1),
    });

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
            .filter((member) => member.seen_message_id)
            .map((member) => member.seen_message_id.id);
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

    onlineMembers = Record.many("ChannelMember", {
        /** @this {import("models").Thread} */
        compute() {
            return this.channelMembers.filter((member) => member.persona.im_status === "online");
        },
        sort: (m1, m2) => {
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
        },
    });

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
