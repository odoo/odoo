/* @odoo-module */

import { reactive } from "@odoo/owl";

import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { Deferred } from "@web/core/utils/concurrency";
import { session } from "@web/session";
import { expirableStorage } from "./misc";

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
    SESSION_STORAGE_KEY = "im_livechat_session";
    OPERATOR_STORAGE_KEY = "im_livechat_previous_operator_pid";
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
     * bus_service: typeof import("@bus/services/bus_service").busService.start,
     * rpc: typeof import("@web/core/network/rpc_service").rpcService.start,
     * "mail.message": import("@mail/core/common/message_service").MessageService,
     * "mail.store": import("@mail/core/common/store_service").Store
     * }} services
     */
    setup(env, services) {
        this.busService = services.bus_service;
        this.rpc = services.rpc;
        this.messageService = services["mail.message"];
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
        }
        this.available = init?.available_for_me ?? this.available;
        this.rule = init?.rule ?? {};
        this.initialized = true;
        this.initializedDeferred.resolve();
    }

    async _createSession({ persisted = false } = {}) {
        const chatbotScriptId = this.sessionData
            ? this.sessionData.chatbotScriptId
            : this.rule.chatbot?.scriptId;
        const session = await this.rpc(
            "/im_livechat/get_session",
            {
                channel_id: this.options.channel_id,
                anonymous_name: this.userName,
                chatbot_script_id: chatbotScriptId,
                previous_operator_id: expirableStorage.getItem(this.OPERATOR_STORAGE_KEY),
                persisted,
            },
            { shadow: true }
        );
        if (!session) {
            expirableStorage.removeItem(this.SESSION_STORAGE_KEY);
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
        const session = JSON.parse(expirableStorage.getItem(this.SESSION_STORAGE_KEY) ?? "{}");
        Object.assign(session, {
            visitor_uid: this.visitorUid,
            ...values,
        });
        expirableStorage.removeItem(this.SESSION_STORAGE_KEY);
        expirableStorage.removeItem(this.OPERATOR_STORAGE_KEY);
        expirableStorage.setItem(
            this.SESSION_STORAGE_KEY,
            JSON.stringify(session).replaceAll("→", " "),
            60 * 60 * 24 // kept for 1 day.
        );
        if (session?.operator_pid) {
            expirableStorage.setItem(
                this.OPERATOR_STORAGE_KEY,
                session.operator_pid[0],
                7 * 24 * 60 * 60 // kept for 1 week.
            );
        }
    }

    /**
     * @param {object} param0
     * @param {boolean} param0.notifyServer Whether to call the
     * `visitor_leave_session` route. Note that this route will
     * never be called if the session was not persisted.
     */
    async leaveSession({ notifyServer = true } = {}) {
        const session = JSON.parse(expirableStorage.getItem(this.SESSION_STORAGE_KEY) ?? "{}");
        expirableStorage.removeItem(this.SESSION_STORAGE_KEY);
        this.state = SESSION_STATE.CLOSED;
        if (!session?.uuid || !notifyServer) {
            return;
        }
        this.busService.deleteChannel(session.uuid);
        await this.rpc("/im_livechat/visitor_leave_session", { uuid: session.uuid });
    }

    async getSession({ persisted = false } = {}) {
        let session = JSON.parse(expirableStorage.getItem(this.SESSION_STORAGE_KEY) ?? false);
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

    get sessionData() {
        return JSON.parse(expirableStorage.getItem(this.SESSION_STORAGE_KEY) ?? false);
    }

    get shouldRestoreSession() {
        if (this.state !== SESSION_STATE.NONE) {
            return false;
        }
        return Boolean(expirableStorage.getItem(this.SESSION_STORAGE_KEY));
    }

    get shouldDeleteSession() {
        return this.sessionData && this.sessionData.visitor_uid !== session.user_id;
    }

    /**
     * @returns {import("@mail/core/common/thread_model").Thread|undefined}
     */
    get thread() {
        return Object.values(this.store.threads).find(({ type }) => type === "livechat");
    }

    get visitorUid() {
        const data = this.sessionData;
        return data && "visitor_uid" in data ? data.visitor_uid : session.user_id;
    }
}

export const livechatService = {
    dependencies: ["notification", "rpc", "bus_service", "mail.message", "mail.store"],
    start(env, services) {
        const livechat = reactive(new LivechatService(env, services));
        if (livechat.shouldDeleteSession) {
            livechat.leaveSession();
            livechat.state = SESSION_STATE.NONE;
        }
        if (livechat.available) {
            livechat.initialize();
        }
        return livechat;
    },
};
registry.category("services").add("im_livechat.livechat", livechatService);
