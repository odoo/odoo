/** @odoo-module **/

import { Order } from "@point_of_sale/app/store/models";
import { patch } from "@web/core/utils/patch";
import { PosStore } from "@point_of_sale/app/store/pos_store";

patch(Order.prototype, {
    async pay() {
        const orderLines = this.get_orderlines();
        const has_origin_order = orderLines.some((line) => line.sale_order_origin_id);
        const has_intracom_taxes = orderLines.some((line) =>
            line.tax_ids?.some((tax) => this.pos.intracom_tax_ids?.includes(tax.id))
        );
        if (
            this.pos.company.country_id &&
            this.pos.company.country_id.code === "BE" &&
            has_origin_order &&
            has_intracom_taxes
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
