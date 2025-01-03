import { cleanTerm, prettifyMessageContent } from "@mail/utils/common/format";
import { Store as BaseStore, makeStore, Record } from "@mail/core/common/record";
import { threadCompareRegistry } from "@mail/core/common/thread_compare";

import { reactive } from "@odoo/owl";

import { _t } from "@web/core/l10n/translation";
import { rpc } from "@web/core/network/rpc";
import { registry } from "@web/core/registry";
import { user } from "@web/core/user";
import { Deferred, Mutex } from "@web/core/utils/concurrency";
import { debounce } from "@web/core/utils/timing";
import { session } from "@web/session";
import { browser } from "@web/core/browser/browser";

/**
 * @typedef {{isSpecial: boolean, channel_types: string[], label: string, displayName: string, description: string}} SpecialMention
 */

let prevLastMessageId = null;
let temporaryIdOffset = 0.01;

export const pyToJsModels = {
    "discuss.channel": "Thread",
    "mail.guest": "Persona",
    "mail.thread": "Thread",
    "res.partner": "Persona",
};

export const addFieldsByPyModel = {
    "discuss.channel": { model: "discuss.channel" },
    "mail.guest": { type: "guest" },
    "res.partner": { type: "partner" },
};

export class Store extends BaseStore {
    static FETCH_DATA_DEBOUNCE_DELAY = 1;
    static OTHER_LONG_TYPING = 60000;
    FETCH_LIMIT = 30;
    DEFAULT_AVATAR = "/mail/static/src/img/smiley/avatar.jpg";
    isReady = new Deferred();

    /** @returns {import("models").Store|import("models").Store[]} */
    static insert() {
        return super.insert(...arguments);
    }

    /** @type {typeof import("@mail/core/common/chat_window_model").ChatWindow} */
    ChatWindow;
    /** @type {typeof import("@mail/core/common/composer_model").Composer} */
    Composer;
    /** @type {typeof import("@mail/core/common/failure_model").Failure} */
    Failure;
    /** @type {typeof import("@mail/core/common/attachment_model").Attachment} */
    ["ir.attachment"];
    /** @type {typeof import("@mail/core/web/activity_model").Activity} */
    ["mail.activity"];
    /** @type {typeof import("@mail/core/common/canned_response_model").CannedResponse} */
    ["mail.canned.response"];
    /** @type {typeof import("@mail/core/common/follower_model").Follower} */
    ["mail.followers"];
    /** @type {typeof import("@mail/core/common/link_preview_model").LinkPreview} */
    ["mail.link.preview"];
    /** @type {typeof import("@mail/core/common/message_model").Message} */
    ["mail.message"];
    /** @type {typeof import("@mail/core/common/notification_model").Notification} */
    ["mail.notification"];
    /** @type {typeof import("@mail/core/common/message_reactions_model").MessageReactions} */
    MessageReactions;
    /** @type {typeof import("@mail/core/common/persona_model").Persona} */
    Persona;
    /** @type {typeof import("@mail/core/common/country_model").Country} */
    ["res.country"];
    /** @type {typeof import("@mail/core/common/settings_model").Settings} */
    Settings;
    /** @type {typeof import("@mail/core/common/thread_model").Thread} */
    Thread;
    /** @type {typeof import("@mail/core/common/volume_model").Volume} */
    Volume;

    /** This is the current logged partner / guest */
    self = Record.one("Persona");
    /**
     * Indicates whether the current user is using the application through the
     * public page.
     */
    inPublicPage = false;
    odoobot = Record.one("Persona");
    users = {};
    /** @type {number} */
    internalUserGroupId;
    /** @type {number} */
    mt_comment_id;
    /** @type {boolean} */
    hasMessageTranslationFeature;
    imStatusTrackedPersonas = Record.many("Persona", {
        inverse: "storeAsTrackedImStatus",
    });
    hasLinkPreviewFeature = true;
    // messaging menu
    menu = { counter: 0 };
    chatHub = Record.one("ChatHub", { compute: () => ({}) });
    failures = Record.many("Failure", {
        /**
         * @param {import("models").Failure} f1
         * @param {import("models").Failure} f2
         */
        sort: (f1, f2) => f2.lastMessage?.id - f1.lastMessage?.id,
    });
    settings = Record.one("Settings");
    openInviteThread = Record.one("Thread");

