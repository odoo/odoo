import { PosOrder } from "@point_of_sale/app/models/pos_order";
import { patch } from "@web/core/utils/patch";

patch(PosOrder.prototype, {
    setup() {
        super.setup(...arguments);
    },
    is_french_country() {
        const french_countries = ["FR", "MF", "MQ", "NC", "PF", "RE", "GF", "GP", "TF"];
        return french_countries.includes(this.company.country_id?.code);
    },
    export_for_printing(baseUrl, headerData) {
        const result = super.export_for_printing(...arguments);
        result.l10n_fr_hash = this.l10n_fr_hash;
        if (this.is_french_country()) {
            result.pos_qr_code = false;
        }
        return result;
    },
});
