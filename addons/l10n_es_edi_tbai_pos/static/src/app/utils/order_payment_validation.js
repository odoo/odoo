import OrderPaymentValidation from "@point_of_sale/app/utils/order_payment_validation";
import { patch } from "@web/core/utils/patch";
import { qrCodeSrc } from "@point_of_sale/utils";

patch(OrderPaymentValidation.prototype, {
    async beforePostPushOrderResolve(order, order_server_ids) {
        if (this.pos.company.l10n_es_tbai_is_enabled) {
            const l10n_es_pos_tbai_qrurl = await this.pos.data.call(
                "pos.order",
                "get_l10n_es_pos_tbai_qrurl",
                [order.id]
            );
            order.l10n_es_pos_tbai_qrsrc = l10n_es_pos_tbai_qrurl
                ? qrCodeSrc(l10n_es_pos_tbai_qrurl)
                : undefined;
        }
        return super.beforePostPushOrderResolve(...arguments);
    },
});
