/** @odoo-module */

import { patch } from "@web/core/utils/patch";
import { Order } from "@point_of_sale/app/store/models";

patch(Order.prototype, {
    //@override
    export_for_printing() {
        return {
            ...super.export_for_printing(...arguments),
            l10n_es_pos_tbai_qrsrc: this.l10n_es_pos_tbai_qrsrc,
        };
    },
});
