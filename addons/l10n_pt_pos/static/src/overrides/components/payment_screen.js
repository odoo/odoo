/** @odoo-module */

import { _t } from "@web/core/l10n/translation";
import { AlertDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { patch } from "@web/core/utils/patch";
import { PaymentScreen } from "@point_of_sale/app/screens/payment_screen/payment_screen";

patch(PaymentScreen.prototype, {
    setup() {
        super.setup(...arguments);
        if (this.pos.isPortugueseCompany() && this.currentOrder) {
            this.currentOrder.set_to_invoice(true);
        }
    },

    toggleIsToInvoice() {
        if (this.pos.isPortugueseCompany()) {
            if (this.currentOrder.is_to_invoice()) {
                this.dialog.add(AlertDialog, {
                    title: _t("Invoice Required"),
                    body: _t(
                        "Invoicing is mandatory for Portuguese fiscal compliance. The invoice cannot be unchecked."
                    ),
                });
                return;
            }
            this.currentOrder.set_to_invoice(true);
            return;
        }
        return super.toggleIsToInvoice(...arguments);
    },

    async _isOrderValid(isForceValidate) {
        const isPtNoPartner = this.pos.isPortugueseCompany() && !this.currentOrder.get_partner();
        const origPartner = this.currentOrder.partner_id;
        if (isPtNoPartner) {
            this.currentOrder.partner_id = true;
        }
        const valid = await super._isOrderValid(isForceValidate);
        if (isPtNoPartner) {
            this.currentOrder.partner_id = origPartner;
        }
        return valid;
    },

    shouldDownloadInvoice() {
        if (this.pos.isPortugueseCompany()) {
            return false;
        }
        return super.shouldDownloadInvoice();
    },
});
