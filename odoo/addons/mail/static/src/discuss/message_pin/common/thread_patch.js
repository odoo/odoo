/* @odoo-module */

import { Thread } from "@mail/core/common/thread";

import { patch } from "@web/core/utils/patch";

patch(Thread.prototype, {
    /**
     * @override
     * @param {MouseEvent} ev
     */
    async onClickNotification(ev) {
        const { oeType } = ev.target.dataset;
        if (oeType === "pin-menu") {
            this.env.pinMenu?.open();
        }
        await super.onClickNotification(...arguments);
    },
});
