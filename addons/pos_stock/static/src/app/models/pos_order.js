import { PosOrder } from "@point_of_sale/app/models/pos_order";
import { patch } from "@web/core/utils/patch";

patch(PosOrder.prototype, {
    setup(vals) {
        super.setup(vals);
        this.shipping_date = vals.shipping_date;
    },

    get pickingType() {
        return this.models["stock.picking.type"].getFirst();
    },

    getPrice(pricelist) {
        this.pricelist_id = pricelist ? pricelist : false;

        const lines_to_recompute = this.getLinesToCompute();

        for (const line of lines_to_recompute) {
            if (line.isLotTracked()) {
                const related_lines = [];
                const price = line.product_id.product_tmpl_id.getPrice(
                    pricelist,
                    line.getQuantity(),
                    line.getPriceExtra(),
                    false,
                    line.product_id,
                    line,
                    related_lines
                );
                related_lines.forEach((line) => line.setUnitPrice(price));
            } else {
                const newPrice = line.product_id.product_tmpl_id.getPrice(
                    pricelist,
                    line.getQuantity(),
                    line.getPriceExtra(),
                    false,
                    line.product_id
                );
                line.setUnitPrice(newPrice);
            }
        }
    },
});
