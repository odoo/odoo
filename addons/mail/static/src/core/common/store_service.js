/* @odoo-module */

import { onChange } from "@mail/utils/common/misc";

import { reactive } from "@odoo/owl";

import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { debounce } from "@web/core/utils/timing";

export class Store {
    constructor(env) {
        this.setup(env);
        this.lastChannelSubscription = "";
        this.updateBusSubscription = debounce(this.updateBusSubscription, 0); // Wait for thread fully inserted.
    }

    setup(env) {
        this.env = env;
        this.discuss.activeTab = this.env.services.ui.isSmall ? "mailbox" : "all";
    }

    updateBusSubscription() {
        const channelIds = [];
        const ids = Object.keys(this.threads).sort(); // Ensure channels processed in same order.
        for (const id of ids) {
            const thread = this.threads[id];
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

    /** @type {Object.<number, import("@mail/core/common/channel_member_model").ChannelMember>} */
    channelMembers = {};
    companyName = "";

    /** @type {Object.<number, import("@mail/core/common/notification_model").Notification>} */
    notifications = {};
    notificationGroups = [];

    /** @type {Object.<number, import("@mail/core/common/follower_model").Follower>} */
    followers = {};

    /** @type {import("@mail/core/common/persona_model").Persona} */
    odoobot = null;
    /** @type {Object.<number, import("@mail/core/common/persona_model").Persona>} */
    personas = {};

    /** @type {Object.<number, import("@mail/discuss/call/common/rtc_session_model").RtcSession>} */
    rtcSessions = {};
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
            extraClass: "o-mail-DiscussCategory-channel",
            id: "channels",
            name: _t("Channels"),
            isOpen: false,
            canView: true,
            canAdd: true,
            serverStateKey: "is_discuss_sidebar_category_channel_open",
            addTitle: _t("Add or join a channel"),
            threads: [], // list of ids
        },
        chats: {
            extraClass: "o-mail-DiscussCategory-chat",
            id: "chats",
            name: _t("Direct messages"),
            isOpen: false,
            canView: false,
            canAdd: true,
            serverStateKey: "is_discuss_sidebar_category_chat_open",
            addTitle: _t("Start a conversation"),
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
    cannedResponses = [];

    /** @type {Object.<number, import("@mail/core/web/activity_model").Activity>} */
    activities = {};
    activityCounter = 0;
    /** @type {Object.<number, import("@mail/core/common/attachment_model").Attachment>} */
    attachments = {};

    /** @type {import("@mail/core/common/chat_window_model").ChatWindow[]} */
    chatWindows = [];

    /** @type {Object.<number, import("@mail/core/common/message_model").Message>} */
    messages = {};

    /** @type {Object.<string, import("@mail/core/common/thread_model").Thread>} */
    threads = {};

    isMessagingReady = false;
}

export const storeService = {
    dependencies: ["bus_service", "ui"],
    start(env, services) {
        const res = reactive(new Store(env, services));
        onChange(res, "threads", () => res.updateBusSubscription());
        services.ui.bus.addEventListener("resize", () => {
            if (!services.ui.isSmall) {
                res.discuss.activeTab = "all";
            } else {
                res.discuss.activeTab = res.threads[res.discuss.threadLocalId]?.type ?? "all";
            }
        });
        return res;
    },
};

registry.category("services").add("mail.store", storeService);
