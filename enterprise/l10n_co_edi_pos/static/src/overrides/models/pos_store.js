/** @odoo-module */

import { PosStore } from "@point_of_sale/app/store/pos_store";
import { patch } from "@web/core/utils/patch";

patch(PosStore.prototype, {
    // @Override
    getSyncAllOrdersContext(orders, options = {}) {
        const context = super.getSyncAllOrdersContext(orders, options);

        if (this.company.l10n_co_edi_pos_dian_enabled) {
            // this ensures that we send all the invoices (generated from pos orders) to dian
            context.generate_pdf = true;
        }

        return context;
    },
});
