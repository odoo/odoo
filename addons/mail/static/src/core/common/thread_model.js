// @ts-check
/** @odoo-module native */
import { getMessagePostParams } from "@mail/core/common/message_post";
import { AND, fields, Record } from "@mail/core/common/record";
import { applyCounterDelta, snapshotCounter } from "@mail/utils/common/counters";
import { assignDefined, makeSequential } from "@mail/utils/common/misc";
import { makeLogger } from "@web/core/debug/debug_logger";
import { rpc } from "@web/core/network";
import { _t } from "@web/core/translation";
import { user } from "@web/core/user";
import { Deferred, delay } from "@web/core/utils/concurrency";
/**
 * @typedef SuggestedRecipient
 * @property {string} [display_name]
 * @property {string} email
 * @property {string} name
 * @property {string} [lang]
 * @property {number | false} [partner_id]
 */

const log = makeLogger("mail.thread");

/**
 * @param {{name: string, displayName?: string}} [persona]
 * @returns {string|undefined}
 */
export function getPersonaName(persona) {
    const displayName =
        persona && "displayName" in persona ? persona.displayName : undefined;
    return displayName || persona?.name;
}

export class Thread extends Record {
    static id = AND("model", "id");
    /**
     * @param {string} localId
     * @returns {string}
     */
    static localIdToActiveId(localId) {
        if (!localId) {
            return undefined;
        }
        return localId.split(",").slice(1).join("_").replace(" AND ", "_");
    }
    /**
     * @param {{model: string, id: number | string}} data
     * @param {string[]} [fieldNames=[]]
     * @returns {Promise<import("models").Thread|undefined>}
     */
    static async getOrFetch(data, fieldNames = []) {
        const thread = /** @type {import("models").Thread|undefined} */ (
            this.get(data)
        );
        if (!(Number(data.id) > 0)) {
            return thread;
        }
        const store = this.store;
        const baseKey = `${data.model},${data.id}`;
        const threadFields = /** @type {Object<string, any>|undefined} */ (
            /** @type {unknown} */ (thread)
        );
        const missingFieldNames = fieldNames.filter(
            (fieldName) =>
                threadFields?.[fieldName] === undefined &&
                !store._threadFetchAttempted.has(`${baseKey},${fieldName}`),
        );
        if (thread && missingFieldNames.length === 0) {
            return thread;
        }
        const promiseKey = `${baseKey},${missingFieldNames.join(",")}`;
        const pending = store._threadFetchPromises.get(promiseKey);
        if (pending) {
            log.logic("getOrFetch dedup", () => ({ promiseKey }));
            return pending;
        }
        log.pipeline("getOrFetch", () => ({
            baseKey,
            known: Boolean(thread),
            missing: missingFieldNames,
        }));
        const promise = (async () => {
            try {
                await store.fetchStoreData("mixin.mail.thread", {
                    thread_model: data.model,
                    thread_id: data.id,
                    request_list: missingFieldNames,
                });
            } catch {
                return;
            } finally {
                store._threadFetchPromises.delete(promiseKey);
            }
            const fetchedThread = /** @type {import("models").Thread|undefined} */ (
                this.get(data)
            );
            if (!fetchedThread?.exists()) {
                return;
            }
            const fetchedFields = /** @type {Object<string, any>} */ (
                /** @type {unknown} */ (fetchedThread)
            );
            const stillMissing = missingFieldNames.filter(
                (fieldName) => fetchedFields[fieldName] === undefined,
            );
            if (stillMissing.length > 0) {
                for (const fieldName of stillMissing) {
                    store._threadFetchAttempted.add(`${baseKey},${fieldName}`);
                }
                log.logic("getOrFetch fields absent from response", () => ({
                    baseKey,
                    stillMissing,
                }));
                console.warn(
                    `Thread.getOrFetch: fields [${stillMissing.join(", ")}] of thread ${baseKey} were requested but absent from the server response; they will not be requested again.`,
                );
            }
            return fetchedThread;
        })();
        store._threadFetchPromises.set(promiseKey, promise);
        return promise;
    }

