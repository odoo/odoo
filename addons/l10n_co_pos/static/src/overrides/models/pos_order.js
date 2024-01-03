/** @odoo-module */

import { PosOrder } from "@point_of_sale/app/models/pos_order";
import { patch } from "@web/core/utils/patch";

patch(PosOrder.prototype, {
    is_colombian_country() {
        return this.company.country_id?.code === "CO";
    },
    export_for_printing() {
        const result = super.export_for_printing(...arguments);
        result.l10n_co_dian = this.name;
        return result;
    },
    wait_for_push_order() {
        var result = super.wait_for_push_order(...arguments);
        result = Boolean(result || this.is_colombian_country());
        return result;
    },
});
