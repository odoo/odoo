// @ts-check
/** @odoo-module native */
import "@mail/core/common/im_status_service";
import "./_models.js";

import { FETCH_DATA_DEBOUNCE_DELAY } from "@mail/core/common/constants";
import { fields, makeStore, Store as BaseStore } from "@mail/core/common/record";
import { attClassObjectToString, prettifyMessageText } from "@mail/utils/common/format";
import {
    initLocalStorageMirror,
    readLocalStorageItem,
    removeLocalStorageItem,
    setLocalStorageItem,
    startLocalStorageMirror,
} from "@mail/utils/common/local_storage";
import { compareDatetime } from "@mail/utils/common/misc";
import { reactive } from "@odoo/owl";
import { loader } from "@web/components/emoji_picker";
import { browser } from "@web/core/browser/browser";
import { isMobileOS } from "@web/core/browser/feature_detection";
import { colorScheme } from "@web/core/color_scheme";
import { makeLogger } from "@web/core/debug/debug_logger";
import { ConnectionLostError, rpc } from "@web/core/network";
import { registry } from "@web/core/registry";
import { _t } from "@web/core/translation";
import { user } from "@web/core/user";
import { Deferred, Mutex } from "@web/core/utils/concurrency";
import { debounce } from "@web/core/utils/timing";
import { session } from "@web/session";

const debugLog = makeLogger("mail.store");

/** @typedef {{isSpecial: true, channel_types: string[], label: string, displayName: string, description: string}} SpecialMention */
const pyToJsModels = {
    "discuss.channel": "Thread",
    "mixin.mail.thread": "Thread",
};

const PUSH_NOTIFICATION_DISMISSED_LS = "mail.user_setting.push_notification_dismissed";

const addFieldsByPyModel = {
    "discuss.channel": { model: "discuss.channel" },
};

export class Store extends BaseStore {
    _makeInsertContext() {
        return { pyModels: Object.values(pyToJsModels) };
    }
    /**
     * @param {{pyModels: string[]}} ctx
     * @param {string} pyOrJsModelName
     * @returns {string}
     */
    _insertModelName(ctx, pyOrJsModelName) {
        if (ctx.pyModels.includes(pyOrJsModelName)) {
            console.warn(
                `store.insert() should receive the python model name instead of “${pyOrJsModelName}”.`,
            );
        }
        return pyToJsModels[pyOrJsModelName] || pyOrJsModelName;
    }
    /**
     * @param {string} pyOrJsModelName
     * @returns {Object|undefined}
     */
    _insertExtraFields(pyOrJsModelName) {
        return addFieldsByPyModel[pyOrJsModelName];
    }

    /** @type {Object<string, string|null>} */
    localStorageValues;
    /** @type {Map<string, Set<(newValue: string|null) => void>>} */
    _localStorageSubscribers;
    FETCH_LIMIT = 30;
    DEFAULT_AVATAR = "/mail/static/src/img/smiley/avatar.jpg";
    isReady = new Deferred();
    self_partner = fields.One("res.partner");
    self_guest = fields.One("mail.guest");
    get self() {
        return this.self_partner || this.self_guest;
    }
    get selfUser() {
        return this.self_partner?.main_user_id;
    }
    get selfIsInternalUser() {
        return Boolean(this.self_partner?.isInternalUser);
    }
    get selfIsAdmin() {
        return Boolean(this.selfUser?.is_admin);
    }
    get selfUsesInbox() {
        return this.selfUser?.notification_type === "inbox";
    }
    allChannels = fields.Many("Thread", {
        inverse: "storeAsAllChannels",
        /** @this {import("models").Store} */
        onUpdate() {
            const busService = this.store.env.services.bus_service;
            if (!busService.isActive && this.allChannels.some((t) => !t.isTransient)) {
                busService.start();
            }
        },
    });
    inPublicPage = false;
    odoobot = fields.One("res.partner");
    useMobileView = fields.Attr(undefined, {
        /** @this {import("models").Store} */
        compute() {
            return this.store.env.services.ui.isSmall || isMobileOS();
        },
    });
    /** @type {number} */
    internalUserGroupId;
    mt_comment = fields.One("mail.message.subtype");
    mt_note = fields.One("mail.message.subtype");
    /** @type {boolean} */
    hasMessageTranslationFeature;
    hasLinkPreviewFeature = true;
    chatHub = fields.One("ChatHub", { compute: () => ({}) });
    messagingMenu = fields.One("MessagingMenu", { compute: () => ({}) });
    failures = fields.Many("Failure", {
        /**
         * @param {import("models").Failure} f1
         * @param {import("models").Failure} f2
         */
        sort: (f1, f2) =>
            Number(f2.lastMessage?.id ?? 0) - Number(f1.lastMessage?.id ?? 0),
    });
    settings = fields.One("Settings");
    emojiLoader = loader;

