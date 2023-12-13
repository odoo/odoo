/* @odoo-module */
import { SESSION_STATE } from "@im_livechat/embed/common/livechat_service";

import { Messaging, messagingService } from "@mail/core/common/messaging_service";

import { patch } from "@web/core/utils/patch";
import { session } from "@web/session";

messagingService.dependencies.push("im_livechat.livechat");

patch(Messaging.prototype, {
    initialize() {
        if (this.env.services["im_livechat.livechat"].state === SESSION_STATE.PERSISTED) {
            return super.initialize();
        }
        if (session.livechatData?.options.current_partner_id) {
            this.store.self = {
                type: "partner",
                id: session.livechatData.options.current_partner_id,
            };
        }
        this.store.isMessagingReady = true;
        this.isReady.resolve({
            Thread: [],
            settings: {},
        });
    },
    get initMessagingParams() {
        return {
            ...super.initMessagingParams,
            context: {
                is_for_livechat: true,
            },
        };
    },
});
