/** @odoo-module */

import { patch } from "@web/core/utils/patch";
import { PosStore } from "@point_of_sale/app/store/pos_store";

const EXCLUDE_IF_NOT_REGISTERED = ["AE", "SA"];
const GCC_COUNTRIES = ["SA", "AE", "BH", "OM", "QA", "KW"];

patch(PosStore.prototype, {
    getReceiptHeaderData(order) {
        const country = this.company.country?.code;
        const useGCCReport =
            GCC_COUNTRIES.includes(country) &&
            (this.company.vat || !EXCLUDE_IF_NOT_REGISTERED.includes(country));
        return {
            ...super.getReceiptHeaderData(...arguments),
            useGCCReport,
        };
    },
});
