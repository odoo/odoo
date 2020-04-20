odoo.define('barcodes.barcode_parser', function (require) {
"use strict";

var BarcodeParser = require('barcodes.BarcodeParser');


QUnit.module('Barcodes', {}, function () {
QUnit.module('Barcode Parser', {
    beforeEach: function () {
        this.data = {
            'barcode.nomenclature': {
                fields: {
                    name: {type: 'char', string: 'Barcode Nomenclature'},
                    rule_ids: {type: 'one2many', relation: 'barcode.rule'},
                    upc_ean_conv: {type: 'selection', string: 'UPC/EAN Conversion'},
                    is_gs1_nomenclature: {type: 'boolean', string: 'Is GS1 Nomenclature'},
                    gs1_separator_fnc1: {type: 'char', string: 'FNC1 Seperator Alternative'}
                },
                records: [
                    {id: 1, name: "normal", upc_ean_conv: "always", is_gs1_nomenclature: false, gs1_separator_fnc1: ''},
                    {id: 2, name: "GS1", upc_ean_conv: "always", is_gs1_nomenclature: true, gs1_separator_fnc1: ''},
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
                    {
                        "id": 1,
                        "name": "Global Trade Item Number (GTIN)",
                        "barcode_nomenclature_id": 2,
                        "sequence": 100,
                        "encoding": "gs1-128",
                        "pattern": "(01)(\\d{14})",
                        "type": "product",
                        "gs1_content_type": "identifier",
                        "gs1_decimal_usage": false
                    }, {
                        "id": 2,
                        "name": "GTIN of contained trade items",
                        "barcode_nomenclature_id": 2,
                        "sequence": 101,
                        "encoding": "gs1-128",
                        "pattern": "(02)(\\d{14})",
                        "type": "product",
                        "gs1_content_type": "identifier",
                        "gs1_decimal_usage": false
                    }, {
                        "id": 3,
                        "name": "Batch or lot number",
                        "barcode_nomenclature_id": 2,
                        "sequence": 102,
                        "encoding": "gs1-128",
                        "pattern": "(10)([!\"%/0-9:?A-Za-z]{0,20})",
                        "type": "product",
                        "gs1_content_type": "alpha",
                        "gs1_decimal_usage": false
                    }, {
                        "id": 4,
                        "name": "Serial number",
                        "barcode_nomenclature_id": 2,
                        "sequence": 105,
                        "encoding": "gs1-128",
                        "pattern": "(21)([!\"%/0-9:?A-Za-z]{0,20})",
                        "type": "product",
                        "gs1_content_type": "alpha",
                        "gs1_decimal_usage": false
                    }, {
                        "id": 5,
                        "name": "Packaging date (YYMMDD)",
                        "barcode_nomenclature_id": 2,
                        "sequence": 103,
                        "encoding": "gs1-128",
                        "pattern": "(13)(\\d{6})",
                        "type": "product",
                        "gs1_content_type": "date",
                        "gs1_decimal_usage": false
                    }, {
                        "id": 6,
                        "name": "Best before date (YYMMDD)",
                        "barcode_nomenclature_id": 2,
                        "sequence": 104,
                        "encoding": "gs1-128",
                        "pattern": "(15)(\\d{6})",
                        "type": "product",
                        "gs1_content_type": "date",
                        "gs1_decimal_usage": false
                    }, {
                        "id": 7,
                        "name": "Expiration date (YYMMDD)",
                        "barcode_nomenclature_id": 2,
                        "sequence": 105,
                        "encoding": "gs1-128",
                        "pattern": "(16)(\\d{6})",
                        "type": "product",
                        "gs1_content_type": "date",
                        "gs1_decimal_usage": false
                    }, {
                        "id": 8,
                        "name": "Variable count of items (variabl",
                        "barcode_nomenclature_id": 2,
                        "sequence": 105,
                        "encoding": "gs1-128",
                        "pattern": "(30)(\\d{0,8})",
                        "type": "product",
                        "gs1_content_type": "measure",
                        "gs1_decimal_usage": false
                    }, {
                        "id": 9,
                        "name": "Count of trade items or trade it",
                        "barcode_nomenclature_id": 2,
                        "sequence": 105,
                        "encoding": "gs1-128",
                        "pattern": "(37)(\\d{0,8})",
                        "type": "product",
                        "gs1_content_type": "measure",
                        "gs1_decimal_usage": false
                    }, {
                        "id": 10,
                        "name": "Net weight, kilograms (variable",
                        "barcode_nomenclature_id": 2,
                        "sequence": 105,
                        "encoding": "gs1-128",
                        "pattern": "(310[0-5])(\\d{6})",
                        "type": "product",
                        "gs1_content_type": "measure",
                        "gs1_decimal_usage": true
                    }, {
                        "id": 11,
                        "name": "Length or first dimension, metre",
                        "barcode_nomenclature_id": 2,
                        "sequence": 105,
                        "encoding": "gs1-128",
                        "pattern": "(311[0-5])(\\d{6})",
                        "type": "product",
                        "gs1_content_type": "measure",
                        "gs1_decimal_usage": true
                    }, {
                        "id": 12,
                        "name": "Net volume, litres (variable mea",
                        "barcode_nomenclature_id": 2,
                        "sequence": 105,
                        "encoding": "gs1-128",
                        "pattern": "(315[0-5])(\\d{6})",
                        "type": "product",
                        "gs1_content_type": "measure",
                        "gs1_decimal_usage": true
                    }, {
                        "id": 13,
                        "name": "Length or first dimension, inche",
                        "barcode_nomenclature_id": 2,
                        "sequence": 105,
                        "encoding": "gs1-128",
                        "pattern": "(321[0-5])(\\d{6})",
                        "type": "product",
                        "gs1_content_type": "measure",
                        "gs1_decimal_usage": true
                    }, {
                        "id": 14,
                        "name": "Net weight (or volume), ounces (",
                        "barcode_nomenclature_id": 2,
                        "sequence": 105,
                        "encoding": "gs1-128",
                        "pattern": "(357[0-5])(\\d{6})",
                        "type": "product",
                        "gs1_content_type": "measure",
                        "gs1_decimal_usage": true
                    }
                ],
            }
        };
    }
}, function () {
    QUnit.test('Test check digit', async function (assert) {
        assert.expect(6);
        var barcodeNomenclature = new BarcodeParser({'nomenclature_id': false});
        await barcodeNomenclature.loaded;

        var ean8 = "87111125";
        assert.equal(barcodeNomenclature.get_barcode_check_digit("0".repeat(10) + ean8), ean8.charAt(ean8.length - 1));
        ean8 = "4725992";
        assert.equal(barcodeNomenclature.get_barcode_check_digit("0".repeat(10) + ean8 + "0"), 8);
        var ean13 = "1234567891231";
        assert.equal(barcodeNomenclature.get_barcode_check_digit("0".repeat(5) + ean13), ean13.charAt(ean13.length - 1));
        ean13 = "962434754318";
        assert.equal(barcodeNomenclature.get_barcode_check_digit("0".repeat(5) + ean13 + "0"), 4);
        var utca = "692771981161";
        assert.equal(barcodeNomenclature.get_barcode_check_digit("0".repeat(6) + utca), utca.charAt(utca.length - 1));
        utca = "71679131569";
        assert.equal(barcodeNomenclature.get_barcode_check_digit("0".repeat(6) + utca + "0"), 7);
    });

    QUnit.test('Test gs1 date barcode', async function (assert) {
        assert.expect(9);
        var barcodeNomenclature = new BarcodeParser({'nomenclature_id': false});
        await barcodeNomenclature.loaded;

        // 20/10/2015 -> 151020
        var dateGS1 = "151020";
        var date = barcodeNomenclature.gs1_date_to_date(dateGS1);
        assert.equal(date.getDate(), 20);
        assert.equal(date.getMonth() + 1, 10);
        assert.equal(date.getFullYear(), 2015);

        // XX/03/2052 -> 520300 -> (if day no set take last day of the month -> 31)
        dateGS1 = "520300";
        date = barcodeNomenclature.gs1_date_to_date(dateGS1);
        assert.equal(date.getDate(), 31);
        assert.equal(date.getMonth() + 1, 3);
        assert.equal(date.getFullYear(), 2052);

        // XX/02/2020 -> 520200 -> (if day no set take last day of the month -> 29)
        dateGS1 = "200200";
        date = barcodeNomenclature.gs1_date_to_date(dateGS1);
        assert.equal(date.getDate(), 29);
        assert.equal(date.getMonth() + 1, 2);
        assert.equal(date.getFullYear(), 2020);
    });

    QUnit.test('Test gs1 decompose extanded', async function (assert) {
        assert.expect(19);
        var barcodeNomenclature = new BarcodeParser({'nomenclature_id': false});
        await barcodeNomenclature.loaded;

        barcodeNomenclature.nomenclature = this.data['barcode.nomenclature'].records[0];
        barcodeNomenclature.nomenclature.rules = this.data['barcode.rule'].records;

        // (01)94019097685457(10)33650100138(3102)002004(15)131018
        var code128 = "01940190976854571033650100138\x1D310200200415131018";
        var res = barcodeNomenclature.gs1_decompose_extanded(code128);
        assert.equal(res.length, 4);
        assert.equal(res[0].ai, "01");

        assert.equal(res[1].ai, "10");

        assert.equal(res[2].ai, "3102");
        assert.equal(res[2].value, 20.04);

        assert.equal(res[3].ai, "15");
        assert.equal(typeof res[3].value.getFullYear, 'function');
        assert.equal(res[3].value.getFullYear(), 2013);
        assert.equal(res[3].value.getDate(), 18);
        assert.equal(res[3].value.getMonth() + 1, 10);

        // (01)94019097685457(13)170119(30)17
        code128 = "0194019097685457131701193017";
        res = barcodeNomenclature.gs1_decompose_extanded(code128);
        assert.equal(res.length, 3);
        assert.equal(res[0].ai, "01");

        assert.equal(res[1].ai, "13");
        assert.equal(typeof res[1].value.getFullYear, 'function');
        assert.equal(res[1].value.getFullYear(), 2017);
        assert.equal(res[1].value.getDate(), 19);
        assert.equal(res[1].value.getMonth() + 1, 1);

        assert.equal(res[2].ai, "30");
        assert.equal(res[2].value, 17);

    });

    QUnit.test('Test Alternative GS1 Separator (fnc1)', async function (assert) {
        assert.expect(5);
        var barcodeNomenclature = new BarcodeParser({'nomenclature_id': false});
        await barcodeNomenclature.loaded;

        barcodeNomenclature.nomenclature = this.data['barcode.nomenclature'].records[0];
        barcodeNomenclature.nomenclature.gs1_separator_fnc1 = "#";
        barcodeNomenclature.nomenclature.rules = this.data['barcode.rule'].records;

        // (21)12345(15)090101(16)100101
        var code128 = "2112345#1509010116100101";
        var res = barcodeNomenclature.gs1_decompose_extanded(code128);
        assert.equal(res.length, 3);
        assert.equal(res[0].ai, "21");
        assert.equal(res[0].value, "12345");
        assert.equal(res[1].ai, "15");
        assert.equal(res[2].ai, "16");
    });
});
});
});