    fetchDeferred = new Deferred();
    fetchParams = {};
    fetchReadonly = true;
    fetchSilent = true;

    cannedReponses = this.makeCachedFetchData({ canned_responses: true });

    specialMentions = [
        {
            isSpecial: true,
            label: "everyone",
            channel_types: ["channel", "group"],
            displayName: "Everyone",
            description: _t("Notify everyone"),
        },
    ];

    get initMessagingParams() {
        return {
            init_messaging: {},
        };
    }

    isNotificationPermissionDismissed = Record.attr(false, {
        compute() {
            return (
                browser.localStorage.getItem("mail.user_setting.push_notification_dismissed") ===
                "true"
            );
        },
        /** @this {import("models").DiscussApp} */
        onUpdate() {
            if (this.isNotificationPermissionDismissed) {
                browser.localStorage.setItem(
                    "mail.user_setting.push_notification_dismissed",
                    "true"
                );
            } else {
                browser.localStorage.removeItem("mail.user_setting.push_notification_dismissed");
            }
        },
    });

    messagePostMutex = new Mutex();

    menuThreads = Record.many("Thread", {
        /** @this {import("models").Store} */
        compute() {
            /** @type {import("models").Thread[]} */
            const searchTerm = cleanTerm(this.discuss.searchTerm);
            let threads = Object.values(this.Thread.records).filter(
                (thread) =>
                    (thread.displayToSelf ||
                        (thread.needactionMessages.length > 0 && thread.model !== "mail.box")) &&
                    cleanTerm(thread.displayName).includes(searchTerm)
            );
            const tab = this.discuss.activeTab;
            if (tab !== "main") {
                threads = threads.filter(({ channel_type }) =>
                    this.tabToThreadType(tab).includes(channel_type)
                );
            } else if (tab === "main" && this.env.inDiscussApp) {
                threads = threads.filter(({ channel_type }) =>
                    this.tabToThreadType("mailbox").includes(channel_type)
                );
            }
            return threads;
        },
        /**
         * @this {import("models").Store}
         * @param {import("models").Thread} thread1
         * @param {import("models").Thread} thread2
         */
        sort(thread1, thread2) {
            const compareFunctions = threadCompareRegistry.getAll();
            for (const fn of compareFunctions) {
                const result = fn(thread1, thread2);
                if (result !== undefined) {
                    return result;
                }
            }
            return thread2.localId > thread1.localId ? 1 : -1;
        },
    });

    /**
     * @param {Object} params post message data
     * @param {import("models").Message} tmpMessage the associated temporary message
     */
    async doMessagePost(params, tmpMessage) {
        return this.messagePostMutex.exec(async () => {
            let res;
            try {
                res = await rpc("/mail/message/post", params, { silent: true });
            } catch (err) {
                if (!tmpMessage) {
                    throw err;
                }
                tmpMessage.postFailRedo = () => {
                    tmpMessage.postFailRedo = undefined;
                    tmpMessage.thread.messages.delete(tmpMessage);
                    tmpMessage.thread.messages.add(tmpMessage);
                    this.doMessagePost(params, tmpMessage);
                };
            }
            return res;
        });
    }

    /**
     * @returns {Deferred}
     */
    async fetchData(params, { readonly = true, silent = true } = {}) {
        Object.assign(this.fetchParams, params);
        this.fetchReadonly = this.fetchReadonly && readonly;
        this.fetchSilent = this.fetchSilent && silent;
        const fetchDeferred = this.fetchDeferred;
        this._fetchDataDebounced();
        return fetchDeferred;
    }

    /** Import data received from init_messaging */
    async initialize() {
        await this.fetchData(this.initMessagingParams);
        this.isReady.resolve();
    }

