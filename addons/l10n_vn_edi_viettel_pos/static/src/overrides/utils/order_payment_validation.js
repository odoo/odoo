/** @odoo-module */

import { _t } from "@web/core/l10n/translation";
import { patch } from "@web/core/utils/patch";
import { AlertDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import OrderPaymentValidation from "@point_of_sale/app/utils/order_payment_validation";

patch(OrderPaymentValidation.prototype, {
    async isOrderValid(isForceValidate) {
        const result = await super.isOrderValid(...arguments);
        if (!this.pos.isVietnamCompany() || !this.order.to_invoice) {
            return result;
        }
        if (
            this.pos.config.l10n_vn_auto_send_to_sinvoice &&
            !this.pos.config._is_vn_edi_pos_applicable
        ) {
            this.pos.dialog.add(AlertDialog, {
                title: _t("Configuration Error"),
                body: _t("Set a POS Symbol or disable 'Auto-send to SInvoice.'"),
            });
            return false;
        }
        return result;
    },
    async finalizeValidation() {
        const result = await super.finalizeValidation(...arguments);
        if (
            this.pos.isVietnamCompany() &&
            this.pos.config.l10n_vn_auto_send_to_sinvoice &&
            this.order.to_invoice &&
            this.order.l10n_vn_sinvoice_state === "ready_to_send" &&
            (!this.pos.data.network.warningTriggered || !navigator.onLine)
        ) {
            this.pos.dialog.add(AlertDialog, {
                title: _t("SInvoice Error"),
                body: _t(
                    "SInvoice transmission failed. Please check the backend for details and retry."
                ),
            });
        }
        return result;
    },
    shouldDownloadInvoice() {
        if (
            this.pos.isVietnamCompany() &&
            this.pos.config.l10n_vn_auto_send_to_sinvoice &&
            !this.order.l10n_vn_has_sinvoice_pdf
        ) {
            return false;
        }
        return super.shouldDownloadInvoice(...arguments);
    },
});
