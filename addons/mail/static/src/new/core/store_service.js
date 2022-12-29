/* @odoo-module */

import { reactive } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { onChange } from "@mail/new/utils/misc";

export class Store {
    constructor(env, { "mail.context": context }) {
        this.setup(env);
        this.lastChannelSubscription = "";
        this.inPublicPage = Boolean(context.inPublicPage);
    }

    setup(env) {
        this.env = env;
        this.isSmall = env.isSmall;
    }

    async updateBusSubscription() {
        await new Promise(setTimeout); // Wait for thread fully inserted.
        const channelIds = [];
        const ids = Object.keys(this.threads).sort(); // Ensure channels processed in same order.
        for (const id of ids) {
            const thread = this.threads[id];
            if (thread.model === "mail.channel" && thread.hasSelfAsMember) {
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
     * @type {import("@mail/new/core/persona_model").Persona}
     */
    user = null;
    /**
     * This is the current logged guest
     *
     * @type {import("@mail/new/core/persona_model").Persona}
     */
    guest = null;

    /**
     * Indicates whether the current user is using the application through the
     * public page.
     */
    inPublicPage = false;

    /** @type {Object.<number, import("@mail/new/core/channel_member_model").ChannelMember>} */
    channelMembers = {};
    companyName = "";

    /** @type {Object.<number, import("@mail/new/core/notification_model").Notification>} */
    notifications = {};
    notificationGroups = [];

    /** @type {Object.<number, import("@mail/new/core/follower_model").Follower>} */
    followers = {};

    /**
     * This is Odoobot
     *
     * @type {import("@mail/new/core/persona_model").Persona}
     */
    partnerRoot = null;
    /** @type {Object.<number, import("@mail/new/core/persona_model").Persona>} */
    personas = {};

    /** @type {import("@mail/new/rtc/rtc_session_model").rtcSession{}} */
    rtcSessions = {};
    users = {};
    internalUserGroupId = null;
    registeredImStatusPartners = null;
    ringingThreads = null;

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
        /** @type {import("@mail/new/core/thread_model").Thread} */
        inbox: null,
        /** @type {import("@mail/new/core/thread_model").Thread} */
        starred: null,
        /** @type {import("@mail/new/core/thread_model").Thread} */
        history: null,
    };
    cannedResponses = [];

    /** @type {Object.<number, import("@mail/new/web/activity/activity_model").Activity>} */
    activities = {};
    activityCounter = 0;
    /** @type {Object.<number, import("@mail/new/attachments/attachment_model").Attachment>} */
    attachments = {};

    /** @type {import("@mail/new/web/chat_window/chat_window_model").ChatWindow[]} */
    chatWindows = [];

    /** @type {Object.<number, import("@mail/new/core/message_model").Message>} */
    messages = {};

    /** @type {Object.<string, import("@mail/new/core/thread_model").Thread>} */
    threads = {};

    isMessagingReady = false;
}

export const storeService = {
    dependencies: ["bus_service", "ui", "mail.context"],
    start(env, services) {
        const res = reactive(new Store(env, services));
        onChange(res, "threads", () => res.updateBusSubscription());
        res.discuss.activeTab = res.isSmall ? "mailbox" : "all";
        services.ui.bus.addEventListener("resize", () => {
            res.isSmall = services.ui.isSmall;
            if (!res.isSmall) {
                res.discuss.activeTab = "all";
            } else {
                res.discuss.activeTab = res.discuss.threadLocalId
                    ? res.threads[res.discuss.threadLocalId].type
                    : "all";
            }
        });
        return res;
    },
};

registry.category("services").add("mail.store", storeService);
