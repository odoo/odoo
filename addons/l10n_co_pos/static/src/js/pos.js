/** @odoo-module */

import { PosGlobalState, Order } from "@point_of_sale/js/models";
import { patch } from "@web/core/utils/patch";

patch(PosGlobalState.prototype, "l10n_co_pos.PosGlobalState", {
    is_colombian_country() {
        return this.company.country?.code === "CO";
    },
});

patch(Order.prototype, "l10n_co_pos.Order", {
    export_for_printing() {
        const result = this._super(...arguments);
        result.l10n_co_dian = this.get_l10n_co_dian();
        return result;
    },
    set_l10n_co_dian(l10n_co_dian) {
        this.l10n_co_dian = l10n_co_dian;
    },
    get_l10n_co_dian() {
        return this.l10n_co_dian;
    },
    wait_for_push_order() {
        var result = this._super(...arguments);
        result = Boolean(result || this.pos.is_colombian_country());
        return result;
    },
});
