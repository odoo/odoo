/** @odoo-module */

import { PosOrder } from "@point_of_sale/app/models/pos_order";
import { patch } from "@web/core/utils/patch";
import { qrCodeSrc } from "@point_of_sale/utils";

patch(PosOrder.prototype, {
    setup() {
        super.setup(...arguments);
        if (this.isSACompany()) {
            this.to_invoice = true;
        }
    },

    isToInvoice() {
        if (this.isSACompany()) {
            return true;
        }
        return super.isToInvoice(...arguments);
    },
    setToInvoice(to_invoice) {
        if (this.isSACompany()) {
            this.assertEditable();
            this.to_invoice = true;
        } else {
            super.setToInvoice(...arguments);
        }
    },
    get notLegal() {
        return !this.l10n_sa_invoice_qr_code_str || this.l10n_sa_invoice_edi_state !== "sent";
    },
    generateQrcode() {
        if (!this.notLegal && this.isSACompany()) {
            return qrCodeSrc(this.l10n_sa_invoice_qr_code_str);
        }
        return false;
    },
});