    /**
     * Create a cacheable version of the `fetchData` method. The result of the
     * request is cached once acquired. In case of failure, the deferred is
     * rejected and the cache is reset allowing to retry the request when
     * calling the function again.
     *
     * @param {{[key: string]: boolean}} params Parameters to pass to the `fetchData` method.
     * @returns {{
     *      fetch: () => ReturnType<Store["fetchData"]>,
     *      status: "not_fetched"|"fetching"|"fetched"
     * }}
     */
    makeCachedFetchData(params) {
        let def = null;
        const r = reactive({
            status: "not_fetched",
            fetch: () => {
                if (["fetching", "fetched"].includes(r.status)) {
                    return def;
                }
                r.status = "fetching";
                def = new Deferred();
                this.fetchData(params).then(
                    (result) => {
                        r.status = "fetched";
                        def.resolve(result);
                    },
                    (error) => {
                        r.status = "not_fetched";
                        def.reject(error);
                    }
                );
                return def;
            },
        });
        return r;
    }

    async _fetchDataDebounced() {
        const fetchDeferred = this.fetchDeferred;
        this.fetchParams.context = {
            ...user.context,
            ...this.fetchParams.context,
        };
        rpc(this.fetchReadonly ? "/mail/data" : "/mail/action", this.fetchParams, {
            silent: this.fetchSilent,
        }).then(
            (data) => {
                const recordsByModel = this.insert(data, { html: true });
                fetchDeferred.resolve(recordsByModel);
            },
            (error) => fetchDeferred.reject(error)
        );
        this.fetchDeferred = new Deferred();
        this.fetchParams = {};
        this.fetchReadonly = true;
        this.fetchSilent = true;
    }

    /**
     * @template T
     * @param {T} [dataByModelName={}]
     * @param {Object} [options={}]
     * @returns {{ [K in keyof T]: import("models").Models[K][] }}
     */
    insert(dataByModelName = {}, options = {}) {
        const store = this;
        const pyModels = Object.values(pyToJsModels);
        return Record.MAKE_UPDATE(function storeInsert() {
            const res = {};
            const recordsDataToDelete = [];
            for (const [pyOrJsModelName, data] of Object.entries(dataByModelName)) {
                if (pyModels.includes(pyOrJsModelName)) {
                    console.warn(
                        `store.insert() should receive the python model name instead of “${pyOrJsModelName}”.`
                    );
                }
                const modelName = pyToJsModels[pyOrJsModelName] || pyOrJsModelName;
                if (!store[modelName]) {
                    console.warn(`store.insert() received data for unknown model “${modelName}”.`);
                    continue;
                }
                const insertData = [];
                for (const vals of Array.isArray(data) ? data : [data]) {
                    const extraFields = addFieldsByPyModel[pyOrJsModelName];
                    if (extraFields) {
                        Object.assign(vals, extraFields);
                    }
                    if (vals._DELETE) {
                        delete vals._DELETE;
                        recordsDataToDelete.push([modelName, vals]);
                    } else {
                        insertData.push(vals);
                    }
                }
                const records = store[modelName].insert(insertData, options);
                if (!res[modelName]) {
                    res[modelName] = records;
                } else {
                    const knownRecordIds = new Set(res[modelName].map((r) => r.localId));
                    res[modelName].push(...records.filter((r) => !knownRecordIds.has(r.localId)));
                }
            }
            // Delete after all inserts to make sure a relation potentially registered before the
            // delete doesn't re-add the deleted record by mistake.
            for (const [modelName, vals] of recordsDataToDelete) {
                store[modelName].get(vals)?.delete();
            }
            return res;
        });
    }

    async startMeeting() {
        const thread = await this.createGroupChat({
            default_display_mode: "video_full_screen",
            partners_to: [this.self.id],
        });
        this.ChatWindow.get(thread)?.update({ autofocus: 0 });
        this.env.services["discuss.rtc"].toggleCall(thread, { camera: true });
        this.openInviteThread = thread;
    }

    /**
     * @param {'chat' | 'group'} tab
     * @returns Thread types matching the given tab.
     */
    tabToThreadType(tab) {
        return tab === "chat" ? ["chat", "group"] : [tab];
    }

