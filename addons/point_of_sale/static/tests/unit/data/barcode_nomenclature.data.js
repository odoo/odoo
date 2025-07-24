import { models } from "@web/../tests/web_test_helpers";

export class BarcodeNomenclature extends models.ServerModel {
    _name = "barcode.nomenclature";

    _load_pos_data_fields() {
        return [];
    }

    _records = [
        {
            id: 2,
            name: "Default Nomenclature",
        },
    ];
}

export class BarcodeRule extends models.ServerModel {
    _name = "barcode.rule";

    _load_pos_data_fields() {
        return ["id", "name", "barcode_nomenclature_id", "type", "encoding", "pattern"];
    }

    _records = [
        {
            id: 2,
            name: "Product Barcodes",
            barcode_nomenclature_id: 2,
            type: "product",
            encoding: "any",
            pattern: ".*",
        },
    ];
}
