import { PosOrderline } from "@point_of_sale/app/models/pos_order_line";
import { patch } from "@web/core/utils/patch";

patch(PosOrderline.prototype, {
    isFbrServiceFeeLine() {
        const feeProduct = this.config.l10n_pk_edi_pos_service_fee_product_id;
        return Boolean(feeProduct) && this.product_id?.id === feeProduct.id;
    },

    isServiceFeeApplicable() {
        return super.isServiceFeeApplicable(...arguments) && !this.isFbrServiceFeeLine();
    },
});
