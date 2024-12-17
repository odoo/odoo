import { EcpayConfirmPopup } from "@l10n_tw_edi_ecpay_pos/js/ecpay_confirm_popup";
import { EcpayInfoPopup } from "@l10n_tw_edi_ecpay_pos/js/ecpay_info_popup";
import { PaymentScreen } from "@point_of_sale/app/screens/payment_screen/payment_screen";
import { makeAwaitable } from "@point_of_sale/app/store/make_awaitable_dialog";
import { patch } from "@web/core/utils/patch";

patch(PaymentScreen.prototype, {
    setup() {
        super.setup(...arguments);
        if (
            this.pos.company.country_id?.code === "TW" &&
            this.pos.config.is_ecpay_enabled &&
            this.currentOrder.get_partner()
        ) {
            this.currentOrder.set_to_invoice(true);
            this.currentOrder.set_invoice_info(true, false, false, false, false);
        }
    },

    // @override
    async toggleIsToInvoice() {
        if (
            this.pos.company.country_id?.code === "TW" &&
            this.pos.config.is_ecpay_enabled &&
            this.currentOrder.get_partner() &&
            !this.currentOrder.is_to_invoice() &&
            !this.currentOrder.get_orderlines().some((line) => line.refunded_orderline_id) &&
            !this.currentOrder.l10n_tw_edi_is_b2b
        ) {
            const confirm = await makeAwaitable(this.dialog, EcpayConfirmPopup, {
                order: this.currentOrder,
            });

            if (!confirm) {
                this.currentOrder.set_to_invoice(false);
                this.currentOrder.set_invoice_info(false, false, false, false, false);
                return;
            }

            if (confirm.confirm === 0) {
                this.currentOrder.set_invoice_info(true, false, false, false, false);
            } else {
                const payload = await makeAwaitable(this.dialog, EcpayInfoPopup, {
                    order: this.currentOrder,
                });

                if (!payload) {
                    this.currentOrder.set_to_invoice(false);
                    this.currentOrder.set_invoice_info(false, false, false, false, false);
                    return;
                }

                this.currentOrder.set_invoice_info(
                    false,
                    "loveCode" in payload.data ? payload.data.loveCode : false,
                    "carrierType" in payload.data && payload.data.carrierType !== "0"
                        ? payload.data.carrierType
                        : false,
                    "carrierNumber" in payload.data ? payload.data.carrierNumber : false,
                    "carrierNumber2" in payload.data ? payload.data.carrierNumber2 : false
                );
            }
        }
        super.toggleIsToInvoice(...arguments);
    },
});
