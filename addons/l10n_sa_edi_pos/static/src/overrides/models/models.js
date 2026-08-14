/** @odoo-module */

import { Order } from "@point_of_sale/app/store/models";
import { patch } from "@web/core/utils/patch";

patch(Order.prototype, {
    setup(_defaultObj, options) {
        super.setup(...arguments);
        if (this.isInvoiceMandatoryForSA) {
            this.to_invoice = true;
        }
    },
    is_to_invoice() {
        if (this.pos.isSACompany) {
            // pos_settle_due flags the order as a settlement after set_partner() has run, so the
            // value computed in setup() cannot be trusted, recompute it here.
            return this.isInvoiceMandatoryForSA;
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

    export_as_JSON() {
        const json = super.export_as_JSON(...arguments);
        if (this.pos.isSACompany) {
            // The raw to_invoice attribute was forced to true before the order was flagged as a
            // settlement. Realign it with is_to_invoice().
            json.to_invoice = this.is_to_invoice();
        }
        return json;
    },

    get isInvoiceMandatoryForSA() {
        // Zatca enforces invoice, but for settlement due, invoices are not needed
        // Only applicable if enterprise:pos_settle_due module is installed
        return this.pos.isSACompany && !this.is_settling_account;
    },

    init_from_JSON(json) {
        super.init_from_JSON(...arguments);
        // Needed to reprint the receipt of a past order with its Phase 2 QR code.
        this.l10n_sa_invoice_qr_code_str = json.l10n_sa_invoice_qr_code_str;
    },
});
