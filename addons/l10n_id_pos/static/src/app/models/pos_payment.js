import { PosPayment } from "@point_of_sale/app/models/pos_payment";
import { patch } from "@web/core/utils/patch";

patch(PosPayment.prototype, {
    getQrPopupProps(customerDisplay = false) {
        // Extract only required fields to prevent circular references when serializing data from CustomerDisplayPosAdapter.dispatch()
        const base = super.getQrPopupProps(customerDisplay);
        return customerDisplay
            ? base
            : {
                  ...base,
                  paymentMethod: {
                      ...(base.paymentMethod || {}),
                      id: this.payment_method_id.id,
                  },
                  order: {
                      ...(base.order || {}),
                      uuid: this.pos_order_id.uuid,
                  },
              };
    },
});