    handleClickOnLink(ev, thread) {
        const model = ev.target.dataset.oeModel;
        const id = Number(ev.target.dataset.oeId);
        if (ev.target.closest(".o_channel_redirect") && model && id) {
            ev.preventDefault();
            this.Thread.getOrFetch({ model, id }).then((thread) => {
                if (thread) {
                    thread.open();
                }
            });
            return true;
        } else if (ev.target.closest(".o_mail_redirect") && id) {
            ev.preventDefault();
            this.openChat({ partnerId: id });
            return true;
        } else if (ev.target.tagName === "A" && model && id) {
            ev.preventDefault();
            Promise.resolve(
                this.env.services.action.doAction({
                    type: "ir.actions.act_window",
                    res_model: model,
                    views: [[false, "form"]],
                    res_id: id,
                })
            ).then(() => this.onLinkFollowed(thread));
            return true;
        }
        return false;
    }

    onLinkFollowed(fromThread) {}

    setup() {
        super.setup();
        this._fetchDataDebounced = debounce(
            this._fetchDataDebounced,
            Store.FETCH_DATA_DEBOUNCE_DELAY
        );
    }

    /** Provides an override point for when the store service has started. */
    onStarted() {}

    /**
     * Search and fetch for a partner with a given user or partner id.
     * @param {Object} param0
     * @param {number} param0.userId
     * @param {number} param0.partnerId
     * @returns {Promise<import("models").Thread | undefined>}
     */
    async getChat({ userId, partnerId }) {
        const partner = await this.getPartner({ userId, partnerId });
        let chat = partner?.searchChat();
        if (!chat || !chat.is_pinned) {
            chat = await this.joinChat(partnerId || partner?.id);
        }
        if (!chat) {
            this.env.services.notification.add(
                _t("An unexpected error occurred during the creation of the chat."),
                { type: "warning" }
            );
            return;
        }
        return chat;
    }

    /** @returns {number} */
    getLastMessageId() {
        return Object.values(this["mail.message"].records).reduce(
            (lastMessageId, message) => Math.max(lastMessageId, message.id),
            0
        );
    }

    getMentionsFromText(
        body,
        { mentionedChannels = [], mentionedPartners = [], specialMentions = [] } = {}
    ) {
        const validMentions = {};
        validMentions.threads = mentionedChannels.filter((thread) => {
            if (thread.parent_channel_id) {
                return body.includes(
                    `#${thread.parent_channel_id.displayName} > ${thread.displayName}`
                );
            }
            return body.includes(`#${thread.displayName}`);
        });
        validMentions.partners = mentionedPartners.filter((partner) =>
            body.includes(`@${partner.name}`)
        );
        validMentions.specialMentions = this.specialMentions
            .filter((special) => body.includes(`@${special.label}`))
            .map((special) => special.label);
        return validMentions;
    }

    /**
     * Get the parameters to pass to the message post route.
     */
    async getMessagePostParams({ body, postData, thread }) {
        const {
            attachments,
            cannedResponseIds,
            emailAddSignature,
            isNote,
            mentionedChannels,
            mentionedPartners,
        } = postData;
        const subtype = isNote ? "mail.mt_note" : "mail.mt_comment";
        const validMentions = this.getMentionsFromText(body, {
            mentionedChannels,
            mentionedPartners,
        });
        const partner_ids = validMentions?.partners.map((partner) => partner.id) ?? [];
        const recipientEmails = [];
        const recipientAdditionalValues = {};
        if (!isNote) {
            const recipientIds = thread.suggestedRecipients
                .filter((recipient) => recipient.persona && recipient.checked)
                .map((recipient) => recipient.persona.id);
            thread.suggestedRecipients
                .filter((recipient) => recipient.checked && !recipient.persona)
                .forEach((recipient) => {
                    recipientEmails.push(recipient.email);
                    recipientAdditionalValues[recipient.email] = recipient.create_values;
                });
            partner_ids.push(...recipientIds);
        }
        postData = {
            body: await prettifyMessageContent(body, validMentions),
            email_add_signature: emailAddSignature,
            message_type: "comment",
            subtype_xmlid: subtype,
        };
        if (attachments.length) {
            postData.attachment_ids = attachments.map(({ id }) => id);
        }
        if (partner_ids.length) {
            Object.assign(postData, { partner_ids });
        }
        if (thread.model === "discuss.channel" && validMentions?.specialMentions.length) {
            postData.special_mentions = validMentions.specialMentions;
        }
        const params = {
            context: {
                mail_post_autofollow: !isNote && thread.hasWriteAccess,
            },
            post_data: postData,
            thread_id: thread.id,
            thread_model: thread.model,
        };
        if (attachments.length) {
            params.attachment_tokens = attachments.map((attachment) => attachment.access_token);
        }
        if (cannedResponseIds?.length) {
            params.canned_response_ids = cannedResponseIds;
        }
        if (recipientEmails.length) {
            Object.assign(params, {
                partner_emails: recipientEmails,
                partner_additional_values: recipientAdditionalValues,
            });
        }
        return params;
    }

