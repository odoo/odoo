import { PaymentScreen } from "@point_of_sale/app/screens/payment_screen/payment_screen";
import { patch } from "@web/core/utils/patch";

patch(PaymentScreen.prototype, {
    setup() {
        super.setup(...arguments);
        if (
            this.pos.company.account_fiscal_country_id?.code === "TW" &&
            this.pos.config.is_ecpay_enabled &&
            this.currentOrder.getPartner()
        ) {
            this.currentOrder.setToInvoice(true);
            this.currentOrder.setEcpayInvoiceInfo({ l10n_tw_edi_is_print: true });
        }
    },

    // @override
    async toggleIsToInvoice() {
        const order = this.currentOrder;

        const proceed = await order.askAndSetEcpayInvoiceInfo(this.dialog, {
            isFromPaymentScreen: true,
        });

        if (!proceed) {
            order.setToInvoice(false);
            order.setEcpayInvoiceInfo({});
            return;
        }
        super.toggleIsToInvoice(...arguments);
    },
});
