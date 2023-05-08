/** @odoo-module */

import { OrderReceipt } from "@point_of_sale/js/Screens/ReceiptScreen/OrderReceipt";
import { patch } from "@web/core/utils/patch";

patch(OrderReceipt.prototype, "l10n_fr_pos_cert.OrderReceipt", {
    showOldPrice(receipt, orderline) {
        const oldPrice = orderline.price_lst;
        const currentPrice = orderline.price_with_tax;
        return (
            !orderline.down_payment_details &&
            orderline.price_changed &&
            orderline.price_with_tax > 0 && // we don't want to display old_price for refunds.
            receipt.l10n_fr_hash &&
            oldPrice !== currentPrice
        );
    },
});
