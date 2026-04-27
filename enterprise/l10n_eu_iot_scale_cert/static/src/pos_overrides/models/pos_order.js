import { patch } from "@web/core/utils/patch";
import { PosOrder } from "@point_of_sale/app/models/pos_order";

patch(PosOrder.prototype, {
    getCustomerDisplayData() {
        return {
            ...super.getCustomerDisplayData(),
            showCertificationWarning: this.config.showCertificationWarning,
        };
    },

    export_for_printing() {
        const result = super.export_for_printing(...arguments);
        return {
            ...result,
            showCertificationWarning: this.config.showCertificationWarning,
        };
    },
});
