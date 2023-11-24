/** @odoo-module */

import { Order } from "@point_of_sale/app/store/models";
import { patch } from "@web/core/utils/patch";

patch(Order.prototype, {
    setup() {
        super.setup(...arguments);
        if (this.pos.isPeruvianCompany() && !this.partner) {
            this.partner = this.pos.models["res.partner"].get(this.pos.consumidorFinalAnonimoId);
        }
    },
});
