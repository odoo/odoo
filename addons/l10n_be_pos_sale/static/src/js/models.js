/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { Order } from "@point_of_sale/app/store/models";
import { PosStore } from "@point_of_sale/app/store/pos_store";

patch(Order.prototype, {
    async pay() {
        const has_origin_order = this.get_orderlines().some(line => line.sale_order_origin_id);
        if (this.pos.company.country && this.pos.company.country.code === "BE" && has_origin_order) {
            this.to_invoice = true;
        }
        return super.pay(...arguments);
    }
});

patch(PosStore.prototype, {
    async _processData(loadedData) {
        await super._processData(...arguments);
        if (this.company.country?.code == "BE") {
            this.intracom_tax_ids = loadedData["intracom_tax_ids"];
        }
    },
});
