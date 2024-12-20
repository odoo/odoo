import { expirableStorage } from "@im_livechat/embed/common/expirable_storage";

import { reactive } from "@odoo/owl";
import { rpc } from "@web/core/network/rpc";

import { cookie } from "@web/core/browser/cookie";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { session } from "@web/session";
import { user } from "@web/core/user";

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

const OPERATOR_STORAGE_KEY = "im_livechat_previous_operator";
const GUEST_TOKEN_STORAGE_KEY = "im_livechat_guest_token";
const SAVED_STATE_STORAGE_KEY = "im_livechat.saved_state";
const LIVECHAT_UUID_COOKIE = "im_livechat_uuid";

export function getGuestToken() {
    return expirableStorage.getItem(GUEST_TOKEN_STORAGE_KEY);
}

export class LivechatService {
    /** @type {keyof typeof SESSION_STATE} */
    state = SESSION_STATE.NONE;
    /** @type {LivechatRule} */
    rule;
    initialized = false;
    available = session.livechatData?.isAvailable;
    /** @type {import("models").Thread} */
    thread;
    _onStateChangeCallbacks = {
        [SESSION_STATE.CREATED]: [],
        [SESSION_STATE.PERSISTED]: [],
        [SESSION_STATE.NONE]: [],
    };

    constructor(env, services) {
        this.setup(env, services);
    }

    /**
     * @param {import("@web/env").OdooEnv} env
     * @param {{
     * bus_service: ReturnType<typeof import("@bus/services/bus_service").busService.start>,
     * "mail.store": import("@mail/core/common/store_service").Store
     * }} services
     */
    setup(env, services) {
        this.env = env;
        this.busService = services.bus_service;
        this.notificationService = services.notification;
        this.store = services["mail.store"];
    }

    async initialize() {
        const data =
            this.options?.init ??
            (await rpc("/im_livechat/init", {
                channel_id: this.options.channel_id,
            }));
        this.available = data.available_for_me;
        this.rule = this.store.LivechatRule.insert(data.rule);
        this.store.insert(data.storeData);
        if (this.options?.force_thread) {
            this.state = SESSION_STATE.PERSISTED;
            this.thread = this.store.Thread.insert(this.options.force_thread);
            this._saveLivechatState();
        }
        if (this.savedState) {
            this.state = this.savedState.persisted
                ? SESSION_STATE.PERSISTED
                : SESSION_STATE.CREATED;
        }
        if (this.state === SESSION_STATE.PERSISTED) {
            await this.busService.addChannel(`mail.guest_${this.guestToken}`);
        }
        this.initialized = true;
        this.env.services["im_livechat.initialized"].ready.resolve();
    }

    /**
     * Open a new live chat thread.
     *
     * @returns {Promise<import("models").Thread|undefined>}
     */
    async open() {
        await this._createThread({ persist: false });
        this.thread?.openChatWindow();
    }

    /**
     * Persist the livechat thread if it is not done yet and swap it with the
     * temporary thread.
     *
     * @returns {Promise<import("models").Thread|undefined>}
     */
    async persist() {
        if (this.state === SESSION_STATE.PERSISTED) {
            return this.thread;
        }
        const temporaryThread = this.thread;
        await this._createThread({ persist: true });
        if (temporaryThread) {
            const chatWindow = this.store.ChatWindow.get({ thread: temporaryThread });
            temporaryThread.delete();
            await chatWindow.close();
        }
        if (!this.thread) {
            return;
        }
        this.store.chatHub.opened.add({ thread: this.thread }).autofocus++;
        await this.busService.addChannel(`mail.guest_${this.guestToken}`);
        await this.env.services["mail.store"].initialize();
        return this.thread;
    }

