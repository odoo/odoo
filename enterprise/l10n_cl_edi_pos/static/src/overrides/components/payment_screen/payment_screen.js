import { PaymentScreen } from "@point_of_sale/app/screens/payment_screen/payment_screen";
import { TextInputPopup } from "@point_of_sale/app/utils/input_popups/text_input_popup";
import { AlertDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { makeAwaitable } from "@point_of_sale/app/store/make_awaitable_dialog";
import { patch } from "@web/core/utils/patch";
import { _t } from "@web/core/l10n/translation";

patch(PaymentScreen.prototype, {
    toggleIsToInvoice() {
        if (this.pos.isChileanCompany()) {
            if (this.currentOrder.invoice_type == "boleta") {
                this.currentOrder.invoice_type = "factura";
            } else {
                this.currentOrder.invoice_type = "boleta";
            }
            this.render(true);
        } else {
            super.toggleIsToInvoice(...arguments);
        }
    },
    highlightInvoiceButton() {
        if (this.pos.isChileanCompany()) {
            return this.currentOrder.isFactura();
        }
        return this.currentOrder.is_to_invoice();
    },
    async _isOrderValid(isForceValidate) {
        const result = await super._isOrderValid(...arguments);
        if (this.pos.isChileanCompany()) {
            if (!result) {
                return false;
            }
            if (
                this.currentOrder._isRefundOrder() &&
                this.currentOrder.get_partner().id === this.pos.session._consumidor_final_anonimo_id
            ) {
                this.dialog.add(AlertDialog, {
                    title: _t("Refund not possible"),
                    body: _t("You cannot refund orders for the Consumidor Final Anònimo."),
                });
                return false;
            }
            const mandatoryFacturaFields = [
                "l10n_cl_dte_email",
                "l10n_cl_activity_description",
                "street",
                "l10n_latam_identification_type_id",
                "l10n_cl_sii_taxpayer_type",
                "vat",
            ];
            const missingFields = [];
            const partner = this.currentOrder.get_partner();
            if (this.currentOrder.invoice_type == "factura" || this.currentOrder._isRefundOrder()) {
                for (const field of mandatoryFacturaFields) {
                    if (!partner[field]) {
                        missingFields.push(field);
                    }
                }
            }
            if (missingFields.length > 0) {
                this.notification.add(
                    _t("Please fill out missing fields to proceed: " + missingFields.join(", "))
                );
                this.pos.editPartner(partner);
                return false;
            }
            return true;
        }
        return result;
    },
    async validateOrder(isForceValidate) {
        if (
            this.pos.isChileanCompany() &&
            this.paymentLines.some((line) => line.payment_method_id.is_card_payment)
        ) {
            const voucherNumber = await makeAwaitable(this.dialog, TextInputPopup, {
                rows: 4,
                title: _t("Please register the voucher number"),
            });
            if (!voucherNumber) {
                return;
            }
            this.currentOrder.voucher_number = voucherNumber;
        }
        await super.validateOrder(...arguments);
    },
    shouldDownloadInvoice() {
        return this.pos.isChileanCompany()
            ? this.currentOrder.isFactura()
            : super.shouldDownloadInvoice();
    },
});
