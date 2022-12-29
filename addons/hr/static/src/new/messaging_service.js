/** @odoo-module */

import { Messaging } from "@mail/new/core/messaging_service";

import { patch } from "web.utils";

patch(Messaging.prototype, "hr", {
    setup(...args) {
        this._super(...args);
        this.store.employees = {};
    },
});