    autofocus = 0;
    create_uid = fields.One("res.users");
    /** @type {number | string} */
    id;
    /** @type {string} */
    uuid;
    /** @type {string} */
    model;
    allMessages = fields.Many("mail.message", {
        inverse: "thread",
    });
    storeAsAllChannels = fields.One("Store", {
        /** @this {import("models").Thread} */
        compute() {
            if (this.isChannelKind) {
                return this.store;
            }
        },
    });
    menuAsThreadCandidate = fields.One("MessagingMenu", {
        /** @this {import("models").Thread} */
        compute() {
            if (
                this.displayToSelf ||
                (this.needactionMessages.length > 0 && !this.isMailbox)
            ) {
                return this.store.messagingMenu;
            }
        },
    });
    /** @returns {boolean} */
    get isChannelKind() {
        return false;
    }
    /** @returns {boolean} */
    get isMailbox() {
        return this.model === "mail.box";
    }
    /** @returns {boolean} */
    get isDirectChat() {
        return false;
    }
    /** @type {boolean} */
    areAttachmentsLoaded = false;
    group_public_id = fields.One("res.groups");
    attachments = fields.Many("ir.attachment", {
        /**
         * @param {import("models").Attachment} a1
         * @param {import("models").Attachment} a2
         */
        sort: (a1, a2) => (a1.id < a2.id ? 1 : -1),
    });
    /** @returns {boolean} */
    get canLeave() {
        return false;
    }
    /** @returns {boolean} */
    get canUnpin() {
        return false;
    }
    /** @type {boolean} */
    can_react = true;
    chat_window = fields.One("ChatWindow", {
        inverse: "thread",
    });
    close_chat_window = fields.Attr(undefined, {
        /** @this {import("models").Thread} */
        onUpdate() {
            if (this.close_chat_window) {
                this.close_chat_window = undefined;
                this.closeChatWindow({ force: true });
            }
        },
    });
    composer = fields.One("Composer", {
        compute: () => ({}),
        inverse: "thread",
        onDelete: (r) => r.delete(),
    });
    counter = 0;
    counter_bus_id = 0;
    /** @type {string} */
    description;
    /** @type {string} */
    display_name;
    displayToSelf = fields.Attr(false, {
        /** @this {import("models").Thread} */
        compute() {
            return this.computeDisplayToSelf();
        },
        /** @this {import("models").Thread} */
        onUpdate() {
            this.onPinStateUpdated();
        },
    });
    /** @returns {boolean} */
    computeDisplayToSelf() {
        return false;
    }
    followers = fields.Many("mail.followers", {
        /** @this {import("models").Thread} */
        onAdd(r) {
            r.thread = this;
        },
        onDelete: (r) => r.delete(),
    });
    selfFollower = fields.One("mail.followers", {
        /** @this {import("models").Thread} */
        onAdd(r) {
            r.thread = this;
        },
        onDelete: (r) => r.delete(),
    });
    /** @type {integer|undefined} */
    followersCount;
    loadOlder = false;
    loadNewer = false;
    /** @returns {number} */
    get importantCounter() {
        if (this.isMailbox) {
            return this.counter;
        }
        return this.message_needaction_counter;
    }
    isDisplayed = fields.Attr(false, {
        /** @this {import("models").Thread} */
        compute() {
            return this.computeIsDisplayed();
        },
        /** @this {import("models").Thread} */
        onUpdate() {
            this.isDisplayedOnUpdate();
        },
    });
    isDisplayedOnUpdate() {}

    get composerDisabled() {
        return false;
    }

