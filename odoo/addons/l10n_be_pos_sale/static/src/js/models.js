/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { Order } from "@point_of_sale/app/store/models";
import { PosStore } from "@point_of_sale/app/store/pos_store";

patch(Order.prototype, {
    async pay() {
        const orderLines = this.get_orderlines();
        const has_origin_order = orderLines.some((line) => line.sale_order_origin_id);
        const has_intracom_taxes = orderLines.some(
            (line) =>
                line.tax_ids &&
                this.pos.intracom_tax_ids &&
                line.tax_ids.some((tax) => this.pos.intracom_tax_ids.includes(tax))
        );
        if (
            this.pos.company.country &&
            this.pos.company.country.code === "BE" &&
            has_origin_order &&
            has_intracom_taxes
        ) {
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
