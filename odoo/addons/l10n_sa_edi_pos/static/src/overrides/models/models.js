/** @odoo-module */

import { Order } from "@point_of_sale/app/store/models";
import { patch } from "@web/core/utils/patch";

patch(Order.prototype, {
    setup(_defaultObj, options) {
        super.setup(...arguments);
        if (this.pos.isSACompany) {
            this.to_invoice = true;
        }
    },
    is_to_invoice() {
        if (this.pos.isSACompany) {
            return true;
        }
        return super.is_to_invoice(...arguments);
    },
    set_to_invoice(to_invoice) {
        if (this.pos.isSACompany) {
            this.assert_editable();
            this.to_invoice = true;
        } else {
            super.set_to_invoice(...arguments);
        }
    },
});
