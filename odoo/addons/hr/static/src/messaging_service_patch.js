/** @odoo-module */

import { Messaging } from "@mail/core/common/messaging_service";

import { patch } from "@web/core/utils/patch";

patch(Messaging.prototype, {
    setup(...args) {
        super.setup(...args);
        this.store.employees = {};
    },
});
