import { SESSION_STATE } from "@im_livechat/embed/common/livechat_service";

import { Store, storeService } from "@mail/core/common/store_service";

import { patch } from "@web/core/utils/patch";
import { session } from "@web/session";

storeService.dependencies.push("im_livechat.initialized");

patch(Store.prototype, {
    async initialize() {
        const livechatInitialized = this.env.services["im_livechat.initialized"];
        await livechatInitialized.ready;
        const livechatService = this.env.services["im_livechat.livechat"];
        if (livechatService.state === SESSION_STATE.PERSISTED) {
            await super.initialize();
            if (!livechatService.thread) {
                livechatService.leave({ notifyServer: false });
            }
            return;
        }
        const messagingData = {
            Store: { settings: {} },
            Thread: [],
        };
        if (session.livechatData?.options.current_partner_id) {
            messagingData.Store.current_partner = {
                id: session.livechatData.options.current_partner_id,
            };
        }
        if (livechatService.savedState?.threadData) {
            messagingData.Thread.push(livechatService.savedState.threadData);
        }
        this.insert(messagingData);
        this.isReady.resolve();
    },
    get initMessagingParams() {
        const params = super.initMessagingParams;
        params.init_messaging.channel_types = ["livechat"];
        return params;
    },
});
