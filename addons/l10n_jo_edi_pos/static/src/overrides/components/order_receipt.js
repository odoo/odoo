import { OrderReceipt } from "@point_of_sale/app/screens/receipt_screen/receipt/order_receipt";
import { qrCodeSrc } from "@point_of_sale/utils";
import { patch } from "@web/core/utils/patch";

patch(OrderReceipt.prototype, {
    get qrCode() {
        if (this.order.l10n_jo_edi_pos_qr) {
            return qrCodeSrc(this.order.l10n_jo_edi_pos_qr);
        }
        return super.qrCode;
    }
});
