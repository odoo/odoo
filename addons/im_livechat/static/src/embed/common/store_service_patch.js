import { expirableStorage } from "@im_livechat/core/common/expirable_storage";
import { Store } from "@mail/core/common/store_service";
import { fields } from "@mail/model/export";

import { patch } from "@web/core/utils/patch";

<<<<<<< b865fb3e4fce8f0432e3a8fee8e6b812c1f68940
export const GUEST_TOKEN_STORAGE_KEY = "im_livechat_guest_token";
/** @type {import("models").Store} */
const StorePatch = {
    setup() {
        super.setup(...arguments);
        this.activeLivechats = fields.Many("Thread", { inverse: "storeAsActiveLivechats" });
        this.activeVisitorLivechats = fields.Many("Thread", {
            inverse: "storeAsActiveVisitorLivechats",
        });
        expirableStorage.onChange(GUEST_TOKEN_STORAGE_KEY, (value) => (this.guest_token = value));
        this.guest_token = fields.Attr(null, {
            compute() {
                return expirableStorage.getItem(GUEST_TOKEN_STORAGE_KEY);
            },
            onUpdate() {
                if (this.guest_token) {
                    expirableStorage.setItem(GUEST_TOKEN_STORAGE_KEY, this.guest_token);
                    this.store.env.services.bus_service.addChannel(
                        `mail.guest_${this.guest_token}`
                    );
                    return;
                }
                expirableStorage.removeItem(GUEST_TOKEN_STORAGE_KEY);
                this.store.env.services.bus_service.deleteChannel(`mail.guest_${this.guest_token}`);
            },
            eager: true,
        });
        this.livechat_rule = fields.One("im_livechat.channel.rule");
        this.livechat_available = false;
||||||| c2fe265e7e53195c68f5e758e26067e3ca055c3c
storeService.dependencies.push("im_livechat.initialized");

patch(Store.prototype, {
    async initialize() {
        const livechatInitialized = this.env.services["im_livechat.initialized"];
        await livechatInitialized.ready;
        const livechatService = this.env.services["im_livechat.livechat"];
        if (livechatService.state === SESSION_STATE.PERSISTED) {
            await super.initialize();
            livechatService.thread ??= this.store.Thread.get({
                id: livechatService.savedState?.store["discuss.channel"][0].id,
                model: "discuss.channel",
            });
            if (!livechatService.thread) {
                livechatService.leave({ notifyServer: false });
            }
            return;
        }
        if (livechatService.savedState?.store) {
            const { Thread = [] } = this.store.insert(livechatService.savedState.store);
            livechatService.thread = Thread[0];
        }
        this.isReady.resolve();
=======
storeService.dependencies.push("im_livechat.initialized");

patch(Store.prototype, {
    async initialize() {
        const livechatInitialized = this.env.services["im_livechat.initialized"];
        await livechatInitialized.ready;
        const livechatService = this.env.services["im_livechat.livechat"];
        if (livechatService.state === SESSION_STATE.PERSISTED) {
            await super.initialize();
            livechatService.thread ??= this.store.Thread.get({
                id: livechatService.savedState?.store["discuss.channel"][0].id,
                model: "discuss.channel",
            });
            if (!livechatService.thread) {
                livechatService.leave({ notifyServer: false });
            }
            return;
        }
        const savedStore = livechatService.savedState?.store;
        if (savedStore) {
            const { chatbot } = savedStore["discuss.channel"][0];
            if (chatbot && livechatService.rule?.chatbotScript?.id === chatbot.script.id) {
                chatbot.script = livechatService.rule.chatbotScript;
            }
            const { Thread = [] } = this.store.insert(savedStore);
            livechatService.thread = Thread[0];
        }
        this.isReady.resolve();
>>>>>>> 174af075b8aea8fbaf2cd70c5db79335e99948e1
    },
};
patch(Store.prototype, StorePatch);
