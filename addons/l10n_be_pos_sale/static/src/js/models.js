/** @odoo-module **/

import { Order } from "@point_of_sale/app/store/models";
import { patch } from "@web/core/utils/patch";
import { PosStore } from "@point_of_sale/app/store/pos_store";

patch(Order.prototype, {
    async pay() {
        const has_origin_order = this.get_orderlines().some((line) => line.sale_order_origin_id);
        if (
            this.pos.company.country_id &&
            this.pos.company.country_id.code === "BE" &&
            has_origin_order
        ) {
            this.to_invoice = true;
        }
        return super.pay(...arguments);
    },
});

patch(PosStore.prototype, {
    async processServerData(loadedData) {
        await super.processServerData(...arguments);
        if (this.company.country_id?.code == "BE") {
            this.intracom_tax_ids = this.data.custom.intracom_tax_ids;
        }
    },
});