    get isFocused() {
        return this.isFocusedCounter !== 0;
    }
    isFocusedByThread = fields.Attr(false, {
        /** @this {import("models").Thread} */
        onUpdate() {
            if (this.isFocusedByThread) {
                this.isFocusedCounter++;
            } else {
                this.isFocusedCounter--;
            }
        },
    });
    isFocusedCounter = fields.Attr(0, {
        /** @this {import("models").Thread} */
        onUpdate() {
            if (this.isFocusedCounter < 0) {
                this.isFocusedCounter = 0;
            }
        },
    });
    isLoadingAttachments = false;
    isLoadedDeferred = new Deferred();
    isLoaded = fields.Attr(false, {
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
    /** @type {Boolean|undefined} */
    has_mail_thread;
    message_main_attachment_id = fields.One("ir.attachment");
    message_needaction_counter = 0;
    message_needaction_counter_bus_id = 0;
    messageInEdition = fields.One("mail.message", { inverse: "threadAsInEdition" });
    messages = fields.Many("mail.message");
    phantomMessages = fields.Many("mail.message");
    /** @type {string} */
    modelName;
    /** @type {string} */
    module_icon;
    pendingNewMessages = fields.Many("mail.message");
    needactionMessages = fields.Many("mail.message", {
        inverse: "threadAsNeedaction",
        sort: (message1, message2) => Number(message1.id) - Number(message2.id),
    });
    portal_partner = fields.One("res.partner");
    status = "new";
    /** @type {number | "bottom" | "bottom-smooth"} */
    scrollTop = "bottom";
    transientMessages = fields.Many("mail.message");
    /** @type {SuggestedRecipient[]} */
    additionalRecipients = fields.Attr([]);
    /** @type {SuggestedRecipient[]} */
    suggestedRecipients = fields.Attr([]);
    /** @returns {SuggestedRecipient[]} */
    get allRecipients() {
        return [...this.suggestedRecipients, ...this.additionalRecipients];
    }
    /** @type {String[]|undefined} */
    partner_fields;
    /** @type {String|undefined} */
    primary_email_field;
    hasLoadingFailed = false;
    /** @type {Error} */
    hasLoadingFailedError;
    /** @type {boolean|undefined} */
    canPostOnReadonly;
    /** @type {boolean|undefined} */
    hasReadAccess;
    /** @type {boolean|undefined} */
    hasWriteAccess;
    /** @type {Boolean} */
    is_editable;
    /** @type {Boolean} */
    isLocallyPinned = fields.Attr(false, {
        /** @this {import("models").Thread} */
        onUpdate() {
            this.onPinStateUpdated();
        },
    });
    /** @type {"not_fetched"|"pending"|"fetched"} */
    fetchMembersState = "not_fetched";
    /** @type {import("models").Message|undefined} */
    highlightMessage = fields.One("mail.message");
    /** @type {String|undefined} */
    access_token;
    /** @type {String|undefined} */
    hash;
    /** @type {integer|undefined} */
    pid;

    get accessRestrictedToGroupText() {
        if (!this.group_public_id?.full_name) {
            return false;
        }
        return _t('Access restricted to group "%(groupFullName)s"', {
            groupFullName: this.group_public_id.full_name,
        });
    }

    get busChannel() {
        return `${this.model}_${this.id}`;
    }

    get followersFullyLoaded() {
        return (
            this.followersCount ===
            (this.selfFollower ? this.followers.length + 1 : this.followers.length)
        );
    }

    get attachmentsInWebClientView() {
        return this.attachments.filter(
            (attachment) =>
                (attachment.isPdf || attachment.isImage) && !attachment.uploading,
        );
    }

    get isUnread() {
        return this.needactionMessages.length > 0;
    }

    /** @returns {boolean} */
    get allowCalls() {
        return false;
    }

    get canPostMessage() {
        return this.hasWriteAccess || (this.hasReadAccess && this.canPostOnReadonly);
    }

    /**
     * @param {{name: string, displayName?: string}} persona
     * @returns {string}
     */
    getPersonaName(persona) {
        return getPersonaName(persona);
    }

    /** @returns {boolean} */
    get hasAttachmentPanel() {
        return false;
    }

    /** @returns {boolean} */
    get isChatChannel() {
        return false;
    }

    /** @returns {boolean} */
    get supportsCustomChannelName() {
        return false;
    }

    get displayName() {
        return this.display_name;
    }

    computeIsDisplayed() {
        return this.store.ChatWindow.get({ thread: this })?.isOpen;
    }

    get avatarUrl() {
        return this.module_icon ?? this.store.DEFAULT_AVATAR;
    }

    /** @returns {boolean} */
    get allowDescription() {
        return false;
    }

    /** @returns {string} */
    get fullNameWithParent() {
        return this.displayName;
    }

    get isTransient() {
        return !this.id || Number(this.id) < 0;
    }

    get lastEditableMessageOfSelf() {
        return (
            this.messages.findLast(
                (message) =>
                    !message.isEmpty && message.isSelfAuthored && message.editable,
            ) ?? null
        );
    }

    get needactionCounter() {
        return this.message_needaction_counter;
    }

    newestMessage = fields.One("mail.message", {
        inverse: "threadAsNewest",
        /** @this {import("models").Thread} */
        compute() {
            return this.messages.at(-1);
        },
    });

    get newestPersistentMessage() {
        return this.messages.findLast(
            /** @returns {msg is import("models").Message & {id: number}} */ (msg) =>
                msg.persistent,
        );
    }

    newestPersistentOfAllMessage = fields.One("mail.message", {
        /** @this {import("models").Thread} */
        compute() {
            let newest;
            for (const message of this.allMessages) {
                if (message.persistent && (!newest || message.id > newest.id)) {
                    newest = message;
                }
            }
            return newest;
        },
    });

    get oldestPersistentMessage() {
        return this.messages.find(
            /** @returns {msg is import("models").Message & {id: number}} */ (msg) =>
                msg.persistent,
        );
    }

    onPinStateUpdated() {}

    /** @returns {string|undefined} */
    get invitationLink() {
        return undefined;
    }

    get isEmpty() {
        return this.messages.length === 0;
    }

    get nonEmptyMessages() {
        return this.messages.filter((message) => !message.isEmpty);
    }

    get persistentMessages() {
        return this.messages.filter((message) => message.persistent);
    }

    get prefix() {
        return this.isChatChannel ? "@" : "#";
    }

    get rpcParams() {
        return {};
    }

    async checkReadAccess() {
        await this.store.Thread.getOrFetch(this, ["hasReadAccess"]);
        return this.hasReadAccess;
    }

    /** @returns {boolean} */
    get canFetchMessages() {
        return this.isMailbox || Boolean(this.id);
    }

    /** @param {{after?: number, around?: number | string, before?: number}} [param0] */
    async fetchMessages({ after, around, before } = {}) {
        this.status = "loading";
        log.pipeline("fetchMessages", () => ({
            thread: this.localId,
            after,
            around,
            before,
        }));
        if (!this.canFetchMessages) {
            this.isLoaded = true;
            this.status = "ready";
            return [];
        }
        let res;
        const endFetch = log.perf("fetchMessages");
        try {
            res = await this.fetchMessagesData({ after, around, before });
            this.hasLoadingFailedError = undefined;
            this.hasLoadingFailed = false;
        } catch (e) {
            endFetch({ thread: this.localId, failed: true });
            this.hasLoadingFailed = true;
            this.hasLoadingFailedError = e;
            this.isLoaded = true;
            this.status = "ready";
            throw e;
        }
        endFetch({ thread: this.localId, messages: res.messages.length });
        this.store.insert(res.data);
        const msgs = this.store["mail.message"].insert(res.messages.reverse());
        this.isLoaded = true;
        this.status = "ready";
        return msgs;
    }

    /** @param {{after?: number, around?: number | string, before?: number}} [param0] */
    async fetchMessagesData({ after, around, before } = {}) {
        return await rpc(this.getFetchRoute(), {
            ...this.getFetchParams(),
            fetch_params: {
                limit:
                    !around && around !== 0
                        ? this.store.FETCH_LIMIT
                        : this.store.FETCH_LIMIT * 2,
                after,
                around,
                before,
            },
        });
    }

    /** @param {"older"|"newer"} epoch */
    async fetchMoreMessages(epoch = "older") {
        if (
            this.status === "loading" ||
            (epoch === "older" && !this.loadOlder) ||
            (epoch === "newer" && !this.loadNewer)
        ) {
            log.logic("fetchMoreMessages skipped", () => ({
                thread: this.localId,
                epoch,
                status: this.status,
                loadOlder: this.loadOlder,
                loadNewer: this.loadNewer,
            }));
            return;
        }
        const before = epoch === "older" ? this.oldestPersistentMessage?.id : undefined;
        const after = epoch === "newer" ? this.newestPersistentMessage?.id : undefined;
        let fetched;
        try {
            fetched = await this.fetchMessages({ after, before });
        } catch {
            return;
        }
        if (
            (after !== undefined &&
                !this.messages.some((message) => message.id === after)) ||
            (before !== undefined &&
                !this.messages.some((message) => message.id === before))
        ) {
            log.logic("fetchMoreMessages anchor gone", () => ({
                thread: this.localId,
                epoch,
                after,
                before,
            }));
            return;
        }
        const alreadyKnownMessages = new Set(this.messages.map(({ id }) => id));
        const messagesToAdd = fetched.filter(
            (message) => !alreadyKnownMessages.has(message.id),
        );
        log.pipeline("fetchMoreMessages", () => ({
            thread: this.localId,
            epoch,
            fetched: fetched.length,
            added: messagesToAdd.length,
            exhausted: fetched.length < this.store.FETCH_LIMIT,
        }));
        if (epoch === "older") {
            this.messages.unshift(...messagesToAdd);
        } else {
            this.messages.push(...messagesToAdd);
        }
        if (fetched.length < this.store.FETCH_LIMIT) {
            if (epoch === "older") {
                this.loadOlder = false;
            } else if (epoch === "newer") {
                this.loadNewer = false;
                const missingMessages = this.pendingNewMessages.filter((message) =>
                    message.notIn(this.messages),
                );
                if (missingMessages.length > 0) {
                    this.messages.push(...missingMessages);
                    this.messages.sort((m1, m2) => Number(m1.id) - Number(m2.id));
                }
            }
        }
        this._enrichMessagesWithTransient();
        this.pendingNewMessages.clear();
    }

    /** @returns {import("models").ResPartner|import("models").MailGuest} */
    get effectiveSelf() {
        return this.store.self_partner || this.store.self_guest;
    }

    /** @returns {boolean} */
    get busKeepsMessagesFresh() {
        return this.isMailbox;
    }

    async fetchNewMessages() {
        if (
            this.status === "loading" ||
            (this.isLoaded && this.busKeepsMessagesFresh)
        ) {
            log.logic("fetchNewMessages skipped", () => ({
                thread: this.localId,
                status: this.status,
                isLoaded: this.isLoaded,
                busKeepsMessagesFresh: this.busKeepsMessagesFresh,
            }));
            return;
        }
        const after = this.isLoaded ? this.newestPersistentMessage?.id : undefined;
        let fetched;
        try {
            fetched = await this.fetchMessages({ after });
        } catch {
            return;
        }
        let startIndex;
        if (after === undefined) {
            startIndex = 0;
        } else {
            const afterIndex = this.messages.findIndex(
                (message) => message.id === after,
            );
            if (afterIndex === -1) {
                log.logic("fetchNewMessages anchor gone", () => ({
                    thread: this.localId,
                    after,
                }));
                return;
            } else {
                startIndex = afterIndex + 1;
            }
        }
        const alreadyKnownMessages = new Set(this.messages.map((m) => m.id));
        const filtered = fetched.filter(
            (message) => !alreadyKnownMessages.has(message.id),
        );
        log.pipeline("fetchNewMessages", () => ({
            thread: this.localId,
            after,
            fetched: fetched.length,
            added: filtered.length,
            startIndex,
        }));
        this.messages.splice(startIndex, 0, ...filtered);
        if (
            after === undefined &&
            filtered.length > 0 &&
            alreadyKnownMessages.size > 0
        ) {
            this.messages.sort((m1, m2) => Number(m1.id) - Number(m2.id));
        }
        if (after === undefined) {
            this.loadOlder = fetched.length === this.store.FETCH_LIMIT;
        } else {
            this.loadNewer = fetched.length === this.store.FETCH_LIMIT;
        }
    }

    getFetchParams() {
        if (this.isMailbox) {
            return {};
        }
        return {
            thread_id: this.id,
            thread_model: this.model,
            ...this.rpcParams,
        };
    }

    getFetchRoute() {
        if (this.isMailbox) {
            return `/mail/${this.id}/messages`;
        }
        return this.fetchRouteChatter;
    }

    get fetchRouteChatter() {
        return "/mail/thread/messages";
    }

    _loadAroundSequential = makeSequential();

    /** @param {number | string} [messageId] */
    async loadAround(messageId) {
        if (this.isLoaded && this.messages.some(({ id }) => id === messageId)) {
            return;
        }
        return this._loadAroundSequential(() => this._loadAround(messageId));
    }

    /** @param {number | string} [messageId] */
    async _loadAround(messageId) {
        if (this.isLoaded && this.messages.some(({ id }) => id === messageId)) {
            log.logic("loadAround already loaded", () => ({
                thread: this.localId,
                messageId,
            }));
            return;
        }
        log.pipeline("loadAround", () => ({
            thread: this.localId,
            messageId,
            phantom: this.messages.length,
        }));
        this.isLoaded = false;
        this.scrollTop = undefined;
        const endLoadAround = log.perf("loadAround");
        try {
            this.phantomMessages = this.messages;
            this.messages = await this.fetchMessages({ around: messageId });
            endLoadAround({ thread: this.localId, messages: this.messages.length });
        } catch {
            endLoadAround({ thread: this.localId, failed: true });
            this.isLoaded = true;
            return;
        } finally {
            this.phantomMessages.clear();
        }
        this.isLoaded = true;
        this.loadNewer = messageId !== undefined;
        this.loadOlder = true;
        const limit =
            !messageId && messageId !== 0
                ? this.store.FETCH_LIMIT
                : this.store.FETCH_LIMIT * 2;
        if (this.messages.length < limit) {
            const olderMessagesCount = this.messages.filter(
                ({ id }) => Number(id) < Number(messageId),
            ).length;
            const newerMessagesCount = this.messages.filter(
                ({ id }) => Number(id) > Number(messageId),
            ).length;
            if (olderMessagesCount < limit / 2 - 1) {
                this.loadOlder = false;
            }
            if (newerMessagesCount < limit / 2) {
                this.loadNewer = false;
            }
        }
        this._enrichMessagesWithTransient();
    }

    async markAllMessagesAsRead() {
        const inbox = this.store.inbox;
        const inboxSnapshot = inbox && snapshotCounter(inbox, "counter");
        const needactionSnapshot = snapshotCounter(this, "message_needaction_counter");
        const messages = [...this.needactionMessages];
        let inboxApplied = 0;
        for (const message of messages) {
            message.needaction = false;
            if (inbox) {
                inbox.messages.delete(message);
                inboxApplied += applyCounterDelta(inbox, "counter", -1);
            }
        }
        this.message_needaction_counter = 0;
        log.pipeline("markAllMessagesAsRead", () => ({
            thread: this.localId,
            messages: messages.length,
            inboxApplied,
        }));
        const endMarkAll = log.perf("markAllMessagesAsRead");
        try {
            await this.store.env.services.orm.silent.call(
                "mail.message",
                "mark_all_as_read",
                [
                    [
                        ["model", "=", this.model],
                        ["res_id", "=", this.id],
                    ],
                ],
            );
            endMarkAll({ thread: this.localId });
        } catch (e) {
            endMarkAll({ thread: this.localId, failed: true });
            log.logic("markAllMessagesAsRead rollback", () => ({
                thread: this.localId,
                messages: messages.length,
            }));
            for (const message of messages) {
                message.needaction = true;
                if (inbox) {
                    inbox.messages.add(message);
                }
            }
            inboxSnapshot?.restoreDelta(-inboxApplied);
            needactionSnapshot.restore();
            console.warn("Failed to mark all messages as read", e);
        }
    }

    /** @param {Object} [options] */
    markAsRead(options) {
        const newestPersistentMessage = this.newestPersistentOfAllMessage;
        log.logic("markAsRead", () => ({
            thread: this.localId,
            needaction: this.message_needaction_counter,
            loaded: this.isLoaded,
        }));
        if (!newestPersistentMessage && !this.isLoaded) {
            log.logic("markAsRead deferred until loaded", () => ({
                thread: this.localId,
            }));
            this.isLoadedDeferred
                .then(() => delay())
                .then(() => this.markAsRead(options));
            return;
        }
        if (this.message_needaction_counter > 0) {
            this.markAllMessagesAsRead();
        }
    }

    /** @param {import("models").Message} message */
    onNewSelfMessage(message) {}

    /**
     * @param {Object} [options]
     * @return {boolean}
     */
    open(options) {
        log.logic("open", () => ({ thread: this.localId, options }));
        return this.openChatUI(options) || this.openWebClientUI(options);
    }

    /**
     * @param {Object} [options]
     * @returns {boolean}
     */
    openChatUI(options) {
        return false;
    }

    /**
     * @param {Object} [options]
     * @returns {boolean}
     */
    openWebClientUI(options) {
        return false;
    }

    /** @returns {boolean} */
    openChannel() {
        return false;
    }

    /**
     * @param {Object} [options]
     * @param {boolean} [options.focus=false]
     * @param {boolean} [options.fromMessagingMenu]
     * @param {boolean} [options.bypassCompact]
     * @param {boolean} [options.swapOpened]
     * @returns {Promise<import("models").ChatWindow|undefined>}
     */
    async openChatWindow({
        focus = false,
        fromMessagingMenu,
        bypassCompact,
        swapOpened,
    } = {}) {
        const thread = await this.store.Thread.getOrFetch(this);
        if (!thread) {
            log.logic("openChatWindow thread not fetched", () => ({
                thread: this.localId,
            }));
            return;
        }
        await this.store.chatHub.initPromise;
        log.logic("openChatWindow", () => ({
            thread: this.localId,
            focus,
            fromMessagingMenu,
            bypassCompact,
            swapOpened,
        }));
        const cw = this.store.ChatWindow.insert(
            assignDefined({ thread: this }, { fromMessagingMenu, bypassCompact }),
        );
        cw.open({ focus, swapOpened });
        return cw;
    }

    /** @param {Object} [options={}] */
    async closeChatWindow(options = {}) {
        await this.store.chatHub.initPromise;
        const chatWindow = this.store.ChatWindow.get({ thread: this });
        log.logic("closeChatWindow", () => ({
            thread: this.localId,
            found: Boolean(chatWindow),
            options,
        }));
        await chatWindow?.close({ notifyState: false, ...options });
    }

    /** @param {string} name */
    async rename(name) {}

    /**
     * @param {import("models").Message} message
     * @param {import("models").Message} [tmpMsg]
     */
    addOrReplaceMessage(message, tmpMsg) {
        if (
            tmpMsg &&
            tmpMsg.in(this.messages) &&
            this.effectiveSelf.eq(message.author)
        ) {
            this.messages.splice(this.messages.indexOf(tmpMsg), 1, message);
            return;
        }
        this.messages.add(message);
    }

    /** @returns {boolean} */
    get hasOptimisticPost() {
        return false;
    }

    /**
     * @param {number} tmpId
     * @param {string | ReturnType<import("@odoo/owl").markup>} body
     * @param {Object} postData
     * @returns {Promise<import("models").Message|undefined>}
     */
    async makeOptimisticPendingMessage(tmpId, body, postData) {
        return undefined;
    }

    /**
     * @this {import("models").Thread}
     * @param {string | ReturnType<import("@odoo/owl").markup>} body
     * @param {Object} [postData={}]
     * @param {Object} [extraData={}]
     * @returns {Promise<import("models").Message|undefined>}
     */
    async post(body, postData = {}, extraData = {}) {
        log.logic("post", () => ({
            thread: this.localId,
            attachments: postData.attachments?.length,
            parentId: postData.parentId,
        }));
        postData.attachments = postData.attachments ? [...postData.attachments] : [];
        const { parentId } = postData;
        const params = await getMessagePostParams(this.store, {
            body,
            postData,
            thread: this,
        });
        Object.assign(params, extraData);
        const tmpId = this.store.getNextTemporaryId();
        params.context = { ...user.context, ...params.context, temporary_id: tmpId };
        if (parentId) {
            params.post_data.parent_id = parentId;
        }
        const tmpMsg = await this.makeOptimisticPendingMessage(tmpId, body, postData);
        log.pipeline("post optimistic", () => ({
            thread: this.localId,
            tmpId,
            optimistic: Boolean(tmpMsg),
        }));
        if (tmpMsg) {
            this.messages.push(tmpMsg);
            this.onNewSelfMessage(tmpMsg);
        }
        const data = await this.store.doMessagePost(params, tmpMsg);
        if (!data) {
            log.logic("post no response", () => ({ thread: this.localId, tmpId }));
            return;
        }
        return this.processMessagePostResponse(data, tmpMsg);
    }

    /**
     * @param {Object} data
     * @param {import("models").Message} [tmpMsg]
     * @returns {import("models").Message}
     */
    processMessagePostResponse(data, tmpMsg) {
        this.store.insert(data.store_data);
        /** @type {import("models").Message} */
        const message = this.store["mail.message"].get(data.message_id);
        log.pipeline("processMessagePostResponse", () => ({
            thread: this.localId,
            messageId: data.message_id,
            replacedTmp: Boolean(tmpMsg),
            hasLink: message.hasLink,
        }));
        this.addOrReplaceMessage(message, tmpMsg);
        this.onNewSelfMessage(message);
        tmpMsg?.delete();
        if (message.hasLink && this.store.hasLinkPreviewFeature) {
            rpc("/mail/link_preview", { message_id: message.id }, { silent: true });
        }
        return message;
    }

    /** @param {number} index */
    async setMainAttachmentFromIndex(index) {
        log.logic("setMainAttachmentFromIndex", () => ({
            thread: this.localId,
            index,
        }));
        this.message_main_attachment_id = this.attachmentsInWebClientView[index];
        await this.store.env.services.orm.call(
            "ir.attachment",
            "register_as_main_attachment",
            [this.message_main_attachment_id.id],
        );
    }

    _enrichMessagesWithTransient() {
        for (const message of this.transientMessages) {
            if (message.in(this.messages)) {
                continue;
            }
            if (
                Number(message.id) < this.oldestPersistentMessage?.id &&
                !this.loadOlder
            ) {
                this.messages.unshift(message);
            } else if (
                Number(message.id) > this.newestPersistentMessage?.id &&
                !this.loadNewer
            ) {
                this.messages.push(message);
            } else {
                let afterIndex = this.messages.findIndex((msg) => msg.id > message.id);
                if (afterIndex === -1) {
                    afterIndex = this.messages.length;
                }
                this.messages.splice(afterIndex, 0, message);
            }
        }
    }

    /** @returns {string} */
    _getActualModelName() {
        return "mixin.mail.thread";
    }

    /** @returns {import("models").ChannelMember|undefined} */
    computeCorrespondent() {
        return undefined;
    }

    /** @returns {Readonly<import("models").ChannelMember[]>} */
    get membersThatCanSeen() {
        return [];
    }

    /** @returns {boolean} */
    get showCorrespondentCountry() {
        return false;
    }

    /** @returns {import("models").ChannelMember|undefined} */
    get imStatusMember() {
        return undefined;
    }

    /**
     * @param {{name: string, displayName?: string}} persona
     * @returns {boolean}
     */
    isChatWith(persona) {
        return false;
    }

    /** @returns {string|undefined} */
    get chatWindowComposerType() {
        return "note";
    }

    /** @returns {string} */
    get composerPlaceholder() {
        return _t("Message %(thread name)s…", { "thread name": this.displayName });
    }

    /**
     * @param {import("models").Message} message
     * @returns {string}
     */
    outOfFocusNotificationTitle(message) {
        return message.authorName;
    }

    /** @returns {boolean} */
    get hasStartOfConversationBanner() {
        return false;
    }

    /** @returns {string} */
    get conversationStartTitle() {
        return this.displayName;
    }

    /** @returns {string} */
    get conversationStartSubtitle() {
        return "";
    }

    /** @returns {number|undefined} */
    get newMessageSeparatorId() {
        return undefined;
    }
}

Thread.register();
