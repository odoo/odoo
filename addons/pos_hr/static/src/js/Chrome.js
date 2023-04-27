/** @odoo-module */

import { Chrome } from "@point_of_sale/js/Chrome";
import { patch } from "@web/core/utils/patch";

patch(Chrome.prototype, "pos_hr.Chrome", {
    get showCashMoveButton() {
        return (
            this._super(...arguments) &&
            (!this.env.pos.cashier || this.env.pos.cashier.role == "manager")
        );
    },
});
