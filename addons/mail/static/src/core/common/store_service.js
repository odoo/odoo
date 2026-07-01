import { Store as BaseStore, fields, makeStore } from "@mail/model/export";
import {
    attClassObjectToString,
    generateEmojisOnHtml,
    prettifyMessageText,
} from "@mail/utils/common/format";
import { compareDatetime } from "@mail/utils/common/misc";

import { proxy } from "@odoo/owl";

import { browser } from "@web/core/browser/browser";
import { cookie } from "@web/core/browser/cookie";
import { isMobileOS } from "@web/core/browser/feature_detection";
import { _t } from "@web/core/l10n/translation";
import { rpc } from "@web/core/network/rpc";
import { registry } from "@web/core/registry";
import { user } from "@web/core/user";
import { Mutex } from "@web/core/utils/concurrency";
import { renderToElement } from "@web/core/utils/render";
import { debounce } from "@web/core/utils/timing";
import { getOrigin } from "@web/core/utils/urls";
import { session } from "@web/session";
import { isMarkup, createDocumentFragmentFromContent } from "@web/core/utils/html";

const { DateTime } = luxon;

/**
 * @typedef {{isSpecial: boolean, channel_types: string[], label: string, displayName: string, description: string}} SpecialMention
 */

let prevLastMessageId = null;
let temporaryIdOffset = 0.01;

export class Store extends BaseStore {
    static FETCH_DATA_DEBOUNCE_DELAY = 1;
    static OTHER_LONG_TYPING = 60000;

    FETCH_LIMIT = 30;
    DEFAULT_AVATAR = "/mail/static/src/img/smiley/avatar.jpg";

