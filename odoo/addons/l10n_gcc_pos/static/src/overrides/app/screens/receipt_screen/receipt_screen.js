/** @odoo-module */

import { Order, Orderline } from "@point_of_sale/app/store/models";
import { patch } from "@web/core/utils/patch";

patch(Order.prototype, {
    export_for_printing() {
        return {
            ...super.export_for_printing(),
            is_gcc_country: ["SA", "AE", "BH", "OM", "QA", "KW"].includes(
                this.pos.company.country?.code
            ),
        };
    },
});

patch(Orderline.prototype, {
    getDisplayData() {
        return {
            ...super.getDisplayData(),
            tax: this.env.utils.formatCurrency(this.get_tax(), false),
        };
    },
});
