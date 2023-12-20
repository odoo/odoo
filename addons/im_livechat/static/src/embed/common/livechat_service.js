/* @odoo-module */

import { Record } from "@mail/core/common/record";
import { reactive } from "@odoo/owl";

import { browser } from "@web/core/browser/browser";
import { cookie } from "@web/core/browser/cookie";
import { _t } from "@web/core/l10n/translation";
import { rpc } from "@web/core/network/rpc";
import { registry } from "@web/core/registry";
import { Deferred } from "@web/core/utils/concurrency";
import { session } from "@web/session";

/**
 * @typedef LivechatRule
 * @property {"auto_popup"|"display_button_and_text"|undefined} [action]
 * @property {number?} [auto_popup_timer]
 * @property {import("@im_livechat/embed/common/chatbot/chatbot_model").IChatbot} [chatbot]
 */

export const RATING = Object.freeze({
    GOOD: 5,
    OK: 3,
    BAD: 1,
});

export const SESSION_STATE = Object.freeze({
    NONE: "NONE",
    CREATED: "CREATED",
    PERSISTED: "PERSISTED",
});

export const ODOO_VERSION_KEY = `${location.origin.replace(
    /:\/{0,2}/g,
    "_"
)}_im_livechat.odoo_version`;

const TEMPORARY_ID = -1;
const SESSION_COOKIE = "im_livechat_session";
const OPERATOR_COOKIE = "im_livechat_previous_operator";
const GUEST_TOKEN_STORAGE_KEY = "im_livechat_guest_token";

export function getGuestToken() {
    return localStorage.getItem(GUEST_TOKEN_STORAGE_KEY);
}

export class LivechatService {
    TEMPORARY_ID = TEMPORARY_ID;
    SESSION_COOKIE = SESSION_COOKIE;
    OPERATOR_COOKIE = OPERATOR_COOKIE;
    GUEST_TOKEN_STORAGE_KEY = GUEST_TOKEN_STORAGE_KEY;
    /** @type {keyof typeof SESSION_STATE} */
    state = SESSION_STATE.NONE;
    /** @type {LivechatRule} */
    rule;
    initializedDeferred = new Deferred();
    initialized = false;
    persistThreadPromise = null;
    sessionInitialized = false;
    available = false;
    /** @type {string} */
    userName;

    constructor(env, services) {
        this.setup(env, services);
    }

    /**
     * @param {import("@web/env").OdooEnv} env
     * @param {{
     * bus_service: ReturnType<typeof import("@bus/services/bus_service").busService.start>,
     * "mail.chat_window": import("@mail/core/common/chat_window_service").ChatWindowService>,
     * "mail.store": import("@mail/core/common/store_service").Store
     * }} services
     */
    setup(env, services) {
        this.env = env;
        this.busService = services.bus_service;
        this.chatWindowService = services["mail.chat_window"];
        this.notificationService = services.notification;
        this.store = services["mail.store"];
        this.available = session.livechatData?.isAvailable;
        this.userName = this.options.default_username ?? _t("Visitor");
    }

    async initialize() {
        let init;
        if (!this.options.isTestChatbot) {
            init = await rpc("/im_livechat/init", {
                channel_id: this.options.channel_id,
            });
            // Clear session if it is outdated.
            const prevOdooVersion = browser.localStorage.getItem(ODOO_VERSION_KEY);
            const currOdooVersion = init?.odoo_version;
            const visitorUid = this.visitorUid || false;
            const userId = session.user_id || false;
            if (
                prevOdooVersion !== currOdooVersion ||
                (this.sessionCookie && visitorUid !== userId)
            ) {
                this.leaveSession({ notifyServer: false });
            }
            browser.localStorage.setItem(ODOO_VERSION_KEY, currOdooVersion);
        }
        this.available = init?.available_for_me ?? this.available;
        this.rule = init?.rule ?? {};
        this.initialized = true;
        this.initializedDeferred.resolve();
    }

    /**
     * Update the session with the given values.
     *
     * @param {Object} values
     */
    updateSession(values) {
        for (const key of Object.keys(values)) {
            if (Record.isRecord(values[key])) {
                values[key] = values[key].toData();
            }
        }
        const session = JSON.parse(cookie.get(this.SESSION_COOKIE) ?? "{}");
        Object.assign(session, {
            visitor_uid: this.visitorUid,
            ...values,
        });
        cookie.delete(this.SESSION_COOKIE);
        cookie.delete(this.OPERATOR_COOKIE);
        cookie.set(this.SESSION_COOKIE, JSON.stringify(session).replaceAll("→", " "), 60 * 60 * 24); // 1 day cookie.
        if (session?.operator) {
            cookie.set(this.OPERATOR_COOKIE, session.operator.id, 7 * 24 * 60 * 60); // 1 week cookie.
        }
    }

