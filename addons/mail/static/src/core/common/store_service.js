/* @odoo-module */

import { registry } from "@web/core/registry";
import { debounce } from "@web/core/utils/timing";
import { Record, makeStore, BaseStore } from "./record";

export class Store extends BaseStore {
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
    /** @type {typeof import("@mail/core/common/thread_model").Thread} */
    Thread;

    get registeredImStatusPartners() {
        return this.imStatusTrackedPersonas.map((persona) => persona.id);
    }

    knownChannelIds = new Set();
    /** This is the current logged partner */
    user = Record.one("Persona");
    /** This is the current logged guest */
    guest = Record.one("Persona");
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
    companyName = "";
    odoobot = Record.one("Persona");
    odoobotOnboarding;
    users = {};
    internalUserGroupId = null;
    imStatusTrackedPersonas = Record.many("Persona", {
        inverse: "storeAsTrackedImStatus",
        onUpdate() {
            this.updateImStatusRegistration();
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
            const aOdooBot = a.isCorrespondentOdooBot;
            const bOdooBot = b.isCorrespondentOdooBot;
            if (aOdooBot && !bOdooBot) {
                return 1;
            }
            if (bOdooBot && !aOdooBot) {
                return -1;
            }
            const aNeedaction = a.needactionMessages.length;
            const bNeedaction = b.needactionMessages.length;
            if (aNeedaction > 0 && bNeedaction === 0) {
                return -1;
            }
            if (bNeedaction > 0 && aNeedaction === 0) {
                return 1;
            }
            const aUnread = a.message_unread_counter;
            const bUnread = b.message_unread_counter;
            if (aUnread > 0 && bUnread === 0) {
                return -1;
            }
            if (bUnread > 0 && aUnread === 0) {
                return 1;
            }
            const aMessageDatetime = a.newestPersistentNotEmptyOfAllMessage?.datetime;
            const bMessageDateTime = b.newestPersistentNotEmptyOfAllMessage?.datetime;
            if (!aMessageDatetime && bMessageDateTime) {
                return 1;
            }
            if (!bMessageDateTime && aMessageDatetime) {
                return -1;
            }
            if (aMessageDatetime && bMessageDateTime && aMessageDatetime !== bMessageDateTime) {
                return bMessageDateTime - aMessageDatetime;
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
    activityCounter = 0;
    isMessagingReady = false;

    get self() {
        return this.guest ?? this.user;
    }

    updateImStatusRegistration() {
        this.env.services.im_status?.registerToImStatus("res.partner", [
            ...this.registeredImStatusPartners,
        ]);
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
        this.updateBusSubscription = debounce(
            () => this.env.services.bus_service.forceUpdateChannels(),
            0
        );
    }
}
Store.register();

export const storeService = {
    dependencies: ["bus_service", "ui"],
    /**
     * @param {import("@web/env").OdooEnv} env
     * @param {Partial<import("services").Services>} services
     */
    start(env, services) {
        const store = makeStore(env);
        store.discuss = {};
        store.discuss.activeTab = "main";
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
        return store;
    },
};

registry.category("services").add("mail.store", storeService);
