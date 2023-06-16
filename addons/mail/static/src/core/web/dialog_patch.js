/* @odoo-module */

import { Dialog } from "@web/core/dialog/dialog";
import { patch } from "@web/core/utils/patch";

patch(Dialog.prototype, "mail/views/web", {
    /**
     * @override
     */
    onEscape() {
        if (this.data.model === "mail.compose.message") {
            return;
        }
        this._super();
    },
});
