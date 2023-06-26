/** @odoo-module */

import { Order } from "@point_of_sale/js/models";
import { patch } from "@web/core/utils/patch";

patch(Order.prototype, "l10n_sa_edi_pos.Order", {
    setup(options) {
        this._super(...arguments);
        if (this.pos.company.country && this.pos.company.country.code === 'SA') {
            this.set_to_invoice(true);
        }
    },
})
