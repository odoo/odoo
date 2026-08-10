import { patch } from "@web/core/utils/patch";
import { ResCountry } from "@point_of_sale/../tests/unit/data/res_country.data";

patch(ResCountry.prototype, {
    _load_pos_self_data_fields() {
        return ["id", "name", "code", "vat_label", "state_ids"];
    },
});
