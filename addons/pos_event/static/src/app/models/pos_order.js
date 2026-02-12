// Part of Odoo. See LICENSE file for full copyright and licensing details.
import { PosOrder } from "@point_of_sale/app/models/pos_order";
import { patch } from "@web/core/utils/patch";

patch(PosOrder.prototype, {
    get eventRegistrations() {
        return this.lines.flatMap((line) => line.event_registration_ids);
    },
    setLinePrice(line, pricelist) {
        if (line.event_ticket_id) {
            if (
                pricelist.item_ids.some(
                    (item) =>
                        item.product_id == line.product_id ||
                        item.product_tmpl_id == line.product_id.product_tmpl_id
                )
            ) {
                super.setLinePrice(line, pricelist);
                return;
            }
            line.setUnitPrice(line.event_ticket_id.price);
        } else {
            super.setLinePrice(line, pricelist);
        }
    },
});
