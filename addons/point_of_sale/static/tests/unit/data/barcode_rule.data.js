import { models } from "@web/../tests/web_test_helpers";

export class BarcodeRule extends models.ServerModel {
    _name = "barcode.rule";

    _load_pos_data_fields() {
        return [];
    }

    _records = [
        {
            id: 1,
            name: "Product Barcodes",
            barcode_nomenclature_id: 1,
            sequence: 90,
            type: "product",
            encoding: "any",
            pattern: ".*",
            alias: "",
        },
        {
            id: 2,
            name: "Customer Barcodes",
            barcode_nomenclature_id: 1,
            sequence: 40,
            type: "client",
            encoding: "any",
            pattern: "042",
            alias: "",
        },
        {
            id: 3,
            name: "Discount Barcodes",
            barcode_nomenclature_id: 1,
            sequence: 20,
            type: "discount",
            encoding: "any",
            pattern: "22{NN}",
            alias: "",
        },
        {
            id: 4,
            name: "Cashier Barcodes",
            barcode_nomenclature_id: 1,
            sequence: 50,
            type: "cashier",
            encoding: "any",
            pattern: "041",
            alias: "",
        },
        {
            id: 5,
            name: "Coupon & Gift Card Barcodes",
            barcode_nomenclature_id: 1,
            sequence: 50,
            type: "coupon",
            encoding: "any",
            pattern: "043|044",
            alias: "",
        },
    ];
}
