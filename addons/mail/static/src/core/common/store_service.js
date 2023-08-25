/* @odoo-module */

import { onChange } from "@mail/utils/common/misc";

import { reactive } from "@odoo/owl";

import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { debounce } from "@web/core/utils/timing";

export class Store {
    Activity = {
        /** @type {Object.<number, import("@mail/core/web/activity_model").Activity>} */
        records: {},
        /**
         * @param {import("@mail/core/web/activity_model").Data} data
         * @param {Object} [param1]
         * @param {boolean} param1.broadcast
         * @returns {import("@mail/core/web/activity_model").Activity}
         */
        insert: (data, { broadcast = true } = {}) =>
            this.env.services["mail.activity"].insert(data, { broadcast }),
    };
    Attachment = {
        /** @type {Object.<number, import("@mail/core/common/attachment_model").Attachment>} */
        records: {},
        /**
         * @param {Object} data
         * @returns {import("@mail/core/common/attachment_model").Attachment}
         */
        insert: (data) => this.env.services["mail.attachment"].insert(data),
    };
    CannedResponse = {
        /** @type {Object.<number, import("@mail/core/common/canned_response_model").CannedResponse>} */
        records: {},
        /**
         * @param {Object} data
         * @returns {import("@mail/core/common/canned_response_model").CannedResponse}
         */
        insert: (data) => this.env.services["mail.messaging"].insertCannedResponse(data),
    };
    ChannelMember = {
        /** @type {Object.<number, import("@mail/core/common/channel_member_model").ChannelMember>} */
        records: {},
        /**
         * @param {Object|Array} data
         * @returns {import("@mail/core/common/channel_member_model").ChannelMember}
         */
        insert: (data) => this.env.services["discuss.channel.member"].insert(data),
    };
    ChatWindow = {
        /** @type {import("@mail/core/common/chat_window_model").ChatWindow[]} */
        records: [],
        /**
         * @param {ChatWindowData} [data]
         * @returns {import("@mail/core/common/chat_window_model").ChatWindow}
         */
        insert: (data = {}) => this.env.services["mail.chat_window"].insert(data),
    };
    Follower = {
        /** @type {Object.<number, import("@mail/core/common/follower_model").Follower>} */
        records: {},
        /**
         * @param {import("@mail/core/common/follower_model").Data} data
         * @returns {import("@mail/core/common/follower_model").Follower}
         */
        insert: (data) => this.env.services["mail.thread"].insertFollower(data),
    };
    Message = {
        /** @type {Object.<number, import("@mail/core/common/message_model").Message>} */
        records: {},
        /**
         * @param {Object} data
         * @returns {import("@mail/core/common/message_model").Message}
         */
        insert: (data) => this.env.services["mail.message"].insert(data),
    };
    Notification = {
        /** @type {Object.<number, import("@mail/core/common/notification_model").Notification>} */
        records: {},
        /**
         * @param {Object} data
         * @returns {import("@mail/core/common/notification_model").Notification}
         */
        insert: (data) => this.env.services["mail.message"].insertNotification(data),
    };
    NotificationGroup = {
        /** @type {import("@mail/core/common/notification_group_model").NotificationGroup[]} */
        records: [],
        /**
         * @param {Object} data
         * @returns {import("@mail/core/common/notification_group_model").NotificationGroup}
         */
        insert: (data) => this.env.services["mail.message"].insertNotificationGroups(data),
    };
    Persona = {
        /** @type {Object.<number, import("@mail/core/common/persona_model").Persona>} */
        records: {},
        /**
         * @param {import("@mail/core/common/persona_model").Data} data
         * @returns {import("@mail/core/common/persona_model").Persona}
         */
        insert: (data) => this.env.services["mail.persona"].insert(data),
    };
    RtcSession = {
        /** @type {Object.<number, import("@mail/discuss/call/common/rtc_session_model").RtcSession>} */
        records: {},
        /**
         * @param {Object} data
         * @returns {number, import("@mail/discuss/call/common/rtc_session_model").RtcSession}
         */
        insert: (data) => this.env.services["discuss.rtc"].insertSession(data),
    };
    Thread = {
        /** @type {Object.<string, import("@mail/core/common/thread_model").Thread>} */
        records: {},
        /**
         * @param {Object} data
         * @returns {import("@mail/core/common/thread_model").Thread}
         */
        insert: (data) => this.env.services["mail.thread"].insert(data),
    };

