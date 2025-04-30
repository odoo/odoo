/** @odoo-module **/

import { expect, test } from "@odoo/hoot";
import { BarcodeParser } from "@barcodes/js/barcode_parser";

test.tags("headless");
test("Test check digit", async () => {
    const nomenclature = {
        id: 1,
        name: "normal",
        upc_ean_conv: "always",
        rules: [
            {
                id: 1,
                name: "Product Barcodes",
                barcode_nomenclature_id: 1,
                sequence: 90,
                type: "product",
                encoding: "any",
                pattern: ".*",
            },
        ],
    };
    const barcodeNomenclature = new BarcodeParser({ nomenclature });

    let ean8 = "87111125";
    expect(barcodeNomenclature.get_barcode_check_digit(ean8)).toEqual(+ean8[ean8.length - 1]);
    ean8 = "4725992";
    expect(barcodeNomenclature.get_barcode_check_digit(ean8 + "0")).toEqual(8);
    let ean13 = "1234567891231";
    expect(barcodeNomenclature.get_barcode_check_digit(ean13)).toEqual(+ean13[ean13.length - 1]);
    ean13 = "962434754318";
    expect(barcodeNomenclature.get_barcode_check_digit(ean13 + "0")).toEqual(4);
    let utca = "692771981161";
    expect(barcodeNomenclature.get_barcode_check_digit(utca)).toEqual(+utca[utca.length - 1]);
    utca = "71679131569";
    expect(barcodeNomenclature.get_barcode_check_digit(utca + "0")).toEqual(7);
});
