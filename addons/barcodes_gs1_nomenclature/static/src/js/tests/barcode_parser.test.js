import { barcodeService } from "@barcodes/barcode_service";
import { BarcodeParser } from "@barcodes/js/barcode_parser";
import { expect, test } from "@odoo/hoot";

function buildBarcodeParser(diff = {}) {
    const nomenclature = {
        id: 2,
        name: "GS1",
        upc_ean_conv: "always",
        is_gs1_nomenclature: true,
        gs1_separator_fnc1: "",
        rules: [
            {
                id: 2,
                name: "Global Trade Item Number (GTIN)",
                barcode_nomenclature_id: 2,
                sequence: 100,
                encoding: "gs1-128",
                pattern: "(01)(\\d{14})",
                type: "product",
                gs1_content_type: "identifier",
                gs1_decimal_usage: false,
            },
            {
                id: 3,
                name: "GTIN of contained trade items",
                barcode_nomenclature_id: 2,
                sequence: 101,
                encoding: "gs1-128",
                pattern: "(02)(\\d{14})",
                type: "product",
                gs1_content_type: "identifier",
                gs1_decimal_usage: false,
            },
            {
                id: 4,
                name: "Batch or lot number",
                barcode_nomenclature_id: 2,
                sequence: 102,
                encoding: "gs1-128",
                pattern: '(10)([!"%/0-9:?A-Za-z]{0,20})',
                type: "product",
                gs1_content_type: "alpha",
                gs1_decimal_usage: false,
            },
            {
                id: 5,
                name: "Serial number",
                barcode_nomenclature_id: 2,
                sequence: 105,
                encoding: "gs1-128",
                pattern: '(21)([!"%/0-9:?A-Za-z]{0,20})',
                type: "product",
                gs1_content_type: "alpha",
                gs1_decimal_usage: false,
            },
            {
                id: 6,
                name: "Pack date (YYMMDD)",
                barcode_nomenclature_id: 2,
                sequence: 103,
                encoding: "gs1-128",
                pattern: "(13)(\\d{6})",
                type: "pack_date",
                gs1_content_type: "date",
                gs1_decimal_usage: false,
            },
            {
                id: 7,
                name: "Best before date (YYMMDD)",
                barcode_nomenclature_id: 2,
                sequence: 104,
                encoding: "gs1-128",
                pattern: "(15)(\\d{6})",
                type: "use_date",
                gs1_content_type: "date",
                gs1_decimal_usage: false,
            },
            {
                id: 8,
                name: "Expiration date (YYMMDD)",
                barcode_nomenclature_id: 2,
                sequence: 105,
                encoding: "gs1-128",
                pattern: "(16)(\\d{6})",
                type: "expiration_date",
                gs1_content_type: "date",
                gs1_decimal_usage: false,
            },
            {
                id: 9,
                name: "Variable count of items (variabl",
                barcode_nomenclature_id: 2,
                sequence: 105,
                encoding: "gs1-128",
                pattern: "(30)(\\d{0,8})",
                type: "product",
                gs1_content_type: "measure",
                gs1_decimal_usage: false,
            },
            {
                id: 10,
                name: "Count of trade items or trade it",
                barcode_nomenclature_id: 2,
                sequence: 105,
                encoding: "gs1-128",
                pattern: "(37)(\\d{0,8})",
                type: "product",
                gs1_content_type: "measure",
                gs1_decimal_usage: false,
            },
            {
                id: 11,
                name: "Net weight, kilograms (variable",
                barcode_nomenclature_id: 2,
                sequence: 105,
                encoding: "gs1-128",
                pattern: "(310[0-5])(\\d{6})",
                type: "product",
                gs1_content_type: "measure",
                gs1_decimal_usage: true,
            },
            {
                id: 12,
                name: "Length or first dimension, metre",
                barcode_nomenclature_id: 2,
                sequence: 105,
                encoding: "gs1-128",
                pattern: "(311[0-5])(\\d{6})",
                type: "product",
                gs1_content_type: "measure",
                gs1_decimal_usage: true,
            },
            {
                id: 13,
                name: "Net volume, litres (variable mea",
                barcode_nomenclature_id: 2,
                sequence: 105,
                encoding: "gs1-128",
                pattern: "(315[0-5])(\\d{6})",
                type: "product",
                gs1_content_type: "measure",
                gs1_decimal_usage: true,
            },
            {
                id: 14,
                name: "Length or first dimension, inche",
                barcode_nomenclature_id: 2,
                sequence: 105,
                encoding: "gs1-128",
                pattern: "(321[0-5])(\\d{6})",
                type: "product",
                gs1_content_type: "measure",
                gs1_decimal_usage: true,
            },
            {
                id: 15,
                name: "Net weight (or volume), ounces (",
                barcode_nomenclature_id: 2,
                sequence: 105,
                encoding: "gs1-128",
                pattern: "(357[0-5])(\\d{6})",
                type: "product",
                gs1_content_type: "measure",
                gs1_decimal_usage: true,
            },
        ],
    };
    return new BarcodeParser({ nomenclature: { ...nomenclature, ...diff } });
}

