import { models } from "@web/../tests/web_test_helpers";

export class BarcodeNomenclature extends models.ServerModel {
    _name = "barcode.nomenclature";

    _load_pos_data_fields() {
        return [];
    }

    _records = [
        {
            id: 1,
            name: "Default Nomenclature",
            rule_ids: [1, 2, 3, 4, 5],
            upc_ean_conv: true,
        },
    ];
}
