import OrderPaymentValidation from "@point_of_sale/app/utils/order_payment_validation";
import { patch } from "@web/core/utils/patch";

patch(OrderPaymentValidation.prototype, {
    async afterOrderValidation() {
        if (this.pos.config._l10n_es_pos_fiscal_mode === "tbai") {
            const url = await this.pos.data.call("pos.order", "get_l10n_es_pos_tbai_qrurl", [
                this.order.id,
            ]);
            this.order.uiState.l10n_es_pos_tbai_qrurl = url || undefined;
        }
        return super.afterOrderValidation(...arguments);
    },
});
