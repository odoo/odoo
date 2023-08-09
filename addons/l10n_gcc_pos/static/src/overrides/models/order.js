/** @odoo-module */

import { patch } from "@web/core/utils/patch";
import { Order } from "@point_of_sale/app/store/models";

patch(Order.prototype, {
    export_for_printing() {
        const result = super.export_for_printing(...arguments);
        const country = this.pos.company.country;
        result.is_gcc_country = country
            ? ["SA", "AE", "BH", "OM", "QA", "KW"].includes(country && country.code)
            : false;
        return result;
    },
});
