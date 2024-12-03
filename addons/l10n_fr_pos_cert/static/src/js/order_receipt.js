import { OrderReceipt } from "@point_of_sale/app/screens/receipt_screen/receipt/order_receipt";
import { patch } from "@web/core/utils/patch";

patch(OrderReceipt.prototype, {
    get qrCode() {
        if (this.order.is_french_country()) {
            return false;
        }
        return super.qrCode;
    },
});
