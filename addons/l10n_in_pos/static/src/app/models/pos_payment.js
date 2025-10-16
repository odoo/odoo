import { PosPayment } from "@point_of_sale/app/models/pos_payment";
import { patch } from "@web/core/utils/patch";

patch(PosPayment.prototype, {
    getQrPopupProps(customerDisplay = false) {
        // Extract only required fields to prevent circular references when serializing data from CustomerDisplayPosAdapter.dispatch()
        const { upi_identifier = "", _qr_payment_icon_urls = [] } = this.payment_method_id || {};
        const base = super.getQrPopupProps(customerDisplay);
        return {
            ...base,
            paymentMethod: {
                ...(base.paymentMethod || {}),
                upi_identifier,
                _qr_payment_icon_urls,
            },
        };
    },
});