    getNextTemporaryId() {
        const lastMessageId = this.getLastMessageId();
        if (prevLastMessageId === lastMessageId) {
            temporaryIdOffset += 0.01;
        } else {
            prevLastMessageId = lastMessageId;
            temporaryIdOffset = 0.01;
        }
        return lastMessageId + temporaryIdOffset;
    }

    /**
     * Search and fetch for a partner with a given user or partner id.
     * @param {Object} param0
     * @param {number} param0.userId
     * @param {number} param0.partnerId
     * @returns {Promise<import("models").Persona> | undefined}
     */
    async getPartner({ userId, partnerId }) {
        if (userId) {
            let user = this.users[userId];
            if (!user) {
                this.users[userId] = { id: userId };
                user = this.users[userId];
            }
            if (!user.partner_id) {
                const [userData] = await this.env.services.orm.silent.read(
                    "res.users",
                    [user.id],
                    ["partner_id"],
                    { context: { active_test: false } }
                );
                if (userData) {
                    user.partner_id = userData.partner_id[0];
                }
            }
            if (!user.partner_id) {
                this.env.services.notification.add(_t("You can only chat with existing users."), {
                    type: "warning",
                });
                return;
            }
            partnerId = user.partner_id;
        }
        if (partnerId) {
            const partner = this.Persona.insert({ id: partnerId, type: "partner" });
            if (!partner.userId) {
                const [userId] = await this.env.services.orm.silent.search(
                    "res.users",
                    [["partner_id", "=", partnerId]],
                    { context: { active_test: false } }
                );
                if (!userId) {
                    this.env.services.notification.add(
                        _t("You can only chat with partners that have a dedicated user."),
                        { type: "info" }
                    );
                    return;
                }
                partner.userId = userId;
            }
            return partner;
        }
    }

    async joinChat(id, forceOpen = false) {
        const data = await rpc("/discuss/channel/get_or_create_chat", {
            partners_to: [id],
            force_open: forceOpen,
        });
        const { Thread } = this.store.insert(data);
        return Thread[0];
    }

    async openChat(person) {
        const chat = await this.getChat(person);
        chat?.open();
    }

    openDocument({ id, model }) {
        this.env.services.action.doAction({
            type: "ir.actions.act_window",
            res_model: model,
            views: [[false, "form"]],
            res_id: id,
        });
    }

    /**
     * @param {string} searchTerm
     * @param {Thread} thread
     * @param {number|false} [before]
     */
    async searchMessagesInThread(searchTerm, thread, before = false) {
        const { count, data, messages } = await rpc(thread.getFetchRoute(), {
            ...thread.getFetchParams(),
            fetch_params: {
                search_term: await prettifyMessageContent(searchTerm), // formatted like message_post
                before,
            },
        });
        this.insert(data, { html: true });
        return {
            count,
            loadMore: messages.length === this.FETCH_LIMIT,
            messages: this["mail.message"].insert(messages),
        };
    }
}
Store.register();

export const storeService = {
    dependencies: ["bus_service", "ui"],
    stateful: true,
    /**
     * @param {import("@web/env").OdooEnv} env
     * @param {import("services").ServiceFactories} services
     * @returns {import("models").Store}
     */
    start(env, services) {
        const store = makeStore(env);
        store.insert(session.storeData);
        /**
         * Add defaults for `self` and `settings` because in livechat there could be no user and no
         * guest yet (both undefined at init), but some parts of the code that loosely depend on
         * these values will still be executed immediately. Providing a dummy default is enough to
         * avoid crashes, the actual values being filled at livechat init when they are necessary.
         */
        store.self ??= { id: -1, type: "guest" };
        store.settings ??= {};
        store.initialize();
        store.onStarted();
        return store;
    },
};

registry.category("services").add("mail.store", storeService);