    /**
     * @param {import("@web/env").OdooEnv} env
     */
    constructor(env) {
        this.setup(env);
        this.lastChannelSubscription = "";
        this.updateBusSubscription = debounce(this.updateBusSubscription, 0); // Wait for thread fully inserted.
    }

    /**
     * @param {import("@web/env").OdooEnv} env
     */
    setup(env) {
        this.env = env;
        this.discuss.activeTab = this.env.services.ui.isSmall ? "mailbox" : "all";
    }

    updateBusSubscription() {
        const channelIds = [];
        const ids = Object.keys(this.Thread.records).sort(); // Ensure channels processed in same order.
        for (const id of ids) {
            const thread = this.Thread.records[id];
            if (thread.model === "discuss.channel" && thread.hasSelfAsMember) {
                channelIds.push(id);
            }
        }
        const channels = JSON.stringify(channelIds);
        if (this.isMessagingReady && this.lastChannelSubscription !== channels) {
            this.env.services["bus_service"].forceUpdateChannels();
        }
        this.lastChannelSubscription = channels;
    }

    get self() {
        return this.guest ?? this.user;
    }

    // base data

    /**
     * This is the current logged partner
     *
     * @type {import("@mail/core/common/persona_model").Persona}
     */
    user = null;
    /**
     * This is the current logged guest
     *
     * @type {import("@mail/core/common/persona_model").Persona}
     */
    guest = null;

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

    /** @type {import("@mail/core/common/persona_model").Persona} */
    odoobot = null;
    odoobotOnboarding;
    users = {};
    internalUserGroupId = null;
    registeredImStatusPartners = null;
    ringingThreads = null;

    hasLinkPreviewFeature = true;

    // messaging menu
    menu = {
        counter: 0,
    };

    // discuss app
    discuss = {
        activeTab: "all", // can be 'mailbox', 'all', 'channel' or 'chat'
        isActive: false,
        threadLocalId: null,
        channels: {
            extraClass: "o-mail-DiscussSidebarCategory-channel",
            id: "channels",
            name: _t("Channels"),
            isOpen: false,
            canView: true,
            canAdd: true,
            serverStateKey: "is_discuss_sidebar_category_channel_open",
            addTitle: _t("Add or join a channel"),
            addHotkey: "c",
            threads: [], // list of ids
        },
        chats: {
            extraClass: "o-mail-DiscussSidebarCategory-chat",
            id: "chats",
            name: _t("Direct messages"),
            isOpen: false,
            canView: false,
            canAdd: true,
            serverStateKey: "is_discuss_sidebar_category_chat_open",
            addTitle: _t("Start a conversation"),
            addHotkey: "d",
            threads: [], // list of ids
        },
        // mailboxes in sidebar
        /** @type {import("@mail/core/common/thread_model").Thread} */
        inbox: null,
        /** @type {import("@mail/core/common/thread_model").Thread} */
        starred: null,
        /** @type {import("@mail/core/common/thread_model").Thread} */
        history: null,
    };

    activityCounter = 0;

    isMessagingReady = false;
}

export const storeService = {
    dependencies: ["bus_service", "ui"],
    /**
     * @param {import("@web/env").OdooEnv} env
     * @param {Partial<import("services").Services>} services
     */
    start(env, services) {
        const res = reactive(new Store(env, services));
        onChange(res.Thread, "records", () => res.updateBusSubscription());
        services.ui.bus.addEventListener("resize", () => {
            if (!services.ui.isSmall) {
                res.discuss.activeTab = "all";
            } else {
                res.discuss.activeTab =
                    res.Thread.records[res.discuss.threadLocalId]?.type ?? "all";
            }
        });
        return res;
    },
};

registry.category("services").add("mail.store", storeService);
