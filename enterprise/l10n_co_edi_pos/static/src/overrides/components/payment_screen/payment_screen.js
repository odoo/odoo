/** @odoo-module */

import { PaymentScreen } from "@point_of_sale/app/screens/payment_screen/payment_screen";
import { patch } from "@web/core/utils/patch";
import { useService } from "@web/core/utils/hooks";

patch(PaymentScreen.prototype, {
    setup() {
        this.ormService = useService("orm");
        return super.setup(...arguments);
    },
    async _finalizeValidation() {
        if (this.pos.company.l10n_co_edi_pos_dian_enabled) {
            const currentPartner = this.currentOrder.get_partner();

            if (
                !currentPartner ||
                currentPartner.id === this.pos.session._l10n_co_final_consumer_id
            ) {
                this.currentOrder.set_to_invoice(false);
            } else {
                this.currentOrder.set_to_invoice(true);
            }
        }

        super._finalizeValidation();
    },
    shouldDownloadInvoice() {
        return this.pos.company.l10n_co_edi_pos_dian_enabled
            ? false
            : super.shouldDownloadInvoice();
    },
});
