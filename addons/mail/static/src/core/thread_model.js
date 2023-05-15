/* @odoo-module */

import { _t } from "@web/core/l10n/translation";
import { sprintf } from "@web/core/utils/strings";

import { ScrollPosition } from "@mail/core/scroll_position_model";
import { createLocalId } from "../utils/misc";
import { Deferred } from "@web/core/utils/concurrency";

/**
 * @typedef SeenInfo
 * @property {{id: number|undefined}} lastFetchedMessage
 * @property {{id: number|undefined}} lastSeenMessage
 * @property {{id: number}} partner
 * @typedef SuggestedRecipient
 * @property {string} email
 * @property {import("@mail/core/persona_model").Persona|false} persona
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
    /** @type {boolean} */
    areAttachmentsLoaded = false;
    /** @type {import("@mail/attachments/attachment_model").Attachment[]} */
    attachments = [];
    /** @type {object|undefined} */
    channel;
    /** @type {integer} */
    chatPartnerId;
    /** @type {import("@mail/composer/composer_model").Composer} */
    composer;
    counter = 0;
    /** @type {string} */
    customName;
    /** @type {string} */
    description;
    /** @type {import("@mail/core/follower_model").Follower[]} */
    followers = [];
    isAdmin = false;
    loadOlder = false;
    loadNewer = false;
    isLoadingAttachments = false;
    isLoadedDeferred = new Deferred();
    isLoaded = false;
    /** @type {import("@mail/attachments/attachment_model").Attachment} */
    mainAttachment;
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
     * @type {import("@mail/core/message_model").Message[]}
     */
    messages = [];
    /**
     * Contains messages received from the bus that are not yet inserted in
     * `messages` list. This is a temporary storage to ensure nothing is lost
     * when fetching newer messages.
     *
     * @type {import("@mail/core/message_model").Message[]}
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
     * @type {import("@mail/core/message_model").Message[]}
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
    /** @type {import("@mail/core/store_service").Store} */
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
        Object.assign(this, {
            id: data.id,
            model: data.model,
            type: data.type,
            _store: store,
        });
        this.setup();
        store.threads[this.localId] = this;
        return store.threads[this.localId];
    }

    setup() {} // To override thread model attributes

    get accessRestrictedToGroupText() {
        if (!this.authorizedGroupFullName) {
            return false;
        }
        return sprintf(_t('Access restricted to group "%(groupFullName)s"'), {
            groupFullName: this.authorizedGroupFullName,
        });
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
        return this.name;
    }

    /**
     * @returns {import("@mail/core/follower_model").Follower}
     */
    get followerOfSelf() {
        return this.followers.find((f) => f.partner === this._store.self);
    }

    get imgUrl() {
        const avatarCacheKey = this.channel?.avatarCacheKey;
        if (this.type === "channel" || this.type === "group") {
            return `/web/image/discuss.channel/${this.id}/avatar_128?unique=${avatarCacheKey}`;
        }
        if (this.type === "chat") {
            return `/web/image/res.partner/${this.chatPartnerId}/avatar_128?unique=${avatarCacheKey}`;
        }
        return (
            this.newestNeedactionMessage?.module_icon ?? "/mail/static/src/img/smiley/avatar.jpg"
        );
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

    get localId() {
        return createLocalId(this.model, this.id);
    }

    /** @returns {import("@mail/core/message_model").Message | undefined} */
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

    get invitationLink() {
        if (!this.uuid || this.type === "chat") {
            return undefined;
        }
        return `${window.location.origin}/chat/${this.id}/${this.uuid}`;
    }

    get isEmpty() {
        return !this.messages.some((message) => !message.isEmpty);
    }

    get nonEmptyMessages() {
        return this.messages.filter((message) => !message.isEmpty);
    }

    get persistentMessages() {
        return this.messages.filter((message) => !message.isTransient);
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
            return message.author === this._store.self && message.id <= lastMessageSeenByAllId;
        });
        if (!orderedSelfSeenMessages || orderedSelfSeenMessages.length === 0) {
            return false;
        }
        return orderedSelfSeenMessages.slice().pop();
    }

    get hasNeedactionMessages() {
        return this.needactionMessages.length > 0;
    }

    get lastInterestDateTime() {
        if (!this.last_interest_dt) {
            return undefined;
        }
        return luxon.DateTime.fromISO(new Date(this.last_interest_dt).toISOString());
    }

    /**
     *
     * @param {import("@mail/core/persona_model").Persona} persona
     */
    getMemberName(persona) {
        return persona.name;
    }

    getPreviousMessage(message) {
        const previousMessages = this.nonEmptyMessages.filter(({ id }) => id < message.id);
        if (previousMessages.length === 0) {
            return false;
        }
        return this._store.messages[Math.max(...previousMessages.map((m) => m.id))];
    }
}
