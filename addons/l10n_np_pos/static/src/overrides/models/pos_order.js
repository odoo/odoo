/** @odoo-module */

import { PosOrder } from "@point_of_sale/app/models/pos_order";
import { patch } from "@web/core/utils/patch";

patch(PosOrder.prototype, {
    setup() {
        super.setup(...arguments);
        if (this.company.account_fiscal_country_id?.code === "NP") {
            this.partner_id = this.partner_id || this.config.l10n_np_default_customer;
        }
    },
});
