import { models } from "@web/../tests/web_test_helpers";

export class BarcodeNomenclature extends models.ServerModel {
    _name = "barcode.nomenclature";

    _load_pos_data_fields() {
        return [];
    }
}
