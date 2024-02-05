/** @odoo-module */

import { PosStore } from "@point_of_sale/app/store/pos_store";
import { Order } from "@point_of_sale/app/store/models";
import { patch } from "@web/core/utils/patch";

patch(PosStore.prototype, {
    is_colombian_country() {
        return this.company.country_id?.code === "CO";
    },
});

patch(Order.prototype, {
    export_for_printing() {
        const result = super.export_for_printing(...arguments);
        result.l10n_co_dian = this.get_l10n_co_dian();
        return result;
    },
    async updateWithServerData(data) {
        await super.updateWithServerData(data);
        if ("name" in data) {
            this.set_l10n_co_dian(data.name);
        }
    },
    init_from_JSON(json) {
        super.init_from_JSON(...arguments);
        this.set_l10n_co_dian(json.l10n_co_dian);
    },
    set_l10n_co_dian(l10n_co_dian) {
        this.l10n_co_dian = l10n_co_dian;
    },
    get_l10n_co_dian() {
        return this.l10n_co_dian;
    },
});
