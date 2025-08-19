import { expirableStorage } from "@im_livechat/core/common/expirable_storage";

import { reactive } from "@odoo/owl";
import { rpc } from "@web/core/network/rpc";

import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { session } from "@web/session";
import { canLoadLivechat } from "@im_livechat/embed/common/misc";

export const RATING = Object.freeze({
    GOOD: 5,
    OK: 3,
    BAD: 1,
});

export const ODOO_VERSION_KEY = `${location.origin.replace(
    /:\/{0,2}/g,
    "_"
)}_im_livechat.odoo_version`;

const OPERATOR_STORAGE_KEY = "im_livechat_previous_operator";

export class LivechatService {
    initialized = false;

    constructor(env, services) {
        this.setup(env, services);
    }

    /**
     * @param {import("@web/env").OdooEnv} env
     * @param {{
     * "mail.store": import("@mail/core/common/store_service").Store
     * }} services
     */
    setup(env, services) {
        this.env = env;
        this.notificationService = services.notification;
        this.store = services["mail.store"];
    }

    async initialize() {
        this.store.fetchStoreData("init_livechat", this.options.channel_id, { readonly: false });
        if (this.options.chatbot_test_store) {
            await this.store.chatHub.initPromise;
            this.store.insert(this.options.chatbot_test_store);
        }
    }

    /**
     * Open a new live chat thread.
     *
     * @returns {Promise<import("models").Thread|undefined>}
     */
    async open(options = {}) {
        const thread = await this._createThread({ persist: false, options});
        await thread?.openChatWindow({ focus: true });
        return thread;
    }

    /**
     * Persist the livechat thread if it is not done yet and swap it with the
     * temporary thread.
     *
     * @returns {Promise<import("models").Thread|undefined>}
     */
    async persist(thread) {
        if (!thread.isTransient) {
            return thread;
        }
        const temporaryThread = thread;
        const deleteTemporary = async () => {
            await this.store.chatHub.initPromise;
            await this.store.ChatWindow.get({ thread: temporaryThread })?.close({ force: true });
            temporaryThread?.delete();
        };
        const savedThread = await this._createThread({ originThread: thread, persist: true });
        if (!savedThread) {
            await deleteTemporary();
            return;
        }
        savedThread.fetchNewMessages();
        this.env.services["mail.store"].initialize();
        savedThread.readyToSwapDeferred.then(async () => {
            if (!savedThread?.exists()) {
                return;
            }
            // Do not load unread messaes: new messages were loaded to avoid
            // flickering, we do not want another load that would result in the
            // same issue.
            savedThread.scrollUnread = false;
            deleteTemporary();
            savedThread.openChatWindow({ focus: true });
        });
        return savedThread;
    }

    /**
     * @param {object} param0
     * @param {boolean} param0.notifyServer Whether to call the `visitor_leave_session` route.
     */
    async leave(thread) {
        await rpc("/im_livechat/visitor_leave_session", { channel_id: thread.id });
    }

    /**
     * @param {object} param0
     * @param {boolean} [param0.persist=false]
     * @param {import("models").Thread} [param0.originThread]
     * @returns {Promise<import("models").Thread>}
     */
    async _createThread({ originThread, persist = false, options = {} }) {
        const { store_data, channel_id } = await rpc(
            "/im_livechat/get_session",
            {
                channel_id: options.channel_id ?? this.options.channel_id,
                previous_operator_id: expirableStorage.getItem(OPERATOR_STORAGE_KEY),
                chatbot_script_id: originThread?.chatbot?.script.id ?? this.store.livechat_rule?.chatbot_script_id?.id,
                persisted: options.persist ?? persist,
                ...this.getSessionExtraParams(originThread, options),
            },
            { silent: true }
        );
        if (!channel_id) {
            this.notificationService.add(_t("No available collaborator, please try again later."));
            return;
        }
        this.store.insert(store_data);
        const thread = this.store.Thread.get({ id: channel_id, model: "discuss.channel" });
        const ONE_DAY_TTL = 60 * 60 * 24;
        expirableStorage.setItem(
            "im_livechat_previous_operator",
            thread.livechat_operator_id.id,
            ONE_DAY_TTL * 7
        );
        return thread;
    }

    getSessionExtraParams(thread, options) {
        return {};
    }

    get options() {
        return session.livechatData?.options ?? {};
    }
}

export const livechatService = {
    dependencies: ["mail.store", "notification"],
    start(env, services) {
        const livechat = reactive(new LivechatService(env, services));
        if (canLoadLivechat()) {
            livechat.initialize();
        }
        return livechat;
    },
};
registry.category("services").add("im_livechat.livechat", livechatService);
