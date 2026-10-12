import { BarcodeRule } from "@point_of_sale/../tests/unit/data/barcode_rule.data";

BarcodeRule._records = [
    ...BarcodeRule._records,
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
