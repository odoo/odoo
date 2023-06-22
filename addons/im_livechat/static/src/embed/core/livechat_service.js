/* @odoo-module */

import { reactive } from "@odoo/owl";

import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { Deferred } from "@web/core/utils/concurrency";
import { session } from "@web/session";

/**
 * @typedef LivechatRule
 * @property {"auto_popup"|undefined} [action]
 * @property {number?} [auto_popup_timer]
 * @property {import("@im_livechat/embed/chatbot/chatbot_model").IChatbot} [chatbot]
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
    CLOSED: "CLOSED",
});

export class LivechatService {
    SESSION_COOKIE = "im_livechat_session";
    OPERATOR_COOKIE = "im_livechat_previous_operator_pid";
    /** @type {keyof typeof SESSION_STATE} */
    state = SESSION_STATE.NONE;
    /** @type {LivechatRule} */
    rule;
    initializedDeferred = new Deferred();
    initialized = false;
    available = false;
    /** @type {string} */
    userName;

    constructor(env, services) {
        this.setup(env, services);
    }

    /**
     * @param {import("@web/env").OdooEnv} env
     * @param {{
     * cookie: typeof import("@web/core/browser/cookie_service").cookieService.start,
     * bus_service: typeof import("@bus/services/bus_service").busService.start,
     * rpc: typeof import("@web/core/network/rpc_service").rpcService.start,
     * "mail.message": import("@mail/core/common/message_service").MessageService,
     * "mail.store": import("@mail/core/common/store_service").Store
     * }} services
     */
    setup(env, services) {
        this.cookie = services.cookie;
        this.busService = services.bus_service;
        this.rpc = services.rpc;
        this.messageService = services["mail.message"];
        this.store = services["mail.store"];

        this.available = session.livechatData?.isAvailable;
        this.userName = this.options.default_username ?? _t("Visitor");
    }

    async initialize() {
        const init = await this.rpc("/im_livechat/init", {
            channel_id: this.options.channel_id,
        });
        this.available = init.available_for_me ?? this.available;
        this.rule = init.rule;
        this.initialized = true;
        this.initializedDeferred.resolve();
    }

    async _createSession({ persisted = false } = {}) {
        const chatbotScriptId = this.sessionCookie
            ? this.sessionCookie.chatbotScriptId
            : this.rule.chatbot?.scriptId;
        const session = await this.rpc(
            "/im_livechat/get_session",
            {
                channel_id: this.options.channel_id,
                anonymous_name: this.userName,
                chatbot_script_id: chatbotScriptId,
                previous_operator_id: this.cookie.current[this.OPERATOR_COOKIE],
                persisted,
            },
            { shadow: true }
        );
        if (!session) {
            this.cookie.deleteCookie(this.SESSION_COOKIE);
            this.state = SESSION_STATE.NONE;
            return;
        }
        session.chatbotScriptId = chatbotScriptId;
        session.isLoaded = true;
        session.status = "ready";
        if (session.operator_pid) {
            this.state = persisted ? SESSION_STATE.PERSISTED : SESSION_STATE.CREATED;
            this.updateSession(session);
        }
        return session;
    }

    /**
     * Update the session with the given values.
     *
     * @param {Object} values
     */
    updateSession(values) {
        const session = JSON.parse(this.cookie.current[this.SESSION_COOKIE] ?? "{}");
        Object.assign(session, values);
        this.cookie.deleteCookie(this.SESSION_COOKIE);
        this.cookie.deleteCookie(this.OPERATOR_COOKIE);
        this.cookie.setCookie(this.SESSION_COOKIE, JSON.stringify(session), 60 * 60 * 24); // 1 day cookie.
        if (session?.operator_pid) {
            this.cookie.setCookie(this.OPERATOR_COOKIE, session.operator_pid[0], 7 * 24 * 60 * 60); // 1 week cookie.
        }
    }

    /**
     * @param {object} param0
     * @param {boolean} param0.notifyServer Whether to call the
     * `visitor_leave_session` route. Note that this route will
     * never be called if the session was not persisted.
     */
    async leaveSession({ notifyServer = true } = {}) {
        const session = JSON.parse(this.cookie.current[this.SESSION_COOKIE] ?? "{}");
        this.cookie.deleteCookie(this.SESSION_COOKIE);
        this.state = SESSION_STATE.CLOSED;
        if (!session?.uuid || !notifyServer) {
            return;
        }
        this.busService.deleteChannel(session.uuid);
        await this.rpc("/im_livechat/visitor_leave_session", { uuid: session.uuid });
    }

    async getSession({ persisted = false } = {}) {
        let session = JSON.parse(this.cookie.current[this.SESSION_COOKIE] ?? false);
        if (session?.uuid && this.state === SESSION_STATE.NONE) {
            // Channel is already created on the server.
            session.messages = await this.rpc("/im_livechat/chat_history", {
                uuid: session.uuid,
            });
            session.messages.reverse();
            this.busService.addChannel(session.uuid);
        }
        if (!session || (!session.uuid && persisted)) {
            session = await this._createSession({ persisted });
            if (session?.uuid) {
                this.busService.addChannel(session.uuid);
            }
        }
        if (session) {
            this.state = session?.uuid ? SESSION_STATE.PERSISTED : SESSION_STATE.CREATED;
        }
        return session;
    }

    /**
     * @param {number} rate
     * @param {string} reason
     */
    async sendFeedback(uuid, rate, reason) {
        return this.rpc("/im_livechat/feedback", { reason, rate, uuid });
    }

    /**
     * @param {number} uuid
     * @param {string} email
     */
    sendTranscript(uuid, email) {
        return this.rpc("/im_livechat/email_livechat_transcript", { uuid, email });
    }

    get options() {
        return session.livechatData?.options ?? {};
    }

    get displayWelcomeMessage() {
        return true;
    }

    get sessionCookie() {
        return JSON.parse(this.cookie.current[this.SESSION_COOKIE] ?? "false");
    }

    get shouldRestoreSession() {
        if (this.state !== SESSION_STATE.NONE) {
            return false;
        }
        return Boolean(this.cookie.current[this.SESSION_COOKIE]);
    }

    /**
     * @returns {import("@mail/core/common/thread_model").Thread|undefined}
     */
    get thread() {
        return Object.values(this.store.threads).find(({ type }) => type === "livechat");
    }
}

export const livechatService = {
    dependencies: ["cookie", "notification", "rpc", "bus_service", "mail.message", "mail.store"],
    start(env, services) {
        const livechat = reactive(new LivechatService(env, services));
        if (livechat.available) {
            livechat.initialize();
        }
        return livechat;
    },
};
registry.category("services").add("im_livechat.livechat", livechatService);
