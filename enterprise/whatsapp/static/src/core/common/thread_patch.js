/** @odoo-module */

import { Thread } from "@mail/core/common/thread";
import { patch } from "@web/core/utils/patch";

patch(Thread.prototype, {
    isSquashed(msg, prevMsg) {
        if (msg.whatsappStatus === "error") {
            return false;
        }
        return super.isSquashed(msg, prevMsg);
    },
});
