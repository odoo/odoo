/** @odoo-module */

import { _t } from "@web/core/l10n/translation";
import { AlertDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { patch } from "@web/core/utils/patch";
import { PaymentScreen } from "@point_of_sale/app/screens/payment_screen/payment_screen";

patch(PaymentScreen.prototype, {
    onMounted() {
        super.onMounted();
        if (this.pos.isPortugueseCompany() && this.currentOrder) {
            this.currentOrder.setToInvoice(true);
        }
    },

    async toggleIsToInvoice() {
        if (this.pos.isPortugueseCompany()) {
            if (this.currentOrder.isToInvoice()) {
                this.dialog.add(AlertDialog, {
                    title: _t("Invoice Required"),
                    body: _t(
                        "Invoicing is mandatory for Portuguese fiscal compliance. The invoice cannot be unchecked."
                    ),
                });
                return;
            }
            this.currentOrder.setToInvoice(true);
            return;
        }
        return super.toggleIsToInvoice(...arguments);
    },
});
