/* @odoo-module */

import { Record } from "@mail/core/common/record";
import { Activity } from "@mail/core/web/activity_model";

import { patch } from "@web/core/utils/patch";

patch(Activity, {
    /** @override */
    _insert(data) {
        const activity = super._insert(...arguments);
        if (Object.hasOwn(data, "partner")) {
            activity.partner = data.partner;
        }
        return activity;
    },
});

patch(Activity.prototype, {
    /** @override */
    setup() {
        super.setup();
        this.partner = Record.one("Persona");
    },
});
