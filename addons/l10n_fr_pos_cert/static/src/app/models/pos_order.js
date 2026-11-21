import { PosOrder } from "@point_of_sale/app/models/pos_order";
import { patch } from "@web/core/utils/patch";
import { isFrenchCountry } from "@l10n_fr_pos_cert/app/utils";

patch(PosOrder.prototype, {
    get canEditPayment() {
        return isFrenchCountry(this.company) ? false : super.canEditPayment;
    },
});