    /** @type {Array<[string, any, import("./data_response_model").DataResponse]>} */
    fetchParams = [];
    fetchReadonly = true;
    fetchSilent = true;

    /** @type {Map<string, Promise<import("models").Thread|undefined>>} */
    _threadFetchPromises = new Map();
    /** @type {Set<string>} */
    _threadFetchAttempted = new Set();
    /** @type {Set<number>} */
    deletedMessageIds = new Set();

    cannedResponses = this.makeCachedFetchData("mail.canned.response");

    /** @type {SpecialMention[]} */
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
        /** @this {import("models").Store} */
        compute() {
            return (
                readLocalStorageItem(this.store, PUSH_NOTIFICATION_DISMISSED_LS) ===
                "true"
            );
        },
        /** @this {import("models").Store} */
        onUpdate() {
            if (this.isNotificationPermissionDismissed) {
                setLocalStorageItem(this.store, PUSH_NOTIFICATION_DISMISSED_LS, "true");
            } else {
                removeLocalStorageItem(this.store, PUSH_NOTIFICATION_DISMISSED_LS);
            }
        },
    });

    /** @type {Map<string, Mutex>} */
    messagePostMutexes = new Map();

    /**
     * @param {{env?: import("@web/env").OdooEnv}} [ctx]
     * @returns {boolean}
     */
    shouldSimulateDarkTheme(ctx) {
        return (
            (ctx?.env?.inDiscussCallView ||
                ctx?.env?.inCallInvitation ||
                ctx?.env?.isDiscussPipBanner ||
                ctx?.env?.inWelcomePage) &&
            this.isOdooWhiteTheme &&
            !ctx?.env?.inMeetingSideActions &&
            !ctx?.env?.inDiscussActionPanel
        );
    }

    /**
     * @param {{env?: import("@web/env").OdooEnv}} [ctx]
     * @returns {string}
     */
    discussDropdownMenuClass(ctx) {
        const simulateDarkTheme = this.shouldSimulateDarkTheme(ctx);
        return attClassObjectToString({
            "o-discuss-dropdownMenu d-flex flex-column border-secondary": true,
            "o-simulateDarkTheme": simulateDarkTheme,
            "bg-view": !simulateDarkTheme,
        });
    }

    standaloneInboxMessages = fields.Many("mail.message", {
        /** @this {import("models").Store} */
        compute() {
            const messages = (this.store.inbox?.messages ?? []).filter(
                (m) => !m.thread,
            );
            return messages.sort(
                (m1, m2) => compareDatetime(m2.datetime, m1.datetime) || m2.id - m1.id,
            );
        },
    });

    /**
     * @param {Object} params
     * @param {import("models").Message} tmpMessage
     */
    async doMessagePost(params, tmpMessage) {
        const mutexKey = `${params.thread_model},${params.thread_id}`;
        let mutex = this.messagePostMutexes.get(mutexKey);
        if (!mutex) {
            mutex = new Mutex();
            this.messagePostMutexes.set(mutexKey, mutex);
        }
        try {
            return await mutex.exec(async () => {
                let res;
                const endPost = debugLog.perf("message post");
                debugLog.logic("doMessagePost", () => ({
                    mutexKey,
                    tmp: tmpMessage?.id,
                }));
                try {
                    res = await rpc("/mail/message/post", params, { silent: true });
                    endPost({ thread: mutexKey });
                } catch (err) {
                    endPost({ thread: mutexKey, failed: true });
                    debugLog.logic("doMessagePost failed", () => ({
                        mutexKey,
                        retryOffered: Boolean(tmpMessage),
                        message: err?.message,
                    }));
                    if (!tmpMessage) {
                        throw err;
                    }
                    console.warn("Failed to post message, retry offered", err);
                    tmpMessage.postFailRedo = async () => {
                        debugLog.logic("doMessagePost retry", () => ({
                            mutexKey,
                            tmp: tmpMessage.id,
                        }));
                        tmpMessage.postFailRedo = undefined;
                        const thread = tmpMessage.thread;
                        thread.messages.delete(tmpMessage);
                        thread.messages.add(tmpMessage);
                        const data = await this.doMessagePost(params, tmpMessage);
                        if (data) {
                            thread.processMessagePostResponse(data, tmpMessage);
                        }
                    };
                }
                return res;
            });
        } finally {
            if (!mutex.locked && this.messagePostMutexes.get(mutexKey) === mutex) {
                this.messagePostMutexes.delete(mutexKey);
            }
        }
    }

    /**
     * @param {string} name
     * @param {any} [params]
     * @param {Object} [options={}]
     * @param {boolean} [options.requestData=false]
     * @param {boolean} [options.readonly=true]
     * @param {boolean} [options.silent=true]
     * @param {(queued: any, incoming: any) => any} [options.merge]
     * @returns {Promise<any>}
     */
    async fetchStoreData(
        name,
        params,
        { requestData = false, readonly = true, silent = true, merge } = {},
    ) {
        if (merge && !requestData) {
            const queued = this.fetchParams.find(
                ([queuedName, , queuedRequest]) =>
                    queuedName === name && queuedRequest._autoResolve,
            );
            if (queued) {
                debugLog.logic("fetchStoreData merged into queued request", () => ({
                    name,
                }));
                queued[1] = merge(queued[1], params);
                return queued[2]._resultDef;
            }
        }
        debugLog.pipeline("fetchStoreData queue", () => ({
            name,
            requestData,
            readonly,
            silent,
            queued: this.fetchParams.length + 1,
        }));
        const dataRequest =
            /** @type {typeof import("./data_response_model").DataResponse} */ (
                this.Models.DataResponse
            ).createRequest();
        dataRequest._autoResolve = !requestData;
        this.fetchParams.push([name, params, dataRequest]);
        this.fetchReadonly = this.fetchReadonly && readonly;
        this.fetchSilent = this.fetchSilent && silent;
        this._fetchStoreDataDebounced();
        return dataRequest._resultDef;
    }

    async initialize() {
        if (this._initializePromise) {
            return this._initializePromise;
        }
        const endInit = debugLog.perf("initialize");
        this._initializePromise = (async () => {
            for (;;) {
                try {
                    await Promise.all(
                        this._getInitialFetchNames().map((name) =>
                            this.fetchStoreData(name),
                        ),
                    );
                    break;
                } catch (error) {
                    if (!(error instanceof ConnectionLostError)) {
                        debugLog.logic("initialize failed", () => ({
                            message: error?.message,
                        }));
                        this._initializePromise = undefined;
                        throw error;
                    }
                    debugLog.logic("initialize waiting for bus reconnect");
                    await this._busReconnected();
                }
            }
            this.isReady.resolve();
            endInit({ fetched: this._getInitialFetchNames() });
        })();
        return this._initializePromise;
    }

    _getInitialFetchNames() {
        return ["init_messaging"];
    }

    _busReconnected() {
        return new Promise((resolve) =>
            this.env.services.bus_service.addEventListener("BUS:RECONNECT", resolve, {
                once: true,
            }),
        );
    }

    /**
     * @param {string} name
     * @param {*} params
     * @returns {{ fetch: () => ReturnType<Store["fetchStoreData"]>, invalidate: () => void, status: "not_fetched"|"fetching"|"fetched" }}
     */
    makeCachedFetchData(name, params) {
        let def = null;
        let invalidatedWhileFetching = false;
        const r = reactive({
            status: /** @type {"not_fetched" | "fetching" | "fetched"} */ (
                "not_fetched"
            ),
            fetch: () => {
                if (["fetching", "fetched"].includes(r.status)) {
                    debugLog.logic("cachedFetchData hit", () => ({
                        name,
                        status: r.status,
                    }));
                    return def;
                }
                debugLog.pipeline("cachedFetchData fetch", () => ({ name }));
                r.status = "fetching";
                invalidatedWhileFetching = false;
                def = new Deferred();
                const fetchDef = def;
                this.fetchStoreData(name, params).then(
                    (result) => {
                        if (fetchDef === def) {
                            r.status = invalidatedWhileFetching
                                ? "not_fetched"
                                : "fetched";
                        }
                        fetchDef.resolve(result);
                    },
                    (error) => {
                        if (fetchDef === def) {
                            r.status = "not_fetched";
                        }
                        fetchDef.reject(error);
                    },
                );
                return def;
            },
            invalidate: () => {
                debugLog.logic("cachedFetchData invalidate", () => ({
                    name,
                    status: r.status,
                }));
                if (r.status === "fetching") {
                    invalidatedWhileFetching = true;
                } else {
                    r.status = "not_fetched";
                }
            },
        });
        return r;
    }

    _fetchStoreDataDebounced() {
        const fetchParams = this.fetchParams;
        const endFetch = debugLog.perf(
            this.fetchReadonly ? "/mail/data" : "/mail/action",
        );
        debugLog.pipeline("fetchStoreData", () => ({
            names: fetchParams.map(([name]) => name),
            readonly: this.fetchReadonly,
        }));
        this._fetchStoreDataRpc(
            fetchParams.map(([name, params, dataRequest]) => {
                if (dataRequest._autoResolve) {
                    if (params !== undefined) {
                        return [name, params];
                    } else {
                        return name;
                    }
                } else {
                    return [name, params, dataRequest.id];
                }
            }),
        ).then(
            (data) => {
                let insertError;
                endFetch({
                    requests: fetchParams.length,
                    models: Object.keys(data || {}),
                });
                try {
                    this.insert(data);
                } catch (error) {
                    insertError = error;
                }
                for (const [name, , dataRequest] of fetchParams) {
                    if (!dataRequest.exists()) {
                        continue;
                    }
                    if (insertError) {
                        dataRequest._resultDef.reject(insertError);
                    } else if (dataRequest._autoResolve) {
                        dataRequest._resolve = true;
                        continue;
                    } else {
                        debugLog.logic("fetchStoreData request unresolved", () => ({
                            name,
                            requestId: dataRequest.id,
                        }));
                        dataRequest._resultDef.reject(
                            new Error(
                                `Data request "${name}" (id ${dataRequest.id}) was not resolved by the server response. The server route probably lacks a "resolve_data_request()" call.`,
                            ),
                        );
                    }
                    dataRequest.delete();
                }
                if (insertError) {
                    console.error("Failed to insert fetched mail data:", insertError);
                }
            },
            (error) => {
                endFetch({ requests: fetchParams.length, failed: true });
                for (const [, , dataRequest] of fetchParams) {
                    dataRequest._resultDef.reject(error);
                    if (dataRequest.exists()) {
                        dataRequest.delete();
                    }
                }
            },
        );
        this.fetchParams = [];
        this.fetchReadonly = true;
        this.fetchSilent = true;
    }

    /**
     * @param {Object} fetchParams
     * @returns {Promise<Object>}
     */
    _fetchStoreDataRpc(fetchParams) {
        return rpc(
            this.fetchReadonly ? "/mail/data" : "/mail/action",
            { fetch_params: fetchParams, context: user.context },
            { silent: this.fetchSilent },
        );
    }

    setup() {
        super.setup();
        initLocalStorageMirror(this);
        this._prevLastMessageId = null;
        this._temporaryIdOffset = 0.01;
        this._fetchStoreDataDebounced = debounce(
            this._fetchStoreDataDebounced,
            FETCH_DATA_DEBOUNCE_DELAY,
        );
    }

    /** @this {import("models").Store} */
    onStarted() {
        this.isOdooWhiteTheme = !colorScheme.isDark || this.inPublicPage;
        /** @param {MessageEvent} ev */
        const onServiceWorkerMessage = (ev) => {
            const { data = {} } = ev;
            const { type, payload } = data;
            if (type === "notification-display-request") {
                const { correlationId, model, res_id } = payload;
                const thread = this.Thread.get({ model, id: res_id });
                let isTabFocused;
                try {
                    isTabFocused = parent.document.hasFocus();
                } catch {}
                const isInbox = this.store.selfUsesInbox && model !== "discuss.channel";
                debugLog.logic("serviceWorker notification-display-request", () => ({
                    model,
                    res_id,
                    isTabFocused,
                    isDisplayed: thread?.isDisplayed,
                    isInbox,
                }));
                if ((isTabFocused && thread?.isDisplayed) || isInbox) {
                    (
                        ev.source ?? browser.navigator.serviceWorker.controller
                    )?.postMessage({
                        type: "notification-display-response",
                        payload: { correlationId },
                    });
                }
            }
            if (type === "notification-displayed") {
                this.onPushNotificationDisplayed(payload);
            }
        };
        browser.navigator.serviceWorker?.addEventListener(
            "message",
            onServiceWorkerMessage,
        );
    }

    /** @param {{model: string, res_id: number}} payload */
    onPushNotificationDisplayed(payload) {
        debugLog.logic("onPushNotificationDisplayed", () => payload);
        if (["mixin.mail.thread", "discuss.channel"].includes(payload.model)) {
            this.env.services["mail.out_of_focus"]._playSound();
        }
    }

    /**
     * @param {Object} param0
     * @param {number} [param0.userId]
     * @param {number} [param0.partnerId]
     * @returns {Promise<import("models").Thread | undefined>}
     */
    async getChat({ userId, partnerId }) {
        const partner = await this.getPartner({ userId, partnerId });
        if (!partner) {
            debugLog.logic("getChat no partner", () => ({ userId, partnerId }));
            return;
        }
        let chat = partner.searchChat();
        debugLog.logic("getChat", () => ({
            partnerId: partner.id,
            localChat: chat?.localId,
            pinned: chat?.self_member_id?.is_pinned,
        }));
        if (!chat?.self_member_id?.is_pinned) {
            chat = await this.joinChat(partner.id);
        }
        if (!chat) {
            this.env.services.notification.add(
                _t("An unexpected error occurred during the creation of the chat."),
                { type: "warning" },
            );
            return;
        }
        return chat;
    }

    /** @type {number} */
    lastKnownMessageId = 0;

    /** @returns {number} */
    getLastMessageId() {
        return this.lastKnownMessageId;
    }

    /** @param {string} recordName */
    notifySendFromMailbox(recordName) {
        this.env.services.notification.add(_t('Message posted on "%s"', recordName), {
            type: "info",
        });
    }

    getNextTemporaryId() {
        const lastMessageId = this.getLastMessageId();
        if (this._prevLastMessageId === lastMessageId) {
            this._temporaryIdOffset += 0.01;
        } else {
            this._prevLastMessageId = lastMessageId;
            this._temporaryIdOffset = 0.01;
        }
        return lastMessageId + this._temporaryIdOffset;
    }

    /**
     * @param {Object} param0
     * @param {number} [param0.userId]
     * @param {number} [param0.partnerId]
     * @returns {Promise<import("models").ResPartner|undefined>}
     */
    async getPartner({ userId, partnerId }) {
        if (userId) {
            const partner = await this["res.users"]
                .insert({ id: userId })
                .fetchPartner();
            if (!partner) {
                debugLog.logic("getPartner user without partner", () => ({ userId }));
                this.env.services.notification.add(
                    _t("You can only chat with existing users."),
                    {
                        type: "warning",
                    },
                );
                return;
            }
            partnerId = partner.id;
        }
        if (partnerId) {
            const partner = this["res.partner"].insert({ id: partnerId });
            if (!partner.main_user_id) {
                const [userId] = await this.env.services.orm.silent.search(
                    "res.users",
                    [["partner_id", "=", partnerId]],
                    {
                        context: { active_test: false },
                        order: "active desc, share asc, id asc",
                    },
                );
                if (!userId) {
                    debugLog.logic("getPartner partner without user", () => ({
                        partnerId,
                    }));
                    this.env.services.notification.add(
                        _t(
                            "You can only chat with partners that have a dedicated user.",
                        ),
                        { type: "info" },
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

    /**
     * @param {number} id
     * @param {boolean} [forceOpen=false]
     * @returns {Promise<import("models").Thread>}
     */
    async joinChat(id, forceOpen = false) {
        debugLog.logic("joinChat", () => ({ partnerId: id, forceOpen }));
        const { channel } = await this.fetchStoreData(
            "/discuss/get_or_create_chat",
            { partners_to: [id] },
            { readonly: false, requestData: true },
        );
        if (forceOpen) {
            await channel.open({ focus: true });
        }
        return channel;
    }

    /** @param {import("models").Persona|Object} person */
    async openChat(person) {
        const chat = await this.getChat(person);
        chat?.open({ focus: true });
    }

    /**
     * @param {Object} document
     * @param {number} document.id
     * @param {string} document.model
     */
    openDocument({ id, model }) {
        debugLog.logic("openDocument", () => ({ id, model }));
        this.env.services.action.doAction({
            type: "ir.actions.act_window",
            res_model: model,
            views: [[false, "form"]],
            res_id: id,
        });
    }

    /**
     * @param {MouseEvent} ev
     * @param {number} id
     */
    onClickPartnerMention(ev, id) {
        this.openChat({ partnerId: id });
    }

    /**
     * @param {string} searchTerm
     * @param {import("models").Thread} thread
     * @param {number | false} before
     * @param {true|false|undefined} is_notification
     */
    async searchMessagesInThread(searchTerm, thread, before, is_notification) {
        const endSearch = debugLog.perf("searchMessagesInThread");
        const { count, count_is_capped, data, messages } = await rpc(
            thread.getFetchRoute(),
            {
                ...thread.getFetchParams(),
                fetch_params: {
                    is_notification,
                    search_term: await prettifyMessageText(searchTerm),
                    before,
                },
            },
        );
        endSearch({ thread: thread.localId, count, results: messages.length });
        this.insert(data);
        return {
            count,
            countIsCapped: Boolean(count_is_capped),
            loadMore: messages.length === this.FETCH_LIMIT,
            messages: this["mail.message"].insert(messages),
        };
    }
}
Store.register();

export const storeService = {
    dependencies: ["bus_service", "im_status", "ui", "popover"],
    /**
     * @param {import("@web/env").OdooEnv} env
     * @param {import("services").ServiceFactories} services
     * @returns {import("models").Store}
     */
    start(env, services) {
        const endStart = debugLog.perf("service start");
        const store = makeStore(env);
        startLocalStorageMirror(store);
        store.insert(session.storeData);
        debugLog.lifecycle("service start", () => ({
            sessionModels: Object.keys(session.storeData || {}),
        }));
        services.bus_service.addEventListener("BUS:RECONNECT", () => {
            debugLog.lifecycle("bus reconnected", () => ({
                threadFetchAttempted: store._threadFetchAttempted.size,
            }));
            store._threadFetchAttempted.clear();
        });
        store.self_guest ??= /** @type {typeof store.self_guest} */ (
            /** @type {unknown} */ ({ id: -1 })
        );
        store.settings ??= /** @type {typeof store.settings} */ (
            /** @type {unknown} */ ({})
        );
        store.onStarted();
        endStart();
        return store;
    },
};

registry.category("services").add("mail.store", storeService);
