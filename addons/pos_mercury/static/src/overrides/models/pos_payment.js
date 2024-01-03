/** @odoo-module */

import { PosPayment } from "@point_of_sale/app/models/pos_payment";
import { patch } from "@web/core/utils/patch";

patch(PosPayment.prototype, {
    set_credit_card_name() {
        if (this.mercury_card_number) {
            this.name = this.mercury_card_brand + " (****" + this.mercury_card_number + ")";
        }
    },
    is_done() {
        var res = super.is_done(...arguments);
        return res && !this.mercury_swipe_pending;
    },
    export_for_printing() {
        const result = super.export_for_printing(...arguments);
        result.mercury_data = this.mercury_data;
        result.mercury_auth_code = this.mercury_auth_code;
        return result;
    },
});
