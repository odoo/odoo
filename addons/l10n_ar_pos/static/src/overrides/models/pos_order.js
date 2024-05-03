import { PosOrder } from "@point_of_sale/app/models/pos_order";
import { patch } from "@web/core/utils/patch";

patch(PosOrder.prototype, {
    setup() {
        super.setup(...arguments);
        if (this.isArgentineanCompany()) {
            if (!this.partner_id) {
                this.update({ partner_id: this.session._consumidor_final_anonimo_id });
            }
        }
    },
    isArgentineanCompany() {
        return this.company.country_id?.code == "AR";
    },
});
