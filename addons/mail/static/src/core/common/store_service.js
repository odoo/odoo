import { rpcWithEnv } from "@mail/utils/common/misc";
import { Store as BaseStore, makeStore, Record } from "@mail/core/common/record";
import { reactive } from "@odoo/owl";

import { router } from "@web/core/browser/router";
/** @type {ReturnType<import("@mail/utils/common/misc").rpcWithEnv>} */
let rpc;
import { registry } from "@web/core/registry";
import { user } from "@web/core/user";
import { Deferred } from "@web/core/utils/concurrency";
import { debounce } from "@web/core/utils/timing";
import { session } from "@web/session";
import { _t } from "@web/core/l10n/translation";
import { prettifyMessageContent } from "@mail/utils/common/format";
import { escape } from "@web/core/utils/strings";

export class Store extends BaseStore {
    static FETCH_DATA_DEBOUNCE_DELAY = 1;
    FETCH_LIMIT = 30;

    /** @returns {import("models").Store|import("models").Store[]} */
    static insert() {
        rpc = rpcWithEnv(this.env);
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
    /** This is the current logged partner / guest */
    self = Record.one("Persona");
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
        inverse: "storeAsTrackedImStatus",
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
                    (thread.needactionMessages.length > 0 && thread.model !== "mail.box")
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
    settings = Record.one("Settings");
    openInviteThread = Record.one("Thread");

    fetchDeferred = new Deferred();
    fetchParams = {};
    fetchReadonly = true;
    fetchSilent = true;

    cannedReponses = this.makeCachedFetchData({ canned_responses: true });

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
        this.updateBusSubscription = debounce(
            () => this.env.services.bus_service.forceUpdateChannels(),
            0
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

    getDiscussSidebarCategoryCounter(categoryId) {
        return this.DiscussAppCategory.get({ id: categoryId }).threads.reduce((acc, channel) => {
            if (categoryId === "channels") {
                return channel.message_needaction_counter > 0 ? acc + 1 : acc;
            } else {
                return channel.message_unread_counter > 0 ? acc + 1 : acc;
            }
        }, 0);
    }

    /**
     * Get the parameters to pass to the message post route.
     */
    async getMessagePostParams({
        attachments,
        body,
        cannedResponseIds,
        isNote,
        mentionedChannels,
        mentionedPartners,
        thread,
    }) {
        const subtype = isNote ? "mail.mt_note" : "mail.mt_comment";
        const validMentions =
            this.self.type === "partner"
                ? this.env.services["mail.message"].getMentionsFromText(body, {
                      mentionedChannels,
                      mentionedPartners,
                  })
                : undefined;
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
        return {
            context: {
                mail_post_autofollow: !isNote && thread.hasWriteAccess,
            },
            post_data: {
                body: await prettifyMessageContent(body, validMentions),
                attachment_ids: attachments.map(({ id }) => id),
                attachment_tokens: attachments.map((attachment) => attachment.accessToken),
                canned_response_ids: cannedResponseIds,
                message_type: "comment",
                partner_ids,
                subtype_xmlid: subtype,
                partner_emails: recipientEmails,
                partner_additional_values: recipientAdditionalValues,
            },
            thread_id: thread.id,
            thread_model: thread.model,
        };
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

    async joinChannel(id, name) {
        await this.env.services.orm.call("discuss.channel", "add_members", [[id]], {
            partner_ids: [this.self.id],
        });
        const thread = this.Thread.insert({
            channel_type: "channel",
            id,
            model: "discuss.channel",
            name,
        });
        if (!thread.avatarCacheKey) {
            thread.avatarCacheKey = "hello";
        }
        thread.open();
        return thread;
    }

    async joinChat(id, forceOpen = false) {
        const data = await this.env.services.orm.call("discuss.channel", "channel_get", [], {
            partners_to: [id],
            force_open: forceOpen,
        });
        const thread = this.Thread.insert(data);
        return thread;
    }

    async openChat(person) {
        const chat = await this.getChat(person);
        chat?.open();
    }

    /**
     * @param {string} searchTerm
     * @param {Thread} thread
     * @param {number|false} [before]
     */
    async search(searchTerm, thread, before = false) {
        const { messages, count } = await rpc(thread.getFetchRoute(), {
            ...thread.getFetchParams(),
            search_term: escape(searchTerm),
            before,
        });
        return {
            count,
            loadMore: messages.length === this.FETCH_LIMIT,
            messages: this.Message.insert(messages, { html: true }),
        };
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
        services.ui.bus.addEventListener("resize", () => {
            store.discuss.activeTab = "main";
            if (services.ui.isSmall && store.discuss.thread?.channel_type) {
                store.discuss.activeTab = store.discuss.thread.channel_type;
            }
        });
        store.onStarted();
        return store;
    },
};

registry.category("services").add("mail.store", storeService);
