import { Store as BaseStore, fields, makeStore, storeInsertFns } from "@mail/core/common/record";
import { threadCompareRegistry } from "@mail/core/common/thread_compare";
import { cleanTerm, prettifyMessageContent } from "@mail/utils/common/format";

import { reactive } from "@odoo/owl";

import { _t } from "@web/core/l10n/translation";
import { rpc } from "@web/core/network/rpc";
import { registry } from "@web/core/registry";
import { user } from "@web/core/user";
import { Deferred, Mutex } from "@web/core/utils/concurrency";
import { debounce } from "@web/core/utils/timing";
import { session } from "@web/session";
import { browser } from "@web/core/browser/browser";
import { loader } from "@web/core/emoji_picker/emoji_picker";
import { patch } from "@web/core/utils/patch";
import { isMobileOS } from "@web/core/browser/feature_detection";

/**
 * @typedef {{isSpecial: boolean, channel_types: string[], label: string, displayName: string, description: string}} SpecialMention
 */

let prevLastMessageId = null;
let temporaryIdOffset = 0.01;

export const pyToJsModels = {
    "discuss.channel": "Thread",
    "mail.thread": "Thread",
};

export const addFieldsByPyModel = {
    "discuss.channel": { model: "discuss.channel" },
    "mail.guest": { type: "guest" },
    "res.partner": { type: "partner" },
};

patch(storeInsertFns, {
    makeContext(store) {
        if (!(store instanceof Store)) {
            return super.makeContext(...arguments);
        }
        return { pyModels: Object.values(pyToJsModels) };
    },
    getActualModelName(store, ctx, pyOrJsModelName) {
        if (!(store instanceof Store)) {
            return super.getActualModelName(...arguments);
        }
        if (ctx.pyModels.includes(pyOrJsModelName)) {
            console.warn(
                `store.insert() should receive the python model name instead of “${pyOrJsModelName}”.`
            );
        }
        return pyToJsModels[pyOrJsModelName] || pyOrJsModelName;
    },
    getExtraFieldsFromModel(store, pyOrJsModelName) {
        if (!(store instanceof Store)) {
            return super.getExtraFieldsFromModel(...arguments);
        }
        return addFieldsByPyModel[pyOrJsModelName];
    },
});

export class Store extends BaseStore {
    static FETCH_DATA_DEBOUNCE_DELAY = 1;
    static OTHER_LONG_TYPING = 60000;
    static IM_STATUS_DEBOUNCE_DELAY = 1000;

    FETCH_LIMIT = 30;
    DEFAULT_AVATAR = "/mail/static/src/img/smiley/avatar.jpg";
    isReady = new Deferred();
    /** This is the current logged partner / guest */
    self_partner = fields.One("res.partner");
    self_guest = fields.One("mail.guest");
    get self() {
        return this.self_partner || this.self_guest;
    }
    allChannels = fields.Many("Thread", {
        inverse: "storeAsAllChannels",
        onUpdate() {
            const busService = this.store.env.services.bus_service;
            if (!busService.isActive && this.allChannels.some((t) => !t.isTransient)) {
                busService.start();
            }
        },
    });
    /**
     * Indicates whether the current user is using the application through the
     * public page.
     */
    inPublicPage = false;
    odoobot = fields.One("res.partner");
    useMobileView = fields.Attr(undefined, {
        compute() {
            return this.store.env.services.ui.isSmall || isMobileOS();
        },
    });
    users = {};
    /** @type {number} */
    internalUserGroupId;
    mt_comment = fields.One("mail.message.subtype");
    mt_note = fields.One("mail.message.subtype");
    /** @type {boolean} */
    hasMessageTranslationFeature;
    hasLinkPreviewFeature = true;
    // messaging menu
    menu = { counter: 0 };
    chatHub = fields.One("ChatHub", { compute: () => ({}) });
    failures = fields.Many("Failure", {
        /**
         * @param {import("models").Failure} f1
         * @param {import("models").Failure} f2
         */
        sort: (f1, f2) => f2.lastMessage?.id - f1.lastMessage?.id,
    });
    settings = fields.One("Settings");
    emojiLoader = loader;

    /** @type {[[string, any, import("models").DataResponse]]} */
    fetchParams = [];
    fetchReadonly = true;
    fetchSilent = true;

    cannedReponses = this.makeCachedFetchData("mail.canned.response");

    specialMentions = [
        {
            isSpecial: true,
            label: "everyone",
            channel_types: ["channel", "group"],
            displayName: "Everyone",
            description: _t("Notify everyone"),
        },
    ];

