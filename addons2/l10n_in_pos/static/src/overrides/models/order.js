/** @odoo-module */

import { Order } from "@point_of_sale/app/store/models";
import { patch } from "@web/core/utils/patch";

patch(Order.prototype, {
    export_for_printing() {
        const result = super.export_for_printing(...arguments);
        if (this.pos.company.country.code === 'IN') {
            result.tax_details.forEach((tax) => {
                tax.tax.letter = tax.tax.tax_group_id[1]
            })
        }
        if (this.get_partner()) {
            result.partner = this.get_partner();
        }
        return result;
    },
});
