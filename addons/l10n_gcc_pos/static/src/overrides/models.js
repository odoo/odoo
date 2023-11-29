/** @odoo-module */

import { patch } from "@web/core/utils/patch";
import { PosStore } from "@point_of_sale/app/store/pos_store";

patch(PosStore.prototype, {
    getReceiptHeaderData() {
        return {
            ...super.getReceiptHeaderData(),
            is_gcc_country: ["SA", "AE", "BH", "OM", "QA", "KW"].includes(
                this.company.country?.code
            ),
        };
    },
});
