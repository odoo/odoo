/* @odoo-module */

import { Thread } from "@mail/core_ui/thread";
import { patch } from "@web/core/utils/patch";

patch(Thread.prototype, "discuss/message_pin", {
    /**
     * @override
     * @param {MouseEvent} ev
     */
    async onClickNotification(ev) {
        const { oeType } = ev.target.dataset;
        if (oeType === "pin-menu") {
            this.env.pinMenu?.open();
        }
    },
});
