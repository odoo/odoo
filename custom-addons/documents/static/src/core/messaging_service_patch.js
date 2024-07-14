/** @odoo-module */

import { Messaging } from "@mail/core/common/messaging_service";

import { patch } from "@web/core/utils/patch";

patch(Messaging.prototype, {
    initMessagingCallback(...args) {
        super.initMessagingCallback(...args);
        if (args[0].hasDocumentsUserGroup) {
            this.store.hasDocumentsUserGroup = true;
        }
    },
});
