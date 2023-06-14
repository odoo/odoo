/** @odoo-module */

import { Messaging } from "@mail/core/common/messaging_service";

import { patch } from "web.utils";

patch(Messaging.prototype, "hr", {
    setup(env, services) {
        this._super(...arguments);
        services["mail.store"].employees = {};
    },
});