    bookmarkBox = fields.One("mail.thread");
    history = fields.One("mail.thread");
    inbox = fields.One("mail.thread");
    isReadyPromise = new Promise((resolve) => (this._resolveIsReady = resolve));
    self_guest = fields.One("mail.guest");
    self_user = fields.One("res.users");
    /** This is the current logged partner / guest */
    get self() {
        return this.self_user?.partner_id || this.self_guest;
    }
    initialized = false;
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
        sort: (f1, f2) => {
            if (f1.lastMessage?.id && !f2.lastMessage?.id) {
                return -1;
            }
            if (!f1.lastMessage?.id && f2.lastMessage?.id) {
                return 1;
            }
            return f2.lastMessage?.id - f1.lastMessage?.id || f2.id - f1.id;
        },
    });
    settings = fields.One("Settings");

    /** @type {[[string, any, import("models").DataResponse]]} */
    fetchParams = [];
    fetchSilent = true;

    cannedReponses = this.makeCachedFetchData("mail.canned.response");

    specialMentions = [
        {
            isSpecial: true,
            label: "everyone",
            channel_types: ["channel", "group"],
            displayName: "Everyone",
            description: _t("Notify all members of this conversation"),
        },
        {
            isSpecial: true,
            label: "here",
            channel_types: ["channel", "group"],
            displayName: "Here",
            description: _t("Notify all members of this conversation who are online"),
        },
    ];

    isNotificationPermissionDismissed = fields.Attr(false, { localStorage: true });

    messagePostMutex = new Mutex();

    shouldSimulateDarkTheme(ctx) {
        return (
            (ctx?.env?.inDiscussCallView ||
                ctx?.env?.inCallInvitation ||
                ctx?.env.isDiscussPipBanner ||
                ctx?.env?.inWelcomePage) &&
            this.isOdooWhiteTheme &&
            !ctx?.env.inDiscussActionPanel
        );
    }

    discussDropdownMenuClass(ctx) {
        const simulateDarkTheme = this.shouldSimulateDarkTheme(ctx);
        return attClassObjectToString({
            "o-discuss-dropdownMenu d-flex flex-column border-secondary": true,
            "o-simulateDarkTheme": simulateDarkTheme,
        });
    }

    standaloneInboxMessages = fields.Many("mail.message", {
        compute() {
            const messages = (this.store.inbox?.messages ?? []).filter((m) => !m.thread);
            return messages.sort(
                (m1, m2) => compareDatetime(m2.datetime, m1.datetime) || m2.id - m1.id
            );
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
     * Ensure `initialize` is executed exactly once. Exposed as a separate function to
     * allow overriding store initialization.
     */
    ensureInitialized() {
        if (this.initialized) {
            return;
        }
        this.initialized = true;
        this.initialize();
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
     * @param {boolean} [options.silent=true]
     */
    async fetchStoreData(name, params, { requestData = false, silent = true } = {}) {
        /** @type {import("models").DataResponse} */
        const dataRequest = this.DataResponse.createRequest();
        dataRequest._autoResolve = !requestData;
        this.fetchParams.push([name, params, dataRequest]);
        this.fetchSilent = this.fetchSilent && silent;
        this._fetchStoreDataDebounced();
        return dataRequest._resultResolvers.promise;
    }

    /**
     * Initialize the store by fetching the required data for the messaging system.
     * Override to add data to be fetched. Do not call directly: use `ensureInitialized`
     * to ensure the store is only initialized once.
     */
    initialize() {
        this.fetchStoreData("init_messaging").then(() => {
            this._resolveIsReady();
        });
    }

    /**
     * Called after the store is fully set up. Override to add listeners or set default field values.
     * This avoids issues with the dummy store created during setup, which would cause computes to
     * crash and listeners to be registered twice.
     */
    onStarted() {
        this.isOdooWhiteTheme = cookie.get("color_scheme") !== "dark" || this.inPublicPage;
        navigator.serviceWorker?.addEventListener("message", ({ data = {} }) => {
            const { type, payload } = data;
            if (type === "notification-display-request") {
                const { correlationId, model, res_id } = payload;
                const thread = this["mail.thread"].get({ model, id: res_id });
                let isTabFocused;
                try {
                    isTabFocused = parent.document.hasFocus();
                } catch {
                    // assumes tab not focused: parent.document from iframe triggers CORS error
                }
                // Prevent duplicate inbox push notifications since they're already handled by
                // `mail.message/inbox` bus notifications, and the `modelsHandleByPush` heuristic
                // in `out_of_focus_service.js` isn't reliable enough to detect these cases.
                const isInbox =
                    this.self_user?.notification_type === "inbox" && model !== "discuss.channel";
                if ((isTabFocused && thread?.channel?.isDisplayed) || isInbox) {
                    navigator.serviceWorker.controller?.postMessage({
                        type: "notification-display-response",
                        payload: { correlationId },
                    });
                }
            }
            if (type === "notification-displayed") {
                this.onPushNotificationDisplayed(payload);
            }
        });
    }

    /**
     * Create a cacheable version of the `fetchStoreData` method. The result of the
     * request is cached once acquired. In case of failure, the promise is
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
        let promWithResolvers = null;
        const r = proxy({
            status: "not_fetched",
            fetch: () => {
                if (["fetching", "fetched"].includes(r.status)) {
                    return promWithResolvers.promise;
                }
                r.status = "fetching";
                promWithResolvers = Promise.withResolvers();
                this.fetchStoreData(name, params).then(
                    (result) => {
                        r.status = "fetched";
                        promWithResolvers.resolve(result);
                    },
                    (error) => {
                        r.status = "not_fetched";
                        promWithResolvers.reject(error);
                    }
                );
                return promWithResolvers.promise;
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
                    dataRequest._resultResolvers.reject(error);
                }
            }
        );
        this.fetchParams = [];
        this.fetchSilent = true;
    }

    _fetchStoreDataRpc(fetchParams) {
        return rpc(
            "/mail/store",
            { fetch_params: fetchParams, context: user.context },
            { silent: this.fetchSilent }
        );
    }

    async startMeeting() {
        const localizedDatetime = this.store.self?.tz
            ? DateTime.now().setZone(this.store.self?.tz)
            : DateTime.now().toLocal();
        const formatDate = localizedDatetime.toLocaleString(
            { month: "short", day: "numeric" },
            { locale: user.lang }
        );
        /** @type {import("models").DiscussChannel} */
        const channel = await this.createGroupChat({
            name: _t("Meeting, %(date)s", { date: formatDate }),
            default_display_mode: "video_full_screen",
            users_to: [this.self_user.id],
        });
        await this.chatHub.initPromise;
        channel.chatWindow?.update({ autofocus: 0 });
        await this.env.services["discuss.rtc"].toggleCall(channel, { camera: true });
        if (this.rtc.selfSession) {
            this.rtc.enterFullscreen();
        }
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
            this["mail.thread"].getOrFetch({ model, id }).then((thread) => {
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
            this.onClickPartnerMention(ev, id);
            return true;
        } else if (link.classList.contains("o_message_redirect")) {
            const message = this["mail.message"].get(id);
            const targetThread = message?.thread;
            const showAccessError = () =>
                this.env.services.notification.add(_t("This conversation isn’t available."), {
                    type: "danger",
                });
            if (targetThread) {
                targetThread.checkReadAccess().then((hasAccess) => {
                    if (hasAccess) {
                        targetThread.highlightMessage = message;
                        let isOpen = targetThread.eq(thread);
                        if (!isOpen) {
                            isOpen = targetThread.open({ focus: true, swapOpened: false });
                        }
                        if (!isOpen) {
                            window.open(link.href);
                        }
                    } else {
                        if (this.self_user) {
                            showAccessError();
                        } else {
                            window.open(link.href);
                        }
                    }
                });
                ev.preventDefault();
                return true;
            } else if (link.getAttribute("href")?.startsWith(getOrigin())) {
                showAccessError();
                ev.preventDefault();
                return true;
            }
        } else if (
            this.env.services.ui.isSmall &&
            ev.target.closest(".o-mail-ChatWindow") &&
            link.href &&
            !link.href.startsWith("#")
        ) {
            let url;
            try {
                url = new URL(link.href);
            } catch {
                // Ignore invalid URLs
                return false;
            }
            if (
                browser.location.host === url.host &&
                browser.location.pathname.startsWith("/odoo")
            ) {
                this.ChatWindow.get({ channel: thread.channel })?.fold();
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

    onPushNotificationDisplayed(payload) {
        if (["mail.thread", "discuss.channel"].includes(payload.model)) {
            this.env.services["mail.out_of_focus"]._playSound();
        }
    }

    /**
     * Search and fetch for a partner with a given user or partner id.
     * @param {Object} param0
     * @param {number} param0.userId
     * @param {number} param0.partnerId
     */
    async getChat({ userId, partnerId }) {
        let partner;
        if (userId) {
            const user = await this["res.users"].getOrFetch(userId, ["partner_id"]);
            if (!user?.partner_id) {
                this.env.services.notification.add(_t("You can only chat with existing users."), {
                    type: "warning",
                });
                return;
            }
            partner = user.partner_id;
        } else if (partnerId) {
            partner = await this["res.partner"].getOrFetch(partnerId, ["main_user_id"]);
            if (!partner?.main_user_id) {
                this.env.services.notification.add(
                    _t("You can only chat with partners that have a dedicated user."),
                    { type: "info" }
                );
                return;
            }
        }
        if (!partner) {
            return;
        }
        let chat = partner.searchChat();
        if (!chat?.self_member_id?.is_pinned) {
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

    fillPartnersMentionToken(postData) {
        postData.partner_ids_mention_token ||= {};
        for (const pid of [...postData.partner_ids, ...(postData.partner_cc_ids || [])]) {
            const partner = this["res.partner"].get(pid);
            if (partner?.mention_token) {
                postData.partner_ids_mention_token[pid] = partner.mention_token;
            }
        }
    }

    /** @returns {number} */
    getLastMessageId() {
        return Object.values(this["mail.message"].records).reduce(
            (lastMessageId, message) => Math.max(lastMessageId, message.id),
            0
        );
    }

    handleValidChannelMention(channelLinks) {
        for (const linkEl of channelLinks.filter(
            (el) => !el.querySelector(".fa-comments-o, .fa-hashtag")
        )) {
            const text = linkEl.textContent.substring(1); // remove '#' prefix
            const icon = linkEl.classList.contains("o_channel_redirect_asThread")
                ? "fa fa-comments-o"
                : "fa fa-hashtag";
            const iconEl = renderToElement("mail.Message.mentionedChannelIcon", { icon });
            linkEl.replaceChildren(iconEl);
            linkEl.insertAdjacentText("beforeend", ` ${text}`);
        }
    }

    getMentionsFromText(body, { mentionedPartners = [], mentionedRoles = [], thread } = {}) {
        const validMentions = {};
        const segments = isMarkup(body)
            ? Array.from(
                  createDocumentFragmentFromContent(body).querySelectorAll("a"),
                  (a) => a.textContent
              )
            : [body];
        validMentions.partners = mentionedPartners.filter((partner) =>
            segments.some((segment) => {
                const name = thread?.getPersonaName(partner) ?? partner.displayName;
                return Boolean(
                    (name && segment.includes(`@${name}`)) ||
                        (partner.email && segment.includes(`@${partner.email}`))
                );
            })
        );
        validMentions.roles = mentionedRoles.filter((role) =>
            segments.some((segment) => segment.includes(`@${role.name}`))
        );
        validMentions.specialMentions = this.specialMentions
            .filter((special) => segments.some((segment) => segment.includes(`@${special.label}`)))
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
            isCcEnabled,
            isNote,
            mentionedPartners,
            mentionedRoles,
            subject,
        } = postData;
        const subtype = isNote ? "mail.mt_note" : "mail.mt_comment";
        const validMentions = this.getMentionsFromText(body, {
            mentionedPartners,
            mentionedRoles,
            thread,
        });
        postData = {
            body: await generateEmojisOnHtml(body),
            email_add_signature: emailAddSignature,
            message_type: "comment",
            partner_cc_emails: [],
            partner_cc_ids: [],
            partner_emails: [],
            partner_ids: validMentions?.partners.map((partner) => partner.id) ?? [],
            role_ids: validMentions?.roles.map((role) => role.id) ?? [],
            subtype_xmlid: subtype,
            subject,
        };
        if (!isNote) {
            for (const recipient of [
                ...thread.suggestedRecipients,
                ...thread.additionalRecipients,
            ]) {
                if (!isCcEnabled && recipient.recipient_type === "cc") {
                    continue;
                }
                if (recipient.persona) {
                    if (recipient.recipient_type === "cc") {
                        postData.partner_cc_ids.push(recipient.persona.id);
                    } else {
                        postData.partner_ids.push(recipient.persona.id);
                    }
                } else {
                    if (recipient.recipient_type === "cc") {
                        postData.partner_cc_emails.push(recipient.email);
                    } else {
                        postData.partner_emails.push(recipient.email);
                    }
                }
            }
        }
        this.fillPartnersMentionToken(postData);
        if (attachments.length) {
            postData.attachment_ids = attachments.map(({ id }) => id);
        }
        if (thread.channel && validMentions?.specialMentions.length) {
            postData.special_mentions = validMentions.specialMentions;
        }
        if (attachments.length) {
            postData.attachment_tokens = attachments.map(
                (attachment) => attachment.ownership_token
            );
        }
        // Clean empty fields
        for (const field of [
            "partner_ids",
            "partner_ids_mention_token",
            "partner_cc_ids",
            "partner_emails",
            "partner_cc_emails",
            "role_ids",
        ]) {
            if (Object.prototype.hasOwnProperty.call(postData, field) && !postData[field].length) {
                delete postData[field];
            }
        }
        const params = {
            // Changed in 18.2+: finally get rid of autofollow, following should be done manually
            post_data: postData,
            thread_id: thread.id,
            thread_model: thread.model,
        };
        if (cannedResponseIds?.length) {
            params.canned_response_ids = cannedResponseIds;
        }
        return params;
    }

    notifySendFromMailbox(recordName) {
        this.env.services.notification.add(_t('Message posted on "%s"', recordName), {
            type: "info",
        });
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

    async joinChat(id, forceOpen = false) {
        const { channel } = await this.fetchStoreData(
            "/discuss/get_or_create_chat",
            { partners_to: [id] },
            { requestData: true }
        );
        if (forceOpen) {
            channel.open({ focus: true });
        }
        return channel;
    }

    async openChat(person) {
        const chat = await this.getChat(person);
        chat?.open({ focus: true });
    }

    /**
     * @param {MouseEvent} ev - Click event triggering the popover.
     * @param {number} id - Partner Id of mentioned partner.
     */
    onClickPartnerMention(ev, id) {
        this.openChat({ partnerId: id });
    }

    /**
     * @param {string} searchTerm
     * @param {Thread} thread
     * @param {number} before
     * @param {true|false|undefined} is_notification
     */
    async searchMessagesInThread(searchTerm, thread, before, is_notification) {
        const { count, messages } = await this.fetchStoreData(
            thread.getFetchRoute(),
            {
                ...thread.getFetchParams(),
                fetch_params: {
                    is_notification,
                    search_term: await prettifyMessageText(searchTerm), // formatted like message_post
                    before,
                },
            },
            { readonly: thread.model === "mail.box", requestData: true }
        );
        return {
            count,
            loadMore: messages.length === this.FETCH_LIMIT,
            messages,
        };
    }
}
Store.register();

export const storeService = {
    dependencies: ["bus_service", "im_status", "ui", "popover", "discuss.upgrade"],
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
        store.onStarted();
        return store;
    },
};

registry.category("services").add("mail.store", storeService);
