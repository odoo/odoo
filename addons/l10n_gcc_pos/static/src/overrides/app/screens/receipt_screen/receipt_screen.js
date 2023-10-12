/** @odoo-module */

import { Order } from "@point_of_sale/app/store/models";
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
