/** @odoo-module */

import { PosOrder } from "@point_of_sale/app/models/pos_order";
import { patch } from "@web/core/utils/patch";
import { qrCodeSrc } from "@point_of_sale/utils";

patch(PosOrder.prototype, {
    setup() {
        super.setup(...arguments);
        if (this.isInvoiceMandatoryForSA()) {
            this.to_invoice = true;
        }
    },

    isInvoiceMandatoryForSA() {
        // Zatca enforces invoice, but for settlement due, invoices are not needed
        // Only applicable if enterprise:pos_settle_due module is installed
        return this.isSACompany() && !this.is_settling_account;
    },

    isToInvoice() {
        if (this.isInvoiceMandatoryForSA()) {
            return true;
        }
        return super.isToInvoice(...arguments);
    },
    setToInvoice(to_invoice) {
        if (this.isInvoiceMandatoryForSA()) {
            this.assertEditable();
            this.to_invoice = true;
        } else {
            super.setToInvoice(...arguments);
        }
    },

    setPartner(partner) {
        /*
        The settlement dialog sets is_settling_account = true after creating the order
        So making it default to false here as this is called after is_settling_account is set
        is_settling_account is only applicable if enterprise:pos_settle_due module is installed
        */
        super.setPartner(partner);
        if (this.is_settling_account) {
            this.setToInvoice(false);
        }
    },

    get notLegal() {
        return !this.l10n_sa_invoice_qr_code_str;
    },
    generateQrcode() {
        if (!this.notLegal && this.isSACompany()) {
            return qrCodeSrc(this.l10n_sa_invoice_qr_code_str);
        }
        return false;
    },
});
