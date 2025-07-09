import { OrderReceipt } from "@point_of_sale/app/screens/receipt_screen/receipt/order_receipt";
import { patch } from "@web/core/utils/patch";

patch(OrderReceipt.prototype, {
    _getAdditionalLineInfo(line) {
        const info = super._getAdditionalLineInfo(line);
        if (line.sale_order_origin_id?.name) {
            info.push({
                class: "sale-order-name",
                value: line.sale_order_origin_id?.name,
                iclass: "fa-shopping-basket",
            });
        }
        return info;
    },
});
