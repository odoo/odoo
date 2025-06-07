import { SESSION_STATE } from "@im_livechat/embed/common/livechat_service";

import { Store, storeService } from "@mail/core/common/store_service";

import { patch } from "@web/core/utils/patch";

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
    },
    get initMessagingParams() {
        const params = super.initMessagingParams;
        params.init_messaging.channel_types = ["livechat"];
        return params;
    },
});
