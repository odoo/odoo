/* @odoo-module */

import { Thread } from "@mail/core/common/thread";
import { patch } from "@web/core/utils/patch";
import { outOfOfficeText } from "./persona_service_patch";

patch(Thread.prototype, "hr_holidays", {
    setup() {
        this._super();
        this.outOfOfficeText = outOfOfficeText;
    },
});
