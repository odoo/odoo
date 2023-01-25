/* @odoo-module */

import { _t } from "@web/core/l10n/translation";
import { sprintf } from "@web/core/utils/strings";

import { ScrollPosition } from "@mail/new/core/scroll_position_model";
import { createLocalId } from "../utils/misc";

/**
 * @typedef SeenInfo
 * @property {{id: number|undefined}} lastFetchedMessage
 * @property {{id: number|undefined}} lastSeenMessage
 * @property {{id: number}} partner
 * @typedef SuggestedRecipient
 * @property {string} email
 * @property {import('@mail/new/core/persona_model').Persona|false} persona
 * @property {string} lang
 * @property {string} reason
 * @property {boolean} checked
 */

export class Thread {
    /** @type {number} */
    id;
    /** @type {string} */
    uuid;
    /** @type {string} */
    model;
    /** @type {import("@mail/new/attachments/attachment_model").Attachment[]} */
    attachments = [];
    /** @type {integer} */
    activeRtcSessionId;
    canLeave = false;
    /** @type {import("@mail/new/core/channel_member_model").ChannelMember[]} */
    channelMembers = [];
    /** @type {RtcSession{}} */
    rtcSessions = {};
    /** @type {import("@mail/new/core/persona_model").Persona[]} */
    invitedPartners = [];
    /** @type {integer} */
    chatPartnerId;
    /** @type {Composer} */
    composer;
    counter = 0;
    /** @type {string} */
    customName;
    /** @type {string} */
    description;
    /** @type {import("@mail/new/core/follower_model").Follower[]} */
    followers = [];
    isAdmin = false;
    isUnread = false;
    loadMore = true;
    /** @type {import("@mail/new/attachments/attachment_model").Attachment} */
    mainAttachment;
    memberCount = 0;
    message_needaction_counter = 0;
    message_unread_counter = 0;
    /** @type {number[]} */
    messageIds = [];
    /** @type {string} */
    name;
    /** @type {number} */
    serverLastSeenMsgBySelf;
    /** @type {'opened' | 'folded' | 'closed'} */
    state;
    status = "new";
    /** @type {ScrollPosition} */
    scrollPosition = new ScrollPosition();
    typingMemberIds = [];
    /** @type {import("@mail/new/core/store_service").Store} */
    _store;
    /** @type {string} */
    defaultDisplayMode;
    /** @type {SeenInfo[]} */
    seenInfos = [];
    serverMessageUnreadCounter = 0;
    /** @type {SuggestedRecipient[]} */
    suggestedRecipients = [];

    constructor(store, data) {
        Object.assign(this, {
            id: data.id,
            model: data.model,
            type: data.type,
            _store: store,
        });
        if (this.type === "channel") {
            this._store.discuss.channels.threads.push(this.localId);
        } else if (this.type === "chat" || this.type === "group") {
            this._store.discuss.chats.threads.push(this.localId);
        }
        store.threads[this.localId] = this;
    }

    get messages() {
        return this.messageIds.map((id) => this._store.messages[id]);
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
        return this._store.rtcSessions[this.activeRtcSessionId];
    }

    set activeRtcSession(session) {
        this.activeRtcSessionId = session?.id;
    }

    get areAllMembersLoaded() {
        return this.memberCount === this.channelMembers.length;
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

    get displayName() {
        if (this.type === "chat" && this.chatPartnerId) {
            return (
                this.customName ||
                this._store.personas[createLocalId("partner", this.chatPartnerId)].name
            );
        }
        if (this.type === "group" && !this.name) {
            return this.channelMembers
                .map((channelMember) => channelMember.persona.name)
                .join(_t(", "));
        }
        return this.name;
    }

    /**
     * @returns {import("@mail/new/core/follower_model").Follower}
     */
    get followerOfSelf() {
        return this.followers.find((f) => f.partner === this._store.self);
    }

    get imgUrl() {
        const avatarCacheKey = this.serverData?.channel?.avatarCacheKey;
        if (this.type === "channel" || this.type === "group") {
            return `/web/image/mail.channel/${this.id}/avatar_128?unique=${avatarCacheKey}`;
        }
        if (this.type === "chat") {
            return `/web/image/res.partner/${this.chatPartnerId}/avatar_128?unique=${avatarCacheKey}`;
        }
        return "/mail/static/src/img/smiley/avatar.jpg";
    }

    get isDescriptionChangeable() {
        return !this._store.guest && ["channel", "group"].includes(this.type);
    }

    get isRenameable() {
        return !this._store.guest && ["chat", "channel", "group"].includes(this.type);
    }

    get isTransient() {
        return !this.id;
    }

    get lastEditableMessageOfSelf() {
        const editableMessagesBySelf = this.messages.filter(
            (message) => message.isSelfAuthored && message.editable
        );
        if (editableMessagesBySelf.length > 0) {
            return editableMessagesBySelf.at(-1);
        }
        return null;
    }

    get localId() {
        return createLocalId(this.model, this.id);
    }

    /** @returns {import("@mail/new/core/message_model").Message | undefined} */
    get mostRecentMsg() {
        if (!this.mostRecentMsgId) {
            return undefined;
        }
        return this._store.messages[this.mostRecentMsgId];
    }

    get mostRecentMsgId() {
        if (this.messageIds.length === 0) {
            return undefined;
        }
        return Math.max(...this.messageIds);
    }

    get mostRecentNonTransientMessage() {
        if (this.messageIds.length === 0) {
            return undefined;
        }
        const oldestNonTransientMessage = [...this.messages]
            .reverse()
            .find((message) => Number.isInteger(message.id));
        return oldestNonTransientMessage;
    }

    get hasSelfAsMember() {
        return this.channelMembers.some(
            (channelMember) => channelMember.persona === this._store.self
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

    get oldestNonTransientMessage() {
        if (this.messageIds.length === 0) {
            return undefined;
        }
        const oldestNonTransientMessage = this.messages.find((message) =>
            Number.isInteger(message.id)
        );
        return oldestNonTransientMessage;
    }

    get nonTransientMessages() {
        return this.messages.filter((message) => !message.isTransient);
    }

    get lastSelfMessageSeenByEveryone() {
        const otherSeenInfos = [...this.seenInfos].filter(
            (seenInfo) => seenInfo.partner.id !== this._store.self.id
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
        const orderedSelfSeenMessages = this.nonTransientMessages.filter((message) => {
            return message.author === this._store.self && message.id <= lastMessageSeenByAllId;
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
        return orderedOnlineMembers.sort((m1, m2) => (m1.persona.name < m2.persona.name ? -1 : 1));
    }

    get unknownMembersCount() {
        return this.memberCount - this.channelMembers.length;
    }

    get hasTypingMembers() {
        return this.typingMembers.length !== 0;
    }

    get typingMembers() {
        return this.typingMemberIds.map((memberId) => this._store.channelMembers[memberId]);
    }

    get videoCount() {
        return Object.values(this.rtcSessions).filter((session) => session.videoStream).length;
    }
}
