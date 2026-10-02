import { BarcodeNomenclature } from "@point_of_sale/../tests/unit/data/barcode_nomenclature.data";

BarcodeNomenclature._records = BarcodeNomenclature._records.map((rec) => {
    if (rec.id === 1) {
        rec.rule_ids.push(5);
    }

    return rec;
});
