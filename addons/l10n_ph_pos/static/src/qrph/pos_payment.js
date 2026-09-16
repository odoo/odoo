import { PosPayment } from "@point_of_sale/app/models/pos_payment";
import { patch } from "@web/core/utils/patch";

patch(PosPayment.prototype, {
    getQrPopupProps() {
        // Pass the ids only: these props are serialized for the customer display, which cannot
        // carry the circular references the records hold.
        const base = super.getQrPopupProps();
        return {
            ...base,
            paymentMethod: { ...(base.paymentMethod || {}), id: this.payment_method_id.id },
            order: { ...(base.order || {}), uuid: this.pos_order_id.uuid },
        };
    },
});
