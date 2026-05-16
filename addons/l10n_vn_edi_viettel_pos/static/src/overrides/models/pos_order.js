/** @odoo-module */

import { PosOrder } from "@point_of_sale/app/models/pos_order";
import { patch } from "@web/core/utils/patch";

patch(PosOrder.prototype, {
    setup(vals) {
        super.setup(...arguments);
        if (this.company.account_fiscal_country_id?.code === "VN") {
            // Set to_invoice to true by default except for return order
            if (!this.lines.some((line) => line.refunded_orderline_id)) {
                this.to_invoice = vals.to_invoice !== false;
            }

            const defaultPartner = this.models["res.partner"].get(
                this.session._default_customer_id
            );
            this.partner_id = this.partner_id || defaultPartner;
        }
    },
});
