/* @odoo-module */

import { Messaging } from "@mail/core/common/messaging_service";

import { patch } from "@web/core/utils/patch";

patch(Messaging.prototype, {
    async initialize() {
        if (!this.store.isMessagingReady) {
            this.store.isMessagingReady = true;
            this.isReady.resolve({
                channels: [],
                current_user_settings: {},
            });
            return;
        }
        return super.initialize();
    },
});
