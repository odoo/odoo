/* @odoo-module */

import { onChange } from "@mail/utils/common/misc";

import { reactive } from "@odoo/owl";

import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { debounce } from "@web/core/utils/timing";
import { DiscussModel, DiscussModelManager, discussModelRegistry } from "./discuss_model";

export class Store {
    /** @type {import("@mail/core/web/activity_model").ActivityManager} */
    Activity;
    /** @type {import("@mail/core/common/attachment_model").AttachmentManager} */
    Attachment;
    /** @type {import("@mail/core/common/canned_response_model").CannedResponseManager} */
    CannedResponse;
    /** @type {import("@mail/core/common/channel_member_model").ChannelMemberManager} */
    ChannelMember;
    /** @type {import("@mail/core/common/chat_window_model").ChatWindowManager} */
    ChatWindow;
    /** @type {import("@mail/core/common/follower_model").FollowerManager} */
    Follower;
    /** @type {import("@mail/core/common/message_model").MessageManager} */
    Message;
    /** @type {import("@mail/core/common/notification_model").NotificationManager} */
    Notification;
    /** @type {import("@mail/core/common/notification_group_model").NotificationGroupManager} */
    NotificationGroup;
    /** @type {import("@mail/core/common/persona_model").PersonaManager} */
    Persona;
    /** @type {import("@mail/discuss/call/common/rtc_session_model").RtcSessionManager} */
    RtcSession;
    /** @type {import("@mail/core/common/thread_model").ThreadManager} */
    Thread;

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
        threadObjectId: null,
        channels: {
            extraClass: "o-mail-DiscussSidebarCategory-channel",
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
            extraClass: "o-mail-DiscussSidebarCategory-chat",
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

    activityCounter = 0;

    isMessagingReady = false;
}

export const storeService = {
    dependencies: ["bus_service", "ui"],
    start(env, services) {
        const res = reactive(new Store(env, services));
        for (const [Model, ModelManager] of discussModelRegistry.getAll()) {
            if (!(Model.prototype instanceof DiscussModel)) {
                throw new Error("1st parameter of `discussModelRegistry` must be a `DiscussModel`");
            }
            if (!(ModelManager.prototype instanceof DiscussModelManager)) {
                throw new Error(
                    "2nd parameter of `discussModelRegistry` must be a `DiscussModelManager`"
                );
            }
            if (res[Model.name]) {
                throw new Error(
                    `There must be no duplicated Discuss Model Names (duplicate found: ${Model.name})`
                );
            }
            res[Model.name] = new ModelManager(env, res);
            res[Model.name].class = Model;
        }
        onChange(res.Thread, "records", () => res.updateBusSubscription());
        services.ui.bus.addEventListener("resize", () => {
            if (!services.ui.isSmall) {
                res.discuss.activeTab = "all";
            } else {
                res.discuss.activeTab =
                    res.Thread.records[res.discuss.threadObjectId]?.type ?? "all";
            }
        });
        return res;
    },
};

registry.category("services").add("mail.store", storeService);
