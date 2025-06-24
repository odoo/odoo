import { patch } from "@web/core/utils/patch";
import { PaymentScreen } from "@point_of_sale/app/screens/payment_screen/payment_screen";

patch(PaymentScreen.prototype, {
    shouldDownloadInvoice() {
        return this.pos.config.is_spanish
            ? !this.currentOrder.is_l10n_es_simplified_invoice
            : super.shouldDownloadInvoice();
    },
    async _postPushOrderResolve(order, order_server_ids) {
        if (this.pos.config.is_spanish) {
            const invoiceName = await this.pos.data.call("pos.order", "get_invoice_name", [
                order_server_ids,
            ]);
            order.invoice_name = invoiceName;
        }
        return super._postPushOrderResolve(...arguments);
    },
});