    /**
     * @param {object} param0
     * @param {boolean} param0.notifyServer Whether to call the
     * `visitor_leave_session` route. Note that this route will
     * never be called if the session was not persisted.
     */
    async leaveSession({ notifyServer = true } = {}) {
        const session = JSON.parse(cookie.get(this.SESSION_COOKIE) ?? "{}");
        try {
            if (session?.uuid && notifyServer) {
                this.busService.deleteChannel(session.uuid);
                await rpc("/im_livechat/visitor_leave_session", { uuid: session.uuid });
            }
        } finally {
            localStorage.removeItem(this.GUEST_TOKEN_STORAGE_KEY);
            cookie.delete(this.SESSION_COOKIE);
            this.state = SESSION_STATE.NONE;
            this.sessionInitialized = false;
        }
    }

    /**
     * Persist the livechat thread if it is not done yet and swap it with the
     * temporary thread.
     *
     * @returns {Promise<import("models").Thread|undefined>}
     */
    async persistThread() {
        if (this.state === SESSION_STATE.PERSISTED) {
            return this.thread;
        }
        const temporaryThread = this.thread;
        this.persistThreadPromise =
            this.persistThreadPromise ?? this.getOrCreateThread({ persist: true });
        try {
            await this.persistThreadPromise;
        } finally {
            this.persistThreadPromise = null;
        }
        if (temporaryThread) {
            const chatWindow = this.store.discuss.chatWindows.find(
                (c) => c.thread?.id === temporaryThread.id
            );
            temporaryThread.delete();
            this.env.services["mail.chat_window"].close(chatWindow);
        }
        if (!this.thread) {
            return;
        }
        this.chatWindowService.open(this.thread);
        if (this.env.services["im_livechat.chatbot"].active) {
            await this.env.services["im_livechat.chatbot"].postWelcomeSteps();
        }
        return this.thread;
    }

    /**
     *
     * @param {{ persist: boolean}} [param0]
     * @returns {Promise<import("models").Thread>|undefined"}
     */
    async getOrCreateThread({ persist = false } = {}) {
        let threadData = this.sessionCookie;
        if (!threadData || (!threadData.uuid && persist)) {
            const chatbotScriptId = this.sessionCookie
                ? this.sessionCookie.chatbot_script_id
                : this.rule.chatbot?.scriptId;
            threadData = await rpc(
                "/im_livechat/get_session",
                {
                    channel_id: this.options.channel_id,
                    anonymous_name: this.userName,
                    chatbot_script_id: chatbotScriptId,
                    previous_operator_id: cookie.get(this.OPERATOR_COOKIE),
                    persisted: persist,
                },
                { shadow: true }
            );
        }
        if (!threadData?.operator) {
            this.notificationService.add(_t("No available collaborator, please try again later."));
            this.leaveSession({ notifyServer: false });
            return;
        }
        if ("guest_token" in threadData) {
            localStorage.setItem(this.GUEST_TOKEN_STORAGE_KEY, threadData.guest_token);
            delete threadData.guest_token;
        }
        this.updateSession(threadData);
        const thread = this.store.Thread.insert({
            ...threadData,
            id: threadData.id ?? this.TEMPORARY_ID,
            isLoaded: !threadData.id,
            model: "discuss.channel",
            channel_type: "livechat",
        });
        this.state = thread.uuid ? SESSION_STATE.PERSISTED : SESSION_STATE.CREATED;
        if (this.state === SESSION_STATE.PERSISTED && !this.sessionInitialized) {
            this.sessionInitialized = true;
            await this.initializePersistedSession();
        }
        return thread;
    }

    async initializePersistedSession() {
        if (this.guestToken) {
            await this.busService.updateContext({
                ...this.busService.context,
                guest_token: this.guestToken,
            });
        }
        if (this.busService.isActive) {
            this.busService.forceUpdateChannels();
        } else {
            await this.busService.start();
        }
        await this.env.services["mail.messaging"].initialize();
    }

    get options() {
        return session.livechatData?.options ?? {};
    }

    get displayWelcomeMessage() {
        return true;
    }

    get sessionCookie() {
        return JSON.parse(cookie.get(this.SESSION_COOKIE) ?? "false");
    }

    get shouldRestoreSession() {
        if (this.state !== SESSION_STATE.NONE) {
            return false;
        }
        return Boolean(cookie.get(this.SESSION_COOKIE));
    }

    /**
     * @returns {string|undefined}
     */
    get guestToken() {
        return getGuestToken();
    }

    /**
     * @returns {import("models").Thread|undefined}
     */
    get thread() {
        return Object.values(this.store.Thread.records).find(
            ({ id, type }) =>
                type === "livechat" && id === (this.sessionCookie?.id ?? this.TEMPORARY_ID)
        );
    }

    get visitorUid() {
        const sessionCookie = this.sessionCookie;
        return sessionCookie && "visitor_uid" in sessionCookie
            ? sessionCookie.visitor_uid
            : session.user_id;
    }
}

export const livechatService = {
    dependencies: ["bus_service", "mail.chat_window", "mail.store", "notification"],
    start(env, services) {
        const livechat = reactive(new LivechatService(env, services));
        if (livechat.available) {
            livechat.initialize();
        }
        return livechat;
    },
};
registry.category("services").add("im_livechat.livechat", livechatService);
