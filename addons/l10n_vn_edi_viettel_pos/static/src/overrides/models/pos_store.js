/** @odoo-module */

import { PosStore } from "@point_of_sale/app/services/pos_store";
import { patch } from "@web/core/utils/patch";

patch(PosStore.prototype, {
    isVietnamCompany() {
        return this.company.account_fiscal_country_id?.code === "VN";
    },
});
