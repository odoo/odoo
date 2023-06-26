/** @odoo-module */

import { PaymentScreen } from "@point_of_sale/js/Screens/PaymentScreen/PaymentScreen";
import { patch } from "@web/core/utils/patch";

patch(PaymentScreen.prototype, "l10n_sa_edi_pos.PaymentScreen", {
    toggleIsToInvoice() {
        // If the company is Saudi, POS orders should always be Invoiced
        if (this.currentOrder.pos.company.country && this.currentOrder.pos.company.country.code === 'SA') return false
        return this._super(...arguments);
    }
});

