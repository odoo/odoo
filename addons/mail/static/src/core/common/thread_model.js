import { AND, fields, Record } from "@mail/core/common/record";
import { generateEmojisOnHtml } from "@mail/utils/common/format";
import { assignDefined } from "@mail/utils/common/misc";
import { rpc } from "@web/core/network/rpc";

import { _t } from "@web/core/l10n/translation";
import { user } from "@web/core/user";
import { Deferred } from "@web/core/utils/concurrency";

/**
 * @typedef SuggestedRecipient
 * @property {string} email
 * @property {import("models").Persona|false} persona
 * @property {string} lang
 * @property {string} reason
 */

export class Thread extends Record {
    static id = AND("model", "id");
    static _name = "mail.thread";
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
    static async getOrFetch(data, fieldNames = []) {
        let thread = this.get(data);
        if (
            data.id > 0 &&
            (!thread || fieldNames.some((fieldName) => thread[fieldName] === undefined))
        ) {
            await this.store.fetchStoreData("mail.thread", {
                thread_model: data.model,
                thread_id: data.id,
                request_list: fieldNames,
            });
            thread = this.get(data);
            if (!thread?.exists()) {
                return;
            }
        }
        return thread;
    }

    autofocus = 0;
    create_uid = fields.One("res.users");
    /** @type {number} */
    id;
    /** @type {string} */
    uuid;
    /** @type {string} */
    model;
    allMessages = fields.Many("mail.message", {
        inverse: "thread",
    });
    storeAsAllChannels = fields.One("Store", {
        compute() {
            if (this.model === "discuss.channel") {
                return this.store;
            }
        },
        eager: true,
    });
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
        compute() {
            return (
                this.self_member_id?.is_pinned ||
                (["channel", "group"].includes(this.channel?.channel_type) &&
                    this.hasSelfAsMember &&
                    !this.parent_channel_id)
            );
        },
        onUpdate() {
            this.onPinStateUpdated();
        },
    });
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
    get importantCounter() {
        if (this.model === "mail.box") {
            return this.counter;
        }
        return this.message_needaction_counter;
    }
    isDisplayed = fields.Attr(false, {
        compute() {
            return this.computeIsDisplayed();
        },
        onUpdate() {
            this.isDisplayedOnUpdate();
        },
    });
    isDisplayedOnUpdate() {}
    get isFocused() {
        return this.isFocusedCounter !== 0;
    }
    isFocusedCounter = fields.Attr(0, {
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
    message_main_attachment_id = fields.One("ir.attachment");
    message_needaction_counter = 0;
    message_needaction_counter_bus_id = 0;
    messageInEdition = fields.One("mail.message", { inverse: "threadAsInEdition" });
    /**
     * Contains continuous sequence of messages to show in message list.
     * Messages are ordered from older to most recent.
     * There should not be any hole in this list: there can be unknown
     * messages before start and after end, but there should not be any
     * unknown in-between messages.
     *
     * Content should be fetched and inserted in a controlled way.
     */
    messages = fields.Many("mail.message");
    /**
     * Phantom messages is a snapshot of `messages` while the thread is being loaded.
     * In other words: when thread is not loaded or loading, phantom messages are the
     * messages before thread loading.
     */
    phantomMessages = fields.Many("mail.message");
    /** @type {string} */
    modelName;
    /** @type {string} */
    module_icon;
    /**
     * Contains messages received from the bus that are not yet inserted in
     * `messages` list. This is a temporary storage to ensure nothing is lost
     * when fetching newer messages.
     */
    pendingNewMessages = fields.Many("mail.message");
    needactionMessages = fields.Many("mail.message", {
        inverse: "threadAsNeedaction",
        sort: (message1, message2) => message1.id - message2.id,
    });
    // FIXME: should be in the portal/frontend bundle but live chat can be loaded
    // before portal resulting in the field not being properly initialized.
    portal_partner = fields.One("res.partner");
    status = "new";
    /**
     * Stored scoll position of thread from top in ASC order.
     *
     * @type {number|'bottom'}
     */
    scrollTop = "bottom";
    transientMessages = fields.Many("mail.message");
    /* The additional recipients are the recipients that are manually added
     * by the user by using the "To" field of the Chatter. */
    additionalRecipients = fields.Attr([]);
    /* The suggested recipients are the recipients that are suggested by the
     * current model and includes the recipients of the last message. (e.g: for
     * a crm lead, the model will suggest the customer associated to the lead). */
    suggestedRecipients = fields.Attr([]);
    /** @type {String[]|undefined} */
    partner_fields;
    /** @type {String|undefined} */
    primary_email_field;
    hasLoadingFailed = false;
    canPostOnReadonly;
    /** @type {Boolean} */
    is_editable;
    /** @type {Boolean} */
    isLocallyPinned = fields.Attr(false, {
        onUpdate() {
            this.onPinStateUpdated();
        },
    });
    /** @type {"not_fetched"|"pending"|"fetched"} */
    fetchMembersState = "not_fetched";
    /** @type {integer|null} */
    highlightMessage = fields.One("mail.message");
    /** @type {String|undefined} */
    access_token;
    /** @type {String|undefined} */
    hash;
    /**
     * Partner id for non channel threads
     *  @type {integer|undefined}
     */
    pid;
    composerDisabled = fields.Attr(false, {
        compute() {
            return this.computeComposerDisabled();
        },
        onUpdate() {
            this.composerDisabledonUpdate();
        },
    });

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
        const attachments = this.attachments.filter(
            (attachment) => (attachment.isPdf || attachment.isImage) && !attachment.uploading
        );
        attachments.sort((a1, a2) => a2.id - a1.id);
        return attachments;
    }

    get isUnread() {
        return this.needactionMessages.length > 0;
    }

    /**
     * Return the name of the given persona to display in the context of this
     * thread.
     *
     * @param {import("models").Persona} persona
     * @returns {string}
     */
    getPersonaName(persona) {
        return persona.displayName || persona.name;
    }

    get hasAttachmentPanel() {
        return this.model === "discuss.channel";
    }

    get supportsCustomChannelName() {
        return this.isChatChannel && this.channel?.channel_type !== "group";
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

    get fullNameWithParent() {
        const text = this.parent_channel_id
            ? `${this.parent_channel_id.displayName} > ${this.displayName}`
            : this.displayName;
        return text;
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
        return this.message_needaction_counter;
    }

    newestMessage = fields.One("mail.message", {
        inverse: "threadAsNewest",
        compute() {
            return this.messages.at(-1);
        },
    });

    get newestPersistentMessage() {
        return this.messages.findLast((msg) => Number.isInteger(msg.id));
    }

    newestPersistentAllMessages = fields.Many("mail.message", {
        compute() {
            const allPersistentMessages = this.allMessages.filter((message) =>
                Number.isInteger(message.id)
            );
            allPersistentMessages.sort((m1, m2) => m2.id - m1.id);
            return allPersistentMessages;
        },
    });

    newestPersistentOfAllMessage = fields.One("mail.message", {
        compute() {
            return this.newestPersistentAllMessages[0];
        },
    });

    get oldestPersistentMessage() {
        return this.messages.find((msg) => Number.isInteger(msg.id));
    }

    onPinStateUpdated() {}

    computeComposerDisabled() {}

    composerDisabledonUpdate() {}

    get isEmpty() {
        return this.messages.length === 0;
    }

    get nonEmptyMessages() {
        return this.messages.filter((message) => !message.isEmpty);
    }

    get persistentMessages() {
        return this.messages.filter((message) => !message.is_transient && !message.isPending);
    }

    get prefix() {
        return this.isChatChannel ? "@" : "#";
    }

    get rpcParams() {
        return {};
    }

    async checkReadAccess() {
        await this.store["mail.thread"].getOrFetch(this, ["hasReadAccess"]);
        return this.hasReadAccess;
    }

    /** @param {{after: Number, before: Number}} */
    async fetchMessages({ after, around, before } = {}) {
        this.status = "loading";
        if (!["mail.box", "discuss.channel"].includes(this.model) && !this.id) {
            this.isLoaded = true;
            return [];
        }
        let res;
        try {
            res = await this.fetchMessagesData({ after, around, before });
            this.hasLoadingFailed = false;
        } catch (e) {
            this.hasLoadingFailed = true;
            this.isLoaded = true;
            this.status = "ready";
            throw e;
        }
        this.store.insert(res.data);
        const msgs = this.store["mail.message"].insert(res.messages.reverse());
        this.isLoaded = true;
        this.status = "ready";
        return msgs;
    }

    /** @param {{after: Number, before: Number}} */
    async fetchMessagesData({ after, around, before } = {}) {
        // ordered messages received: newest to oldest
        return await rpc(this.getFetchRoute(), {
            ...this.getFetchParams(),
            fetch_params: {
                limit:
                    !around && around !== 0 ? this.store.FETCH_LIMIT : this.store.FETCH_LIMIT * 2,
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
            return;
        }
        const before = epoch === "older" ? this.oldestPersistentMessage?.id : undefined;
        const after = epoch === "newer" ? this.newestPersistentMessage?.id : undefined;
        let fetched = [];
        try {
            fetched = await this.fetchMessages({ after, before });
        } catch {
            return;
        }
        if (
            (after !== undefined && !this.messages.some((message) => message.id === after)) ||
            (before !== undefined && !this.messages.some((message) => message.id === before))
        ) {
            // there might have been a jump to message during RPC fetch.
            // Abort feeding messages as to not put holes in message list.
            return;
        }
        const alreadyKnownMessages = new Set(this.messages.map(({ id }) => id));
        const messagesToAdd = fetched.filter((message) => !alreadyKnownMessages.has(message.id));
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
                const missingMessages = this.pendingNewMessages.filter(
                    ({ id }) => !alreadyKnownMessages.has(id)
                );
                if (missingMessages.length > 0) {
                    this.messages.push(...missingMessages);
                    this.messages.sort((m1, m2) => m1.id - m2.id);
                }
            }
        }
        this._enrichMessagesWithTransient();
        this.pendingNewMessages = [];
    }

    /**
     * Get the effective persona performing actions on this thread.
     * Priority order: logged-in user, portal partner (token-authenticated), guest.
     *
     * @returns {import("models").Persona}
     */
    get effectiveSelf() {
        return this.store.self_partner || this.store.self_guest;
    }

    async fetchNewMessages() {
        if (
            this.status === "loading" ||
            (this.isLoaded && ["discuss.channel", "mail.box"].includes(this.model))
        ) {
            return;
        }
        const after = this.isLoaded ? this.newestPersistentMessage?.id : undefined;
        let fetched = [];
        try {
            fetched = await this.fetchMessages({ after });
        } catch {
            return;
        }
        // feed messages
        // could have received a new message as notification during fetch
        // filter out already fetched (e.g. received as notification in the meantime)
        let startIndex;
        if (after === undefined) {
            startIndex = 0;
        } else {
            const afterIndex = this.messages.findIndex((message) => message.id === after);
            if (afterIndex === -1) {
                // there might have been a jump to message during RPC fetch.
                // Abort feeding messages as to not put holes in message list.
                return;
            } else {
                startIndex = afterIndex + 1;
            }
        }
        const alreadyKnownMessages = new Set(this.messages.map((m) => m.id));
        const filtered = fetched.filter(
            (message) =>
                !alreadyKnownMessages.has(message.id) &&
                (this.persistentMessages.length === 0 ||
                    message.id < this.oldestPersistentMessage.id ||
                    message.id > this.newestPersistentMessage.id)
        );
        this.messages.splice(startIndex, 0, ...filtered);
        Object.assign(this, {
            loadOlder:
                after === undefined && fetched.length === this.store.FETCH_LIMIT
                    ? true
                    : after === undefined && fetched.length !== this.store.FETCH_LIMIT
                    ? false
                    : this.loadOlder,
        });
    }

    getFetchParams() {
        if (this.model === "discuss.channel") {
            return { channel_id: this.id };
        }
        if (this.model === "mail.box") {
            return {};
        }
        return {
            thread_id: this.id,
            thread_model: this.model,
            ...this.rpcParams,
        };
    }

    getFetchRoute() {
        if (this.model === "discuss.channel") {
            return "/discuss/channel/messages";
        }
        if (this.model === "mail.box" && this.id === "inbox") {
            return `/mail/inbox/messages`;
        }
        if (this.model === "mail.box" && this.id === "starred") {
            return `/mail/starred/messages`;
        }
        if (this.model === "mail.box" && this.id === "history") {
            return `/mail/history/messages`;
        }
        return this.fetchRouteChatter;
    }

    get fetchRouteChatter() {
        return "/mail/thread/messages";
    }

    /**
     * Get ready to jump to a message in a thread. This method will fetch the
     * messages around the message to jump to if required, and update the thread
     * messages accordingly.
     *
     * @param {import("models").Message} [messageId] if not provided, load around newest message
     */
    async loadAround(messageId) {
        if (
            this.status === "loading" ||
            (this.isLoaded && this.messages.some(({ id }) => id === messageId))
        ) {
            return;
        }
        this.isLoaded = false;
        this.scrollTop = undefined;
        try {
            this.phantomMessages = this.messages;
            this.messages = await this.fetchMessages({ around: messageId });
            this.phantomMessages = [];
        } catch {
            this.isLoaded = true;
            return;
        }
        this.isLoaded = true;
        this.loadNewer = messageId !== undefined ? true : false;
        this.loadOlder = true;
        const limit =
            !messageId && messageId !== 0 ? this.store.FETCH_LIMIT : this.store.FETCH_LIMIT * 2;
        if (this.messages.length < limit) {
            const olderMessagesCount = this.messages.filter(({ id }) => id < messageId).length;
            const newerMessagesCount = this.messages.filter(({ id }) => id > messageId).length;
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
        await this.store.env.services.orm.silent.call("mail.message", "mark_all_as_read", [
            [
                ["model", "=", this.model],
                ["res_id", "=", this.id],
            ],
        ]);
        this.message_needaction_counter = 0;
    }

    /**
     * @param {Object} [options] used in overrides
     */
    markAsRead(options) {
        const newestPersistentMessage = this.newestPersistentOfAllMessage;
        if (!newestPersistentMessage && !this.isLoaded) {
            this.isLoadedDeferred
                .then(() => new Promise(setTimeout))
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
     * @return {boolean} true if the thread was opened, false otherwise
     */
    open(options) {
        return false;
    }

    async openChatWindow({ focus = false, fromMessagingMenu, bypassCompact, swapOpened } = {}) {
        const thread = await this.store["mail.thread"].getOrFetch(this);
        if (!thread) {
            return;
        }
        await this.store.chatHub.initPromise;
        const cw = this.store.ChatWindow.insert(
            assignDefined({ thread: this }, { fromMessagingMenu, bypassCompact })
        );
        cw.open({ focus, swapOpened });
        return cw;
    }

    async closeChatWindow(options = {}) {
        await this.store.chatHub.initPromise;
        const chatWindow = this.store.ChatWindow.get({ thread: this });
        await chatWindow?.close({ notifyState: false, ...options });
    }

    addOrReplaceMessage(message, tmpMsg) {
        // The message from other personas (not self) should not replace the tmpMsg
        if (tmpMsg && tmpMsg.in(this.messages) && this.effectiveSelf.eq(message.author)) {
            this.messages.splice(this.messages.indexOf(tmpMsg), 1, message);
            return;
        }
        this.messages.add(message);
    }

    /**
     *  @param {ReturnType<import("@odoo/owl").markup>} body
     *  @param {Object} extraData
     */
    async post(body, postData = {}, extraData = {}) {
        let tmpMsg;
        postData.attachments = postData.attachments ? [...postData.attachments] : []; // to not lose them on composer clear
        const { attachments, parentId } = postData;
        const params = await this.store.getMessagePostParams({ body, postData, thread: this });
        Object.assign(params, extraData);
        const tmpId = this.store.getNextTemporaryId();
        params.context = { ...user.context, ...params.context, temporary_id: tmpId };
        if (parentId) {
            params.post_data.parent_id = parentId;
        }
        if (this.model !== "discuss.channel") {
            params.thread_id = this.id;
            params.thread_model = this.model;
        } else {
            const tmpData = {
                id: tmpId,
                attachment_ids: attachments,
                res_id: this.id,
                model: "discuss.channel",
            };
            if (this.store.self_partner) {
                tmpData.author_id = this.store.self_partner;
            } else {
                tmpData.author_guest_id = this.store.self_guest;
            }
            if (parentId) {
                tmpData.parent_id = this.store["mail.message"].get(parentId);
            }
            tmpMsg = this.store["mail.message"].insert({
                ...tmpData,
                body: await generateEmojisOnHtml(body),
                isPending: true,
                thread: this,
            });
            this.messages.push(tmpMsg);
            this.onNewSelfMessage(tmpMsg);
        }
        const data = await this.store.doMessagePost(params, tmpMsg);
        if (!data) {
            return;
        }
        this.store.insert(data.store_data);
        /** @type {import("models").Message} */
        const message = this.store["mail.message"].get(data.message_id);
        this.addOrReplaceMessage(message, tmpMsg);
        this.onNewSelfMessage(message);
        // Only delete the temporary message now that seen_message_id is updated
        // to avoid flickering.
        tmpMsg?.delete();
        if (message.hasLink && this.store.hasLinkPreviewFeature) {
            rpc("/mail/link_preview", { message_id: message.id }, { silent: true });
        }
        return message;
    }

    /** @param {number} index */
    async setMainAttachmentFromIndex(index) {
        this.message_main_attachment_id = this.attachmentsInWebClientView[index];
        await this.store.env.services.orm.call("ir.attachment", "register_as_main_attachment", [
            this.message_main_attachment_id.id,
        ]);
    }

    /**
     * Following a load more or load around, listing of messages contains persistent messages.
     * Transient messages are missing, so this function puts known transient messages at the
     * right place in message list of thread.
     */
    _enrichMessagesWithTransient() {
        for (const message of this.transientMessages) {
            if (message.id < this.oldestPersistentMessage && !this.loadOlder) {
                this.messages.unshift(message);
            } else if (message.id > this.newestPersistentMessage && !this.loadNewer) {
                this.messages.push(message);
            } else {
                let afterIndex = this.messages.findIndex((msg) => msg.id > message.id);
                if (afterIndex === -1) {
                    afterIndex = this.messages.length + 1;
                }
                this.messages.splice(afterIndex - 1, 0, message);
            }
        }
    }
}

Thread.register();
