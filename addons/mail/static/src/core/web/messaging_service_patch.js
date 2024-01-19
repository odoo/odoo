/* @odoo-module */

import { Messaging } from "@mail/core/common/messaging_service";

import { patch } from "@web/core/utils/patch";

patch(Messaging.prototype, {
    get initMessagingParams() {
        return {
            ...super.initMessagingParams,
            failures: true,
        };
    },
});
