import { EcpayInfoPopup } from "@l10n_tw_edi_ecpay_pos/js/ecpay_info_popup";
import { PaymentScreen } from "@point_of_sale/app/screens/payment_screen/payment_screen";
import { makeAwaitable } from "@point_of_sale/app/store/make_awaitable_dialog";
import { patch } from "@web/core/utils/patch";

patch(PaymentScreen.prototype, {
    setup() {
        super.setup(...arguments);
        if (this.pos.company.country_id?.code === "TW" && this.pos.config.is_ecpay_enabled) {
            this.currentOrder.set_to_invoice(false);
        }
    },

    // @override
    async toggleIsToInvoice() {
        if (
            this.pos.company.country_id?.code === "TW" &&
            !this.currentOrder.is_to_invoice() &&
            !this.currentOrder.get_orderlines().some((line) => line.refunded_orderline_id) &&
            this.pos.config.is_ecpay_enabled
        ) {
            const payload = await makeAwaitable(this.dialog, EcpayInfoPopup, {
                order: this.currentOrder,
            });
            if (payload) {
                this.currentOrder.set_invoice_info(
                    "printFlag" in payload.data ? payload.data.printFlag : false,
                    "loveCode" in payload.data ? payload.data.loveCode : false,
                    "carrierType" in payload.data && payload.data.carrierType !== "0"
                        ? payload.data.carrierType
                        : false,
                    "carrierNumber" in payload.data ? payload.data.carrierNumber : false,
                    payload.data.invoiceType
                );
            } else {
                this.currentOrder.set_to_invoice(!this.currentOrder.is_to_invoice());
            }
        }
        super.toggleIsToInvoice(...arguments);
    },
});
