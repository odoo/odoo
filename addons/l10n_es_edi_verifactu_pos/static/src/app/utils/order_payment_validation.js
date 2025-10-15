import OrderPaymentValidation from "@point_of_sale/app/utils/order_payment_validation";
import { patch } from "@web/core/utils/patch";

patch(OrderPaymentValidation.prototype, {
    async beforePostPushOrderResolve(order, order_server_ids) {
        const invoiceName = await this.pos.data.call(
            "pos.order",
            "l10n_es_edi_verifactu_get_invoice_name",
            [order_server_ids]
        );
        order.invoice_name = invoiceName;

        return super.beforePostPushOrderResolve(...arguments);
    },
});
