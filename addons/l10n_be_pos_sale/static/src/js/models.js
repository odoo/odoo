/** @odoo-module **/

import { Order } from "@point_of_sale/js/models";
import { patch } from "@web/core/utils/patch";

patch(Order.prototype, "l10n_be_pos_sale.order", {
    async pay() {
        const has_origin_order = this.get_orderlines().some(line => line.sale_order_origin_id);
        if (this.pos.company.country && this.pos.company.country.code === "BE" && has_origin_order) {
            this.to_invoice = true;
        }
        return super.pay(...arguments);
    }
});
