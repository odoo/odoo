/** @odoo-module **/

import { BarcodeParser } from "@barcodes/js/barcode_parser";


QUnit.module('Barcodes', {}, function () {
QUnit.module('Barcode Parser', function () {
    QUnit.test('Test check digit', function (assert) {
        assert.expect(6);
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
        assert.equal(barcodeNomenclature.get_barcode_check_digit(ean8), ean8[ean8.length - 1]);
        ean8 = "4725992";
        assert.equal(barcodeNomenclature.get_barcode_check_digit(ean8 + "0"), 8);
        let ean13 = "1234567891231";
        assert.equal(barcodeNomenclature.get_barcode_check_digit(ean13), ean13[ean13.length - 1]);
        ean13 = "962434754318";
        assert.equal(barcodeNomenclature.get_barcode_check_digit(ean13 + "0"), 4);
        let utca = "692771981161";
        assert.equal(barcodeNomenclature.get_barcode_check_digit(utca), utca[utca.length - 1]);
        utca = "71679131569";
        assert.equal(barcodeNomenclature.get_barcode_check_digit(utca + "0"), 7);
    });
});
});