    /**
     * @param {object} param0
     * @param {boolean} param0.notifyServer Whether to call the
     * `visitor_leave_session` route. Note that this route will never be called
     * if the session was not persisted.
     */
    async leave({ notifyServer = true } = {}) {
        try {
            if (this.thread && this.state === SESSION_STATE.PERSISTED && notifyServer) {
                await rpc("/im_livechat/visitor_leave_session", { channel_id: this.thread.id });
            }
        } finally {
            this.thread = undefined;
            expirableStorage.removeItem(SAVED_STATE_STORAGE_KEY);
            cookie.delete(LIVECHAT_UUID_COOKIE);
            this.state = SESSION_STATE.NONE;
            await Promise.all(this._onStateChangeCallbacks[SESSION_STATE.NONE].map((fn) => fn()));
        }
    }

    /**
     * Add a callback to be executed when the livechat service state changes.
     *
     * @param {keyof typeof SESSION_STATE} state
     * @param {Function} callback
     */
    onStateChange(state, callback) {
        this._onStateChangeCallbacks[state].push(callback);
    }

    /**
     * Save the current live chat state. Only save the strict minimum if the
     * thread is persisted.
     *
     * @param {Object} [saveData]
     */
    _saveLivechatState(saveData) {
        const { guest_token } = this.store;
        if (guest_token) {
            expirableStorage.setItem(GUEST_TOKEN_STORAGE_KEY, guest_token);
        }
        const ONE_DAY_TTL = 60 * 60 * 24;
        if (this.thread.uuid) {
            cookie.set(LIVECHAT_UUID_COOKIE, this.thread.uuid, ONE_DAY_TTL);
        }
        const persisted = this.state === SESSION_STATE.PERSISTED;
        expirableStorage.setItem(
            SAVED_STATE_STORAGE_KEY,
            JSON.stringify({
                livechatUserId: this.savedState?.livechatUserId ?? user.userId,
                persisted,
                store: persisted ? { "discuss.channel": [{ id: this.thread.id }] } : saveData,
            }),
            ONE_DAY_TTL
        );
        if (this.thread.operator) {
            expirableStorage.setItem(
                OPERATOR_STORAGE_KEY,
                this.thread.operator.id,
                ONE_DAY_TTL * 7
            );
        }
    }

    /**
     * @param {object} param0
     * @param {boolean} [param0.persist=false]
     * @returns {Promise<import("models").Thread>}
     */
    async _createThread({ persist = false }) {
        const data = await rpc(
            "/im_livechat/get_session",
            {
                channel_id: this.options.channel_id,
                anonymous_name: this.options.default_username ?? _t("Visitor"),
                chatbot_script_id: this.savedState
                    ? this.thread.chatbot?.script.id
                    : this.rule.chatbotScript?.id,
                previous_operator_id: expirableStorage.getItem(OPERATOR_STORAGE_KEY),
                persisted: persist,
            },
            { shadow: true }
        );
        // clean copy of data for saving in storage, because store insert will add cyclic references
        const saveData = JSON.parse(JSON.stringify(data));
        const { Thread = [] } = this.store.insert(data);
        this.thread = Thread[0];
        if (!this.thread?.operator) {
            this.notificationService.add(_t("No available collaborator, please try again later."));
            this.leave({ notifyServer: false });
            return;
        }
        this.state = persist ? SESSION_STATE.PERSISTED : SESSION_STATE.CREATED;
        this._saveLivechatState(saveData);
        await Promise.all(this._onStateChangeCallbacks[this.state].map((fn) => fn()));
    }

    get options() {
        return session.livechatData?.options ?? {};
    }

    get savedState() {
        return JSON.parse(expirableStorage.getItem(SAVED_STATE_STORAGE_KEY) ?? false);
    }

    /**
     * @returns {string|undefined}
     */
    get guestToken() {
        return getGuestToken();
    }
}

export const livechatService = {
    dependencies: ["bus_service", "im_livechat.initialized", "mail.store", "notification"],
    start(env, services) {
        const livechat = reactive(new LivechatService(env, services));
        (async () => {
            // Live chat state should be deleted if it is linked to another user
            // (log in/out after chat start).
            if ((livechat.savedState?.livechatUserId || false) !== (user.userId || false)) {
                await livechat.leave({ notifyServer: false });
            }
            if (livechat.available) {
                livechat.initialize();
            }
        })();
        return livechat;
    },
};
registry.category("services").add("im_livechat.livechat", livechatService);
