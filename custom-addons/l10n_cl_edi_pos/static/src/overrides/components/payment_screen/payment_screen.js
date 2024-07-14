/** @odoo-module */

import { PaymentScreen } from "@point_of_sale/app/screens/payment_screen/payment_screen";
import { TextAreaPopup } from "@point_of_sale/app/utils/input_popups/textarea_popup";
import { ErrorPopup } from "@point_of_sale/app/errors/popups/error_popup";
import { patch } from "@web/core/utils/patch";
import { _t } from "@web/core/l10n/translation";

patch(PaymentScreen.prototype, {
    toggleIsToInvoice() {
        if (this.pos.isChileanCompany()) {
            if (this.currentOrder.invoiceType == "boleta") {
                this.currentOrder.invoiceType = "factura";
            } else {
                this.currentOrder.invoiceType = "boleta";
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
                this.currentOrder.get_partner().id === this.pos.consumidorFinalAnonimoId
            ) {
                this.popup.add(ErrorPopup, {
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
            if (this.currentOrder.invoiceType == "factura" || this.currentOrder._isRefundOrder()) {
                for (const field of mandatoryFacturaFields) {
                    if (!partner[field]) {
                        missingFields.push(field);
                    }
                }
            }
            if (missingFields.length > 0) {
                this.notification.add(_t("Please fill out missing fields to proceed.", 5000));
                this.selectPartner(true, missingFields);
                return false;
            }
            return true;
        }
        return result;
    },
    async validateOrder(isForceValidate) {
        if (
            this.pos.isChileanCompany() &&
            this.paymentLines.some((line) => line.payment_method.is_card_payment)
        ) {
            const { confirmed, payload } = await this.popup.add(TextAreaPopup, {
                confirmText: _t("Confirm"),
                cancelText: _t("Cancel"),
                title: _t("Please register the voucher number"),
            });

            if (!confirmed) {
                return;
            }
            this.currentOrder.voucherNumber = payload;
        }
        await super.validateOrder(...arguments);
    },
    shouldDownloadInvoice() {
        return this.pos.isChileanCompany()
            ? this.pos.selectedOrder.isFactura()
            : super.shouldDownloadInvoice();
    },
    async _postPushOrderResolve(order, order_server_ids) {
        const result = await super._postPushOrderResolve(...arguments);
        if (this.pos.isChileanCompany()) {
            const result = await this.orm.call(
                "pos.order",
                "get_cl_pos_info",
                [order_server_ids],
                {}
            );
            order.l10n_latam_document_type = result[0].l10n_latam_document_type;
            order.l10n_latam_document_number = result[0].l10n_latam_document_number;
            order.l10n_cl_sii_barcode = result[0].l10n_cl_sii_barcode;
            order.l10n_cl_sii_regional_office = result[0].l10n_cl_sii_regional_office;
        }
        return result;
    },
});
