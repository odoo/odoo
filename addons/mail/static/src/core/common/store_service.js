/* @odoo-module */

import { BaseStore, makeStore, Record } from "@mail/core/common/record";

import { router } from "@web/core/browser/router";
import { rpc } from "@web/core/network/rpc";
import { registry } from "@web/core/registry";
import { user } from "@web/core/user";
import { Deferred } from "@web/core/utils/concurrency";
import { debounce } from "@web/core/utils/timing";
import { session } from "@web/session";

export class Store extends BaseStore {
    static FETCH_DATA_DEBOUNCE_DELAY = 1;

    /** @returns {import("models").Store|import("models").Store[]} */
    static insert() {
        return super.insert(...arguments);
    }

    /** @type {typeof import("@mail/core/web/activity_model").Activity} */
    Activity;
    /** @type {typeof import("@mail/core/common/attachment_model").Attachment} */
    Attachment;
    /** @type {typeof import("@mail/core/common/canned_response_model").CannedResponse} */
    CannedResponse;
    /** @type {typeof import("@mail/core/common/channel_member_model").ChannelMember} */
    ChannelMember;
    /** @type {typeof import("@mail/core/common/chat_window_model").ChatWindow} */
    ChatWindow;
    /** @type {typeof import("@mail/core/common/composer_model").Composer} */
    Composer;
    /** @type {typeof import("@mail/core/common/discuss_app_model").DiscussApp} */
    DiscussApp;
    /** @type {typeof import("@mail/core/common/discuss_app_category_model").DiscussAppCategory} */
    DiscussAppCategory;
    /** @type {typeof import("@mail/core/common/failure_model").Failure} */
    Failure;
    /** @type {typeof import("@mail/core/common/follower_model").Follower} */
    Follower;
    /** @type {typeof import("@mail/core/common/link_preview_model").LinkPreview} */
    LinkPreview;
    /** @type {typeof import("@mail/core/common/message_model").Message} */
    Message;
    /** @type {typeof import("@mail/core/common/message_reactions_model").MessageReactions} */
    MessageReactions;
    /** @type {typeof import("@mail/core/common/notification_model").Notification} */
    Notification;
    /** @type {typeof import("@mail/core/common/persona_model").Persona} */
    Persona;
    /** @type {typeof import("@mail/discuss/call/common/rtc_session_model").RtcSession} */
    RtcSession;
    /** @type {typeof import("@mail/core/common/settings_model").Settings} */
    Settings;
    /** @type {typeof import("@mail/core/common/thread_model").Thread} */
    Thread;
    /** @type {typeof import("@mail/core/common/volume_model").Volume} */
    Volume;

