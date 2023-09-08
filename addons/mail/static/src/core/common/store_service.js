/* @odoo-module */

import { onChange } from "@mail/utils/common/misc";

import { reactive } from "@odoo/owl";

import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { debounce } from "@web/core/utils/timing";
import { modelRegistry, Record } from "./record";

export class Store {
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
    /** @type {typeof import("@mail/core/common/notification_group_model").NotificationGroup} */
    NotificationGroup;
    /** @type {typeof import("@mail/core/common/persona_model").Persona} */
    Persona;
    /** @type {typeof import("@mail/discuss/call/common/rtc_session_model").RtcSession} */
    RtcSession;
    /** @type {typeof import("@mail/core/common/thread_model").Thread} */
    Thread;

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
        for (const [name, Model] of modelRegistry.getEntries()) {
            if (res[name]) {
                throw new Error(
                    `There must be no duplicated Model Names (duplicate found: ${name})`
                );
            }
            // classes cannot be made reactive because they are functions and they are not supported.
            // work-around: make an object whose prototype is the class, so that static props become
            // instance props.
            const entry = Object.assign(Object.create(Model), { env, store: res });
            // Produce another class with changed prototype, so that there are automatic get/set on relational fields
            const Class = {
                [Model.name]: class extends Model {
                    static __rels__ = new Set();
                    constructor() {
                        super();
                        for (const name of this.constructor.__rels__) {
                            // Relational fields contain symbols for detection in original class.
                            // This constructor is called on genuine records:
                            // - 'one' fields => undefined
                            const newVal = undefined;
                            this[name] = newVal;
                            this.__rels__.set(name, newVal);
                        }
                    }
                },
            }[Model.name];
            entry.Class = Class;
            entry.records = JSON.parse(JSON.stringify(Model.records));
            res[name] = entry;
            // Detect relational fields with a dummy record and setup getter/setters on them
            const obj = new Model();
            for (const [name, val] of Object.entries(obj)) {
                if (val !== Record.one()) {
                    continue;
                }
                Class.__rels__.add(name);
                Object.defineProperty(Class.prototype, name, {
                    get() {
                        const localId = this.__rels__.get(name);
                        return res.get(localId);
                    },
                    set(record) {
                        this.__rels__.set(name, record?.localId);
                    },
                });
            }
        }
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
