/* @odoo-module */

import { Messaging } from "@mail/core/common/messaging_service";

import { patch } from "@web/core/utils/patch";
import { session } from "@web/session";

patch(Messaging.prototype, "im_livechat", {
    initialize() {
        if (session.livechatData?.options.current_partner_id) {
            this.store.user = this.personaService.insert({
                type: "partner",
                id: session.livechatData.options.current_partner_id,
            });
        }
        this.store.isMessagingReady = true;
        this.isReady.resolve({
            channels: [],
            current_user_settings: {},
        });
    },
});
