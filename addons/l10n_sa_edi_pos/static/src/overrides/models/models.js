/** @odoo-module */

import { PosOrder } from "@point_of_sale/app/models/pos_order";
import { patch } from "@web/core/utils/patch";

patch(PosOrder.prototype, {
    setup(_defaultObj, options) {
        super.setup(...arguments);
        if (this.isInvoiceMandatoryForSA) {
            this.to_invoice = true;
        }
    },
    is_to_invoice() {
        if (this.isInvoiceMandatoryForSA) {
            return true;
        }
        return super.is_to_invoice(...arguments);
    },
    set_to_invoice(to_invoice) {
        if (this.isInvoiceMandatoryForSA) {
            this.assert_editable();
            this.to_invoice = true;
        } else {
            super.set_to_invoice(...arguments);
        }
    },

    set_partner(partner) {
        /*
        The settlement dialog sets is_settling_account = true after creating the order
        So making it default to false here as this is called after is_settling_account is set
        is_settling_account is only applicable if enterprise:pos_settle_due module is installed
        */
        super.set_partner(partner);
        if (this.is_settling_account) {
            this.set_to_invoice(false);
        }
    },

    get isInvoiceMandatoryForSA() {
        // Zatca enforces invoice, but for settlement due, invoices are not needed
        // Only applicable if enterprise:pos_settle_due module is installed
        return this.isSACompany && !this.is_settling_account;
    },

    get isSACompany() {
        return this.company.country_id?.code == "SA";
    },
});
