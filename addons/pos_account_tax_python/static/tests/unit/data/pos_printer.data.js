import { patch } from "@web/core/utils/patch";
import { PosPrinter } from "@point_of_sale/../tests/unit/data/pos_printer.data";

patch(PosPrinter.prototype, {
    _load_pos_data_fields() {
        return [...super._load_pos_data_fields(), "formula_decoded_info"];
    },
});
