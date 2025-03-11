/** @odoo-module */

import { PosOrder } from "@point_of_sale/app/models/pos_order";
import { patch } from "@web/core/utils/patch";

patch(PosOrder.prototype, {
    setup() {
        super.setup(...arguments);
        if (this.isSACompany()) {
            this.to_invoice = true;
        }
    },

    isSACompany() {
        return this.company.country_id?.code === "SA";
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
});