    isNotificationPermissionDismissed = fields.Attr(false, {
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

    menuThreads = fields.Many("Thread", {
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
            if (tab === "inbox") {
                threads = threads.filter(({ channel_type }) =>
                    this.tabToThreadType("mailbox").includes(channel_type)
                );
            } else if (tab !== "notification") {
                threads = threads.filter(({ channel_type }) =>
                    this.tabToThreadType(tab).includes(channel_type)
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
     * @param {string} name
     * @param {any} params
     * @param {Object} [options={}]
     * @param {boolean} [options.requestData=false] when set to true, the return promise will
     *  resolve only when the requested data are returned (the data might come later, from another
     *  RPC or a bus notification for example). When set to false (the default), the return promise
     *  will resolve as soon as the RPC is done. This is intended to be true only for requests that
     *  will be resolved server side with `resolve_data_request`.
     * @param {boolean} [options.readonly=true] when set to false, the server will open a read-write
     *  cursor to process this request which is necessary if the request is expected to change data.
     * @param {boolean} [options.silent=true]
     * @returns {Deferred}
     */
    async fetchStoreData(
        name,
        params,
        { requestData = false, readonly = true, silent = true } = {}
    ) {
        const dataRequest = this.DataResponse.createRequest();
        dataRequest._autoResolve = !requestData;
        this.fetchParams.push([name, params, dataRequest]);
        this.fetchReadonly = this.fetchReadonly && readonly;
        this.fetchSilent = this.fetchSilent && silent;
        this._fetchStoreDataDebounced();
        return dataRequest._resultDef;
    }

    /** Import data received from init_messaging */
    async initialize() {
        await this.fetchStoreData("init_messaging");
        this.isReady.resolve();
    }

    /**
     * Create a cacheable version of the `fetchStoreData` method. The result of the
     * request is cached once acquired. In case of failure, the deferred is
     * rejected and the cache is reset allowing to retry the request when
     * calling the function again.
     *
     * @param {string} name
     * @param {*} params Parameters to pass to the `fetchStoreData` method.
     * @returns {{
     *      fetch: () => ReturnType<Store["fetchStoreData"]>,
     *      status: "not_fetched"|"fetching"|"fetched"
     * }}
     */
    makeCachedFetchData(name, params) {
        let def = null;
        const r = reactive({
            status: "not_fetched",
            fetch: () => {
                if (["fetching", "fetched"].includes(r.status)) {
                    return def;
                }
                r.status = "fetching";
                def = new Deferred();
                this.fetchStoreData(name, params).then(
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

    _fetchStoreDataDebounced() {
        const fetchParams = this.fetchParams;
        this._fetchStoreDataRpc(
            fetchParams.map(([name, params, dataRequest]) => {
                if (dataRequest._autoResolve) {
                    /**
                     * Auto-resolve requests don't need to pass any data request id as the server is
                     * expected to not return anything specific for them. It would work if id are
                     * given but it's more bytes on the network and more noise in the logs/tests.
                     */
                    if (params !== undefined) {
                        return [name, params];
                    } else {
                        // In a similar reasoning, also remove empty params.
                        return name;
                    }
                } else {
                    return [name, params, dataRequest.id];
                }
            })
        ).then(
            (data) => {
                this.insert(data);
                for (const [, , dataRequest] of fetchParams) {
                    if (dataRequest._autoResolve) {
                        dataRequest._resolve = true;
                    }
                }
            },
            (error) => {
                for (const [, , dataRequest] of fetchParams) {
                    dataRequest._resultDef.reject(error);
                }
            }
        );
        this.fetchParams = [];
        this.fetchReadonly = true;
        this.fetchSilent = true;
    }

    _fetchStoreDataRpc(fetchParams) {
        const context = {
            ...user.context,
            allowed_company_ids: user.allowedCompanies.map((c) => c.id),
        };
        return rpc(
            this.fetchReadonly ? "/mail/data" : "/mail/action",
            { fetch_params: fetchParams, context },
            { silent: this.fetchSilent }
        );
    }

    async startMeeting() {
        const thread = await this.createGroupChat({
            default_display_mode: "video_full_screen",
            partners_to: [this.self.id],
        });
        await this.store.chatHub.initPromise;
        this.ChatWindow.get(thread)?.update({ autofocus: 0 });
        await this.env.services["discuss.rtc"].toggleCall(thread, { camera: true });
        this.rtc.enterFullscreen({ keepBrowserHeader: true, initialSidePanel: "invite" });
    }

    /**
     * @param {'chat' | 'group'} tab
     * @returns Thread types matching the given tab.
     */
    tabToThreadType(tab) {
        return tab === "chat" ? ["chat", "group"] : [tab];
    }

    handleClickOnLink(ev, thread) {
        const link = ev.target.closest("a");
        if (!link) {
            return;
        }
        const model = link.dataset.oeModel;
        const id = Number(link.dataset.oeId);
        if (link.classList.contains("o_channel_redirect") && model && id) {
            ev.preventDefault();
            this.Thread.getOrFetch({ model, id }).then((thread) => {
                if (thread) {
                    thread.open({ focus: true });
                } else {
                    this.env.services.notification.add(_t("This thread is no longer available."), {
                        type: "danger",
                    });
                }
            });
            return true;
        } else if (link.classList.contains("o_mail_redirect") && id) {
            ev.preventDefault();
            this.openChat({ partnerId: id });
            return true;
        } else if (link.classList.contains("o_message_redirect_transformed") && id) {
            const message = this["mail.message"].get(id);
            const targetThread = message?.thread;
            if (targetThread) {
                targetThread.checkReadAccess().then((hasAccess) => {
                    if (hasAccess) {
                        targetThread.highlightMessage = message;
                        const wasOpen = targetThread.open({ focus: true });
                        if (!wasOpen) {
                            window.open(link.href);
                        }
                    } else {
                        if (this.self_partner) {
                            this.env.services.notification.add(
                                _t("You do not have the permission to access this thread."),
                                { type: "warning" }
                            );
                        } else {
                            window.open(link.href);
                        }
                    }
                });
                ev.preventDefault();
                return true;
            }
        }
        return false;
    }

    setup() {
        super.setup();
        this._fetchStoreDataDebounced = debounce(
            this._fetchStoreDataDebounced,
            Store.FETCH_DATA_DEBOUNCE_DELAY
        );
    }

    /** Provides an override point for when the store service has started. */
    onStarted() {
        navigator.serviceWorker?.addEventListener("message", ({ data = {} }) => {
            const { type, payload } = data;
            if (type === "notification-display-request") {
                const { correlationId, model, res_id } = payload;
                const thread = this.Thread.get({ model, id: res_id });
                let isTabFocused;
                try {
                    isTabFocused = parent.document.hasFocus();
                } catch {
                    // assumes tab not focused: parent.document from iframe triggers CORS error
                }
                if (isTabFocused && thread?.isDisplayed) {
                    navigator.serviceWorker.controller?.postMessage({
                        type: "notification-display-response",
                        payload: { correlationId },
                    });
                }
            }
            if (
                type === "notification-displayed" &&
                ["mail.thread", "discuss.channel"].includes(payload.model)
            ) {
                this.env.services["mail.out_of_focus"]._playSound();
            }
        });
    }

    /**
     * Search and fetch for a partner with a given user or partner id.
     * @param {Object} param0
     * @param {number} param0.userId
     * @param {number} param0.partnerId
     * @returns {Promise<import("models").Thread | undefined>}
     */
    async getChat({ userId, partnerId }) {
        const partner = await this.getPartner({ userId, partnerId });
        if (!partner) {
            return;
        }
        let chat = partner.searchChat();
        if (!chat?.selfMember?.is_pinned) {
            chat = await this.joinChat(partner.id);
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
        { mentionedChannels = [], mentionedPartners = [], mentionedRoles = [] } = {}
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
        validMentions.roles = mentionedRoles.filter((role) => body.includes(`@${role.name}`));
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
            mentionedRoles,
        } = postData;
        const subtype = isNote ? "mail.mt_note" : "mail.mt_comment";
        const validMentions = this.getMentionsFromText(body, {
            mentionedChannels,
            mentionedPartners,
            mentionedRoles,
        });
        const partner_ids = validMentions?.partners.map((partner) => partner.id) ?? [];
        const role_ids = validMentions?.roles.map((role) => role.id) ?? [];
        const recipientEmails = [];
        if (!isNote) {
            const allRecipients = [...thread.suggestedRecipients, ...thread.additionalRecipients];
            const recipientIds = allRecipients
                .filter((recipient) => recipient.persona)
                .map((recipient) => recipient.persona.id);
            allRecipients
                .filter((recipient) => !recipient.persona)
                .forEach((recipient) => {
                    recipientEmails.push(recipient.email);
                });
            partner_ids.push(...recipientIds);
        }
        postData = {
            body: await prettifyMessageContent(body, { validMentions }),
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
        if (role_ids.length) {
            Object.assign(postData, { role_ids });
        }
        if (thread.model === "discuss.channel" && validMentions?.specialMentions.length) {
            postData.special_mentions = validMentions.specialMentions;
        }
        const params = {
            // Changed in 18.2+: finally get rid of autofollow, following should be done manually
            post_data: postData,
            thread_id: thread.id,
            thread_model: thread.model,
        };
        if (attachments.length) {
            params.attachment_tokens = attachments.map((attachment) => attachment.ownership_token);
        }
        if (cannedResponseIds?.length) {
            params.canned_response_ids = cannedResponseIds;
        }
        if (recipientEmails.length) {
            Object.assign(params, {
                partner_emails: recipientEmails,
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
            const partner = this["res.partner"].insert({ id: partnerId });
            if (!partner.main_user_id) {
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
                if (!partner.main_user_id) {
                    partner.main_user_id = userId;
                }
            }
            return partner;
        }
    }

    async joinChat(id, forceOpen = false) {
        const { channel } = await this.fetchStoreData(
            "/discuss/get_or_create_chat",
            { partners_to: [id] },
            { readonly: false, requestData: true }
        );
        if (forceOpen) {
            await channel.open({ focus: true });
        }
        return channel;
    }

    async openChat(person) {
        const chat = await this.getChat(person);
        chat?.open({ focus: true });
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
        this.insert(data);
        return {
            count,
            loadMore: messages.length === this.FETCH_LIMIT,
            messages: this["mail.message"].insert(messages),
        };
    }
}
Store.register();

export const storeService = {
    dependencies: ["bus_service", "im_status", "ui"],
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
        store.self_guest ??= { id: -1 };
        store.settings ??= {};
        store.initialize();
        store.onStarted();
        return store;
    },
};

registry.category("services").add("mail.store", storeService);
