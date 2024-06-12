/* @odoo-module */

import { Record } from "@mail/core/common/record";
import { reactive } from "@odoo/owl";

import { browser } from "@web/core/browser/browser";
import { cookie } from "@web/core/browser/cookie";
import { _t } from "@web/core/l10n/translation";
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

export class LivechatService {
    static TEMPORARY_ID = "livechat_temporary_thread";
    SESSION_COOKIE = "im_livechat_session";
    OPERATOR_COOKIE = "im_livechat_previous_operator_pid";
    GUEST_TOKEN_STORAGE_KEY = "im_livechat_guest_token";
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
     * rpc: ReturnType<typeof import("@web/core/network/rpc_service").rpcService.start>,
     * "mail.chat_window": import("@mail/core/common/chat_window_service").ChatWindowService>,
     * "mail.store": import("@mail/core/common/store_service").Store
     * }} services
     */
    setup(env, services) {
        this.env = env;
        this.busService = services.bus_service;
        this.chatWindowService = services["mail.chat_window"];
        this.rpc = services.rpc;
        this.notificationService = services.notification;
        this.store = services["mail.store"];
        this.available = session.livechatData?.isAvailable;
        this.userName = this.options.default_username ?? _t("Visitor");
    }

    async initialize() {
        let init;
        if (!this.options.isTestChatbot) {
            init = await this.rpc("/im_livechat/init", {
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
        if (Record.isRecord(values?.channel)) {
            values.channel = values.channel.toData();
        }
        const session = JSON.parse(cookie.get(this.SESSION_COOKIE) ?? "{}");
        Object.assign(session, {
            visitor_uid: this.visitorUid,
            ...values,
        });
        cookie.delete(this.SESSION_COOKIE);
        cookie.delete(this.OPERATOR_COOKIE);
        cookie.set(this.SESSION_COOKIE, JSON.stringify(session).replaceAll("→", " "), 60 * 60 * 24); // 1 day cookie.
        if (session?.operator_pid) {
            cookie.set(this.OPERATOR_COOKIE, session.operator_pid[0], 7 * 24 * 60 * 60); // 1 week cookie.
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
                await this.rpc("/im_livechat/visitor_leave_session", { uuid: session.uuid });
            }
        } finally {
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
        this.persistThreadPromise =
            this.persistThreadPromise ?? this.getOrCreateThread({ persist: true });
        try {
            await this.persistThreadPromise;
        } finally {
            this.persistThreadPromise = null;
        }
        const chatWindow = this.store.discuss.chatWindows.find(
            (c) => c.thread.id === LivechatService.TEMPORARY_ID
        );
        if (chatWindow) {
            chatWindow.thread?.delete();
            if (!this.thread) {
                await this.chatWindowService.close(chatWindow);
                return;
            }
            chatWindow.thread = this.thread;
            if (this.env.services["im_livechat.chatbot"].active) {
                await this.env.services["im_livechat.chatbot"].postWelcomeSteps();
            }
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
        let isNewlyCreated = false;
        if (!threadData || (!threadData.uuid && persist)) {
            const chatbotScriptId = this.sessionCookie
                ? this.sessionCookie.chatbot_script_id
                : this.rule.chatbot?.scriptId;
            threadData = await this.rpc(
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
            isNewlyCreated = true;
        }
        if (!threadData?.operator_pid) {
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
            id: threadData.id ?? LivechatService.TEMPORARY_ID,
            isLoaded: !threadData.id || isNewlyCreated,
            model: "discuss.channel",
            type: "livechat",
            isNewlyCreated,
        });
        this.state = thread.uuid ? SESSION_STATE.PERSISTED : SESSION_STATE.CREATED;
        if (this.state === SESSION_STATE.PERSISTED && !this.sessionInitialized) {
            this.sessionInitialized = true;
            await this.initializePersistedSession();
        }
        return thread;
    }

    async initializePersistedSession() {
        await this.busService.addChannel(`mail.guest_${this.guestToken}`);
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
        return localStorage.getItem(this.GUEST_TOKEN_STORAGE_KEY);
    }

    /**
     * @returns {import("models").Thread|undefined}
     */
    get thread() {
        return Object.values(this.store.Thread.records).find(
            ({ id, type }) =>
                type === "livechat" &&
                id === (this.sessionCookie?.id ?? LivechatService.TEMPORARY_ID)
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
    dependencies: [
        "bus_service",
        "mail.chat_window",
        "mail.store",
        "notification",
        "notification",
        "rpc",
    ],
    start(env, services) {
        const livechat = reactive(new LivechatService(env, services));
        if (livechat.available) {
            livechat.initialize();
        }
        return livechat;
    },
};
registry.category("services").add("im_livechat.livechat", livechatService);
