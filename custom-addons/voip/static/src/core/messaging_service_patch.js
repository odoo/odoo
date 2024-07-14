/* @odoo-module */

import { Messaging } from "@mail/core/common/messaging_service";

import { patch } from "@web/core/utils/patch";

patch(Messaging.prototype, {
    initMessagingCallback({ voipConfig }) {
        super.initMessagingCallback(...arguments);
        this.store.voipConfig = voipConfig;
    },
});
