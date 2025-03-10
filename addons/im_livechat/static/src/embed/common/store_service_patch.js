import { GUEST_TOKEN_STORAGE_KEY, SESSION_STATE } from "@im_livechat/embed/common/livechat_service";

import { Store, storeService } from "@mail/core/common/store_service";

import { patch } from "@web/core/utils/patch";
import { expirableStorage } from "./expirable_storage";
import { Record } from "@mail/model/record";

storeService.dependencies.push("im_livechat.initialized");

patch(Store.prototype, {
    setup() {
        super.setup(...arguments);
        expirableStorage.onChange(GUEST_TOKEN_STORAGE_KEY, (value) => (this.guest_token = value));
        this.guest_token = Record.attr(null, {
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
    },
    async initialize({ force } = {}) {
        const livechatInitialized = this.env.services["im_livechat.initialized"];
        await livechatInitialized.ready;
        const livechatService = this.env.services["im_livechat.livechat"];
        if (livechatService.state === SESSION_STATE.PERSISTED || force) {
            try {
                await super.initialize();
                await this.fetchDeferred;
                livechatService.thread ??= this.store.Thread.get({
                    id: livechatService.savedState?.store["discuss.channel"][0].id,
                    model: "discuss.channel",
                });
            } finally {
                if (!livechatService.thread) {
                    livechatService.leave({ notifyServer: false });
                }
            }
            return;
        }
        if (livechatService.savedState?.store) {
            const { Thread = [] } = this.store.insert(livechatService.savedState.store);
            livechatService.thread = Thread[0];
        }
        this.isReady.resolve();
    },
});
