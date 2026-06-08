import { PosOrder } from "@point_of_sale/app/models/pos_order";
import { patch } from "@web/core/utils/patch";
import { _t } from "@web/core/l10n/translation";

patch(PosOrder.prototype, {
    setup(vals) {
        super.setup(vals);
        this.shipping_date = vals.shipping_date;
    },

    get pickingType() {
        return this.models["stock.picking.type"].getFirst();
    },

    setLinePriceFromPriceList(line, pricelist) {
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
            super.setLinePriceFromPriceList(line, pricelist);
        }
    },

    dataMaker(prepOrPosLine, quantity) {
        const result = super.dataMaker(prepOrPosLine, quantity);
        const trackingStr = prepOrPosLine.product_id?.tracking == "lot" ? _t("Lot:") : _t("SN:");
        result["data"]["pack_lot_lines"] = prepOrPosLine.pack_lot_ids?.map(
            (l) => `${trackingStr} ${l.lot_name}`
        );
        return result;
    },
});
