/* @odoo-module */

import { Thread } from "@mail/core_ui/thread";
import { useState } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { patch } from "@web/core/utils/patch";

patch(Thread.prototype, "discuss/message_pin", {
    setup() {
        this._super();
        this.ui = useState(useService("ui"));
    },
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
