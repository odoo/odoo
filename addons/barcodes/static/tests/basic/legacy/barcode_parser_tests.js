odoo.define('barcodes/static/tests/barcode_parser_tests.js', function (require) {
"use strict";

const BarcodeParser = require('barcodes.BarcodeParser');


QUnit.module('Barcodes', {}, function () {
QUnit.module('Barcode Parser', {
    beforeEach: function () {
        this.data = {
            'barcode.nomenclature': {
                fields: {
                    name: {type: 'char', string: 'Barcode Nomenclature'},
                    rule_ids: {type: 'one2many', relation: 'barcode.rule'},
                    upc_ean_conv: {type: 'selection', string: 'UPC/EAN Conversion'},
                },
                records: [
                    {id: 1, name: "normal", upc_ean_conv: "always"},
                ],
            },
            'barcode.rule': {
                fields: {
                    name: {type: 'char', string: 'Barcode Nomenclature'},
                    barcode_nomenclature_id: {type: 'many2one', relation: 'barcode.nomenclature'},
                    sequence: {type: 'integer', string: 'Sequence'},
                    encoding: {type: 'selection', string: 'Encoding'},
                    type: {type: 'selection', string: 'Type'},
                    pattern: {type: 'Char', string: 'Pattern'},
                    alias: {type: 'Char', string: 'Alias'},
                },
                records: [
                    {id: 1, name: "Product Barcodes", barcode_nomenclature_id: 1, sequence: 90, type: 'product', encoding: 'any', pattern: ".*"},
                ],
            }
        };
    }
}, function () {
    QUnit.test('Test check digit', async function (assert) {
        assert.expect(6);
        const barcodeNomenclature = new BarcodeParser({'nomenclature_id': 1});
        await barcodeNomenclature.loaded;

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
});