test("Test gs1 date barcode", async () => {
    const barcodeNomenclature = buildBarcodeParser();

    // 20/10/2015 -> 151020
    let dateGS1 = "151020";
    let date = barcodeNomenclature.gs1_date_to_date(dateGS1);
    expect(date.getDate()).toBe(20);
    expect(date.getMonth() + 1).toBe(10);
    expect(date.getFullYear()).toBe(2015);

    // XX/03/2052 -> 520300 -> (if day no set take last day of the month -> 31)
    dateGS1 = "520300";
    date = barcodeNomenclature.gs1_date_to_date(dateGS1);
    expect(date.getDate()).toBe(31);
    expect(date.getMonth() + 1).toBe(3);
    expect(date.getFullYear()).toBe(2052);

    // XX/02/2020 -> 520200 -> (if day no set take last day of the month -> 29)
    dateGS1 = "200200";
    date = barcodeNomenclature.gs1_date_to_date(dateGS1);
    expect(date.getDate()).toBe(29);
    expect(date.getMonth() + 1).toBe(2);
    expect(date.getFullYear()).toBe(2020);
});

test("Test gs1 decompose extended", async () => {
    const barcodeNomenclature = buildBarcodeParser();

    // (01)94019097685457(10)33650100138(3102)002004(15)131018
    const code128 = "01940190976854571033650100138\x1D310200200415131018";
    let res = barcodeNomenclature.gs1_decompose_extended(code128);
    expect(res.length).toBe(4);
    expect(res[0].ai).toBe("01");

    expect(res[1].ai).toBe("10");

    expect(res[2].ai).toBe("3102");
    expect(res[2].value).toBe(20.04);

    expect(res[3].ai).toBe("15");
    expect(res[3].value.getFullYear()).toBe(2013);
    expect(res[3].value.getDate()).toBe(18);
    expect(res[3].value.getMonth() + 1).toBe(10);

    // Check multiple variants of the same GS1, the result should be always the same.
    // (01)94019097685457(30)17(13)170119
    const gs1Barcodes = [
        "0194019097685457300000001713170119",
        "\x1D0194019097685457300000001713170119",
        "01940190976854573017\x1D13170119",
    ];
    for (const gs1Barcode of gs1Barcodes) {
        res = barcodeNomenclature.gs1_decompose_extended(gs1Barcode);
        expect(res.length).toBe(3);
        expect(res[0].ai).toBe("01");

        expect(res[1].ai).toBe("30");
        expect(res[1].value).toBe(17);

        expect(res[2].ai).toBe("13");
        expect(res[2].value.getFullYear()).toBe(2017);
        expect(res[2].value.getDate()).toBe(19);
        expect(res[2].value.getMonth() + 1).toBe(1);
    }
});

test("Test Alternative GS1 Separator (fnc1)", async () => {
    let barcodeNomenclature = buildBarcodeParser();

    // (21)12345(15)090101(16)100101
    const code128 = "2112345#1509010116100101";
    expect(() => {
        barcodeNomenclature.gs1_decompose_extended(barcodeService.cleanBarcode(code128));
    }).toThrow();

    // Reload the nomenclature but this time using '#' as separator.
    barcodeNomenclature = buildBarcodeParser({ gs1_separator_fnc1: "#" });
    const res = barcodeNomenclature.gs1_decompose_extended(barcodeService.cleanBarcode(code128));
    expect(res.length).toBe(3);
    expect(res[0].ai).toBe("21");
    expect(res[0].value).toBe("12345");
    expect(res[1].ai).toBe("15");
    expect(res[2].ai).toBe("16");
});
