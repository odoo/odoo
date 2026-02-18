/** @odoo-module */

import { _t } from "@web/core/l10n/translation";
import { patch } from "@web/core/utils/patch";
import { AlertDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { PaymentScreen } from "@point_of_sale/app/screens/payment_screen/payment_screen";
import { makeAwaitable } from "@point_of_sale/app/store/make_awaitable_dialog";
import { TextInputPopup } from "@point_of_sale/app/utils/input_popups/text_input_popup";

patch(PaymentScreen.prototype, {
    async toggleIsToInvoice() {
        if (
            this.pos.isVietnamCompany() &&
            this.pos.config.l10n_vn_auto_send_to_sinvoice &&
            !this.currentOrder.is_to_invoice() &&
            this.currentOrder.lines.some((line) => line.refunded_orderline_id) // Refund Order
        ) {
            const reason = await makeAwaitable(this.dialog, TextInputPopup, {
                rows: 4,
                title: _t("Refund Reason"),
            });
            if (reason) {
                this.currentOrder.credit_note_reason = reason;
            }
        }
        super.toggleIsToInvoice(...arguments);
    },
    async _isOrderValid(isForceValidate) {
        const result = await super._isOrderValid(...arguments);
        if (!this.pos.isVietnamCompany() || !this.currentOrder.is_to_invoice()) {
            return result;
        }
        if (
            this.pos.config.l10n_vn_auto_send_to_sinvoice &&
            !this.pos.config._is_vn_edi_pos_applicable
        ) {
            this.dialog.add(AlertDialog, {
                title: _t("Configuration Error"),
                body: _t("Set a POS Symbol or disable 'Auto-send to SInvoice.'"),
            });
            return false;
        }
        return result;
    },
    async _finalizeValidation() {
        await super._finalizeValidation(...arguments);
        if (
            this.pos.isVietnamCompany() &&
            this.pos.config.l10n_vn_auto_send_to_sinvoice &&
            this.currentOrder.is_to_invoice() &&
            this.currentOrder.l10n_vn_sinvoice_state != "sent" &&
            (!this.pos.data.network.warningTriggered || !navigator.onLine)
        ) {
            this.dialog.add(AlertDialog, {
                title: _t("SInvoice Error"),
                body: _t(
                    "SInvoice transmission failed. Please check the backend for details and retry."
                ),
            });
        }
    },
    shouldDownloadInvoice() {
        if (
            this.pos.isVietnamCompany() &&
            this.pos.config.l10n_vn_auto_send_to_sinvoice &&
            !this.currentOrder.l10n_vn_has_sinvoice_pdf
        ) {
            // Skip download if sinvoice pdf is not available
            return;
        } else {
            return super.shouldDownloadInvoice(...arguments);
        }
    },
});
