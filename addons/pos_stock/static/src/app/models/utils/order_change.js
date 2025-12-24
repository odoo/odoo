import { LineDetailsGetter } from "@point_of_sale/app/models/utils/order_change";
import { patch } from "@web/core/utils/patch";
import { _t } from "@web/core/l10n/translation";

patch(LineDetailsGetter, {
    getLineDetails(order, orderline, quantityDiff) {
        const result = super.getLineDetails(order, orderline, quantityDiff);
        const trackingStr = orderline.product_id?.tracking == "lot" ? _t("Lot:") : _t("SN:");
        result["pack_lot_lines"] = orderline.pack_lot_ids?.map(
            (l) => `${trackingStr} ${l.lot_name}`
        );
        return result;
    },
});
