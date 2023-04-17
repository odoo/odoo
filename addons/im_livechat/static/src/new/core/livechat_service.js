/** @odoo-module */

import { registry } from "@web/core/registry";
import { _t } from "@web/core/l10n/translation";
import { session } from "@web/session";
import { sprintf } from "@web/core/utils/strings";
import { RATING } from "../feedback_panel/feedback_panel";
import { reactive } from "@odoo/owl";

export const RATING_TO_EMOJI = {
    [RATING.GOOD]: "😊",
    [RATING.OK]: "😐",
    [RATING.BAD]: "😞",
};

export const SESSION_STATE = Object.freeze({
    NONE: "NONE",
    CREATED: "CREATED",
    PERSISTED: "PERSISTED",
    CLOSED: "CLOSED",
});

export class LivechatService {
    SESSION_COOKIE = "im_livechat_session";
    /** @type {keyof typeof SESSION_STATE} */
    state = SESSION_STATE.NONE;
    available = false;
    /** @type {string} */
    userName;

    constructor(env, services) {
        this.setup(env, services);
        return reactive(this);
    }

    setup(env, { bus_service: busService, cookie, notification, rpc }) {
        this.env = env;
        this.cookie = cookie;
        this.notification = notification;
        this.busService = busService;
        this.rpc = rpc;

        this.available = session.livechatData?.isAvailable;
        this.userName = this.options.default_username ?? _t("Visitor");
    }

    async initialize() {
        const init = await this.rpc("/im_livechat/init", {
            channel_id: this.options.channel_id,
        });
        this.available = init.available_for_me ?? this.available;
    }

    async _createSession() {
        // TODO - MISSING PREVIOUS OPERATOR ID IN RPC
        const session = await this.rpc(
            "/im_livechat/get_session",
            {
                channel_id: this.options.channel_id,
                anonymous_name: this.userName,
                persisted: false,
            },
            { shadow: true }
        );
        if (session) {
            this.state = SESSION_STATE.CREATED;
            this.cookie.setCookie(this.SESSION_COOKIE, JSON.stringify(session), 60 * 60 * 24); // 1 day cookie.
        }
        return session;
    }

    async _persistSession() {
        const session = await this.rpc("/im_livechat/get_session", {
            channel_id: this.options.channel_id,
            anonymous_name: this.userName,
            persisted: true,
        });
        if (!session || !session.operator_pid) {
            this.cookie.deleteCookie(this.SESSION_COOKIE);
        } else {
            this.state = SESSION_STATE.PERSISTED;
            this.cookie.setCookie(this.SESSION_COOKIE, JSON.stringify(session), 60 * 60 * 24); // 1 day cookie.
        }
        return session;
    }

    async leaveSession() {
        const session = JSON.parse(this.cookie.current[this.SESSION_COOKIE] ?? "{}");
        this.cookie.deleteCookie(this.SESSION_COOKIE);
        this.state = SESSION_STATE.CLOSED;
        if (!session?.uuid) {
            return;
        }
        await this.rpc("/im_livechat/visitor_leave_session", { uuid: session.uuid });
    }

    async getSession({ persisted = false } = {}) {
        let session;
        const sessionCookie = this.cookie.current[this.SESSION_COOKIE];
        session = sessionCookie ? JSON.parse(sessionCookie) : undefined;
        if (session?.uuid && this.state === SESSION_STATE.NONE) {
            // Channel is already created on the server.
            session.messages = await this.rpc("/im_livechat/chat_history", {
                uuid: session.uuid,
                limit: this.MESSAGE_HISTORY_LIMIT,
            });
            session.messages.reverse();
            this.busService.addChannel(session.uuid);
        } else if (!session && this.state === SESSION_STATE.NONE) {
            // First time visitor or not yet created channel.
            session = await this._createSession();
        }
        if (session && persisted && !session.uuid) {
            session = await this._persistSession();
            this.busService.addChannel(session.uuid);
        }
        return session;
    }

    get options() {
        return session.livechatData?.options ?? {};
    }

    /**
     * @param {number} rate
     * @param {string} reason
     */
    async sendFeedback(uuid, rate, reason) {
        await this.rpc("/im_livechat/feedback", { reason, rate, uuid });
        await this.rpc("/im_livechat/chat_post", {
            uuid,
            message_content: sprintf(_t("Rating: %s"), RATING_TO_EMOJI[rate]),
        });
        if (reason) {
            await this.rpc("/im_livechat/chat_post", {
                uuid,
                message_content: sprintf(_t("Rating reason: %s"), reason),
            });
        }
    }

    /**
     * @param {number} uuid
     * @param {string} email
     */
    sendTranscript(uuid, email) {
        return this.rpc("/im_livechat/email_livechat_transcript", { uuid, email });
    }
}

export const publicLivechatService = {
    dependencies: ["cookie", "notification", "rpc", "bus_service"],

    async start(env, services) {
        const livechat = new LivechatService(env, services);
        if (livechat.available) {
            await livechat.initialize();
        }
        return livechat;
    },
};
registry.category("services").add("im_livechat.livechat", publicLivechatService);