    /** @type {number} */
    action_discuss_id;
    /** @type {"not_fetched"|"fetching"|"fetched"} */
    fetchCannedResponseState = "not_fetched";
    fetchCannedResponseDeferred;
    lastChannelSubscription = "";
    /** This is the current logged partner / guest */
    self = Record.one("Persona");
    /**
     * The last id of bus notification at the time for fetch init_messaging.
     * When receiving a notification:
     * - if id greater than this value: the notification is newer than init_messaging state.
     * - if same id or lower: the notification is older than init_messaging state.
     * This is useful to determine whether we should increment or decrement a counter based
     * on init_messaging state.
     */
    initBusId = 0;
    /**
     * Indicates whether the current user is using the application through the
     * public page.
     */
    inPublicPage = false;
    odoobot = Record.one("Persona");
    /** @type {boolean} */
    odoobotOnboarding;
    users = {};
    /** @type {number} */
    internalUserGroupId;
    /** @type {number} */
    mt_comment_id;
    /** @type {boolean} */
    hasMessageTranslationFeature;
    imStatusTrackedPersonas = Record.many("Persona", {
        /** @this {import("models").Store} */
        compute() {
            return Object.values(this.Persona?.records ?? []).filter(
                (persona) => persona.im_status !== "im_partner" && !persona.is_public
            );
        },
        eager: true,
        /** @this {import("models").Store} */
        onUpdate() {
            this.env.services["im_status"].registerToImStatus(
                "res.partner",
                this.imStatusTrackedPersonas.map((p) => p.id)
            );
        },
    });
    hasLinkPreviewFeature = true;
    // messaging menu
    menu = { counter: 0 };
    menuThreads = Record.many("Thread", {
        /** @this {import("models").Store} */
        compute() {
            /** @type {import("models").Thread[]} */
            let threads = Object.values(this.Thread.records).filter(
                (thread) =>
                    thread.displayToSelf ||
                    (thread.needactionMessages.length > 0 && thread.type !== "mailbox")
            );
            const tab = this.discuss.activeTab;
            if (tab !== "main") {
                threads = threads.filter(({ type }) => this.tabToThreadType(tab).includes(type));
            } else if (tab === "main" && this.env.inDiscussApp) {
                threads = threads.filter(({ type }) =>
                    this.tabToThreadType("mailbox").includes(type)
                );
            }
            return threads;
        },
        /**
         * @this {import("models").Store}
         * @param {import("models").Thread} a
         * @param {import("models").Thread} b
         */
        sort(a, b) {
            /**
             * Ordering:
             * - threads with needaction
             * - unread channels
             * - read channels
             * - odoobot chat
             *
             * In each group, thread with most recent message comes first
             */
            if (a.correspondent?.eq(this.odoobot) && !b.correspondent?.eq(this.odoobot)) {
                return 1;
            }
            if (b.correspondent?.eq(this.odoobot) && !a.correspondent?.eq(this.odoobot)) {
                return -1;
            }
            if (a.needactionMessages.length > 0 && b.needactionMessages.length === 0) {
                return -1;
            }
            if (b.needactionMessages.length > 0 && a.needactionMessages.length === 0) {
                return 1;
            }
            if (a.message_unread_counter > 0 && b.message_unread_counter === 0) {
                return -1;
            }
            if (b.message_unread_counter > 0 && a.message_unread_counter === 0) {
                return 1;
            }
            if (
                !a.newestPersistentNotEmptyOfAllMessage?.datetime &&
                b.newestPersistentNotEmptyOfAllMessage?.datetime
            ) {
                return 1;
            }
            if (
                !b.newestPersistentNotEmptyOfAllMessage?.datetime &&
                a.newestPersistentNotEmptyOfAllMessage?.datetime
            ) {
                return -1;
            }
            if (
                a.newestPersistentNotEmptyOfAllMessage?.datetime &&
                b.newestPersistentNotEmptyOfAllMessage?.datetime &&
                a.newestPersistentNotEmptyOfAllMessage?.datetime !==
                    b.newestPersistentNotEmptyOfAllMessage?.datetime
            ) {
                return (
                    b.newestPersistentNotEmptyOfAllMessage.datetime -
                    a.newestPersistentNotEmptyOfAllMessage.datetime
                );
            }
            return b.localId > a.localId ? 1 : -1;
        },
    });
    discuss = Record.one("DiscussApp");
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

    async fetchCannedResponses() {
        if (["fetching", "fetched"].includes(this.fetchCannedResponseState)) {
            return this.fetchCannedResponseDeferred;
        }
        this.fetchCannedResponseState = "fetching";
        this.fetchCannedResponseDeferred = new Deferred();
        this.fetchData({ canned_responses: true }).then(
            (recordsByModel) => {
                this.fetchCannedResponseState = "fetched";
                this.fetchCannedResponseDeferred.resolve(recordsByModel);
            },
            (error) => {
                this.fetchCannedResponseState = "not_fetched";
                this.fetchCannedResponseDeferred.reject(error);
            }
        );
        return this.fetchCannedResponseDeferred;
    }

