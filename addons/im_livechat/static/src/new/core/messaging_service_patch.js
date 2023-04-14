/** @odoo-module */

import { Messaging } from "@mail/core/messaging_service";
import { patch } from "@web/core/utils/patch";

patch(Messaging.prototype, "im_livechat", {
    initialize() {
        this.isReady.resolve();
        this.store.isMessagingReady = true;
    },
});
