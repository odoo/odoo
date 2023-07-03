/** @odoo-module */

import { Chrome } from "@point_of_sale/app/pos_app";
import { patch } from "@web/core/utils/patch";

patch(Chrome.prototype, "pos_hr.Chrome", {
    get showCashMoveButton() {
        const { cashier } = this.pos;
        return this._super(...arguments) && (!cashier || cashier.role == "manager");
    },
});