    async fetchData(params, { readonly = true, silent = true } = {}) {
        Object.assign(this.fetchParams, params);
        this.fetchReadonly = this.fetchReadonly && readonly;
        this.fetchSilent = this.fetchSilent && silent;
        const fetchDeferred = this.fetchDeferred;
        this._fetchDataDebounced();
        return fetchDeferred;
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
     * @returns {{ [K in keyof T]: T[K] extends Array ? import("models").Models[K][] : import("models").Models[K] }}
     */
    insert(dataByModelName = {}, options = {}) {
        const store = this;
        return Record.MAKE_UPDATE(function storeInsert() {
            const res = {};
            for (const [modelName, data] of Object.entries(dataByModelName)) {
                res[modelName] = store[modelName].insert(data, options);
            }
            return res;
        });
    }

    async startMeeting() {
        const thread = await this.env.services["discuss.core.common"].createGroupChat({
            default_display_mode: "video_full_screen",
            partners_to: [this.self.id],
        });
        this.ChatWindow.get(thread)?.update({ autofocus: 0 });
        this.env.services["discuss.rtc"].toggleCall(thread, { video: true });
        this.openInviteThread = thread;
    }

    /**
     * @param {'chat' | 'group'} tab
     * @returns Thread types matching the given tab.
     */
    tabToThreadType(tab) {
        return tab === "chat" ? ["chat", "group"] : [tab];
    }

    setup() {
        super.setup();
        this._fetchDataDebounced = debounce(
            this._fetchDataDebounced,
            Store.FETCH_DATA_DEBOUNCE_DELAY
        );
        this.updateBusSubscription = debounce(this.updateBusSubscription, 0); // Wait for thread fully inserted.
    }

    /** Provides an override point for when the store service has started. */
    onStarted() {}

    updateBusSubscription() {
        const channelIds = [];
        const ids = Object.keys(this.Thread.records).sort(); // Ensure channels processed in same order.
        for (const id of ids) {
            const thread = this.Thread.records[id];
            if (thread.model === "discuss.channel") {
                channelIds.push(id);
                if (!thread.hasSelfAsMember) {
                    this.env.services["bus_service"].addChannel(`discuss.channel_${thread.id}`);
                }
            }
        }
        const channels = JSON.stringify(channelIds);
        if (this.lastChannelSubscription !== channels) {
            this.env.services["bus_service"].forceUpdateChannels();
        }
        this.lastChannelSubscription = channels;
    }
}
Store.register();

export const storeService = {
    dependencies: ["bus_service", "im_status", "ui"],
    /**
     * @param {import("@web/env").OdooEnv} env
     * @param {Partial<import("services").Services>} services
     */
    start(env, services) {
        const store = makeStore(env);
        store.discuss = { activeTab: "main" };
        store.insert(session.storeData);
        /**
         * Add defaults for `self` and `settings` because in livechat there could be no user and no
         * guest yet (both undefined at init), but some parts of the code that loosely depend on
         * these values will still be executed immediately. Providing a dummy default is enough to
         * avoid crashes, the actual values being filled at livechat init when they are necessary.
         */
        store.self ??= { id: -1, type: "guest" };
        store.settings ??= {};
        const discussActionIds = ["mail.action_discuss"];
        if (store.action_discuss_id) {
            discussActionIds.push(store.action_discuss_id);
        }
        store.discuss.isActive ||= discussActionIds.includes(router.current.action);
        Record.onChange(store.Thread, "records", () => store.updateBusSubscription());
        services.ui.bus.addEventListener("resize", () => {
            store.discuss.activeTab = "main";
            if (
                services.ui.isSmall &&
                store.discuss.thread &&
                store.discuss.thread.type !== "mailbox"
            ) {
                store.discuss.activeTab = store.discuss.thread.type;
            }
        });
        store.onStarted();
        return store;
    },
};

registry.category("services").add("mail.store", storeService);
