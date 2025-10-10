import { ask, makeAwaitable } from "@point_of_sale/app/store/make_awaitable_dialog";
import { EcpayInfoPopup } from "@l10n_tw_edi_ecpay_pos/js/ecpay_info_popup";
import { PaymentScreen } from "@point_of_sale/app/screens/payment_screen/payment_screen";
import { _t } from "@web/core/l10n/translation";
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
            let dismiss = false;
            const confirm = await ask(this.dialog, {
                title: _t("Ecpay Invoicing Confirmation"),
                body: _t("Store in Carrier or Donate?"),
                confirmLabel: _t("Yes"),
                cancelLabel: _t("No"),
                dismiss: () => {
                    dismiss = true;
                },
            });

            if (dismiss) {
                this.currentOrder.set_to_invoice(false);
                this.currentOrder.set_invoice_info(false, false, false, false, false);
                return;
            }

            if (confirm) {
                const payload = await makeAwaitable(this.dialog, EcpayInfoPopup);

                if (!payload) {
                    this.currentOrder.set_to_invoice(false);
                    this.currentOrder.set_invoice_info(false, false, false, false, false);
                    return;
                }

                this.currentOrder.set_invoice_info(
                    false,
                    "loveCode" in payload ? payload.loveCode : false,
                    "carrierType" in payload && payload.carrierType !== "0"
                        ? payload.carrierType
                        : false,
                    "carrierNumber" in payload ? payload.carrierNumber : false,
                    "carrierNumber2" in payload ? payload.carrierNumber2 : false
                );
            } else {
                this.currentOrder.set_invoice_info(true, false, false, false, false);
            }
        }
        super.toggleIsToInvoice(...arguments);
    },
});
