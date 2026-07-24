/** @odoo-module */

import { Order, Orderline } from "@point_of_sale/app/store/models";
import { patch } from "@web/core/utils/patch";

const EXCLUDE_IF_NOT_REGISTERED = ["AE", "SA"];
const GCC_COUNTRIES = ["SA", "AE", "BH", "OM", "QA", "KW"];

patch(Order.prototype, {
    export_for_printing() {
        const country = this.pos.company.country?.code;
        const useGCCReport =
            GCC_COUNTRIES.includes(country) &&
            (this.pos.company.vat || !EXCLUDE_IF_NOT_REGISTERED.includes(country));
        return {
            ...super.export_for_printing(),
            useGCCReport,
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
