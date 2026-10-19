import { expect, test } from "@odoo/hoot";
import { decode } from "@barcodes_gs1_nomenclature/js/epc_utils";

test.tags("RFID");

test("Decode SGTIN-96 URI", () => {
    const test = decode("3066C4409047E140075BCD15", true);
    expect(test).toEqual("urn:epc:id:sgtin:95060001343.05.123456789");
});

test("Decode SGTIN-96 Barcode Format", () => {
    const test = decode("3066C4409047E140075BCD15");
    expect(test).toEqual("\x1D0109506000134352\x1D21123456789");
});

test("Decode SGTIN-198 URI", () => {
    const test = decode("3666C4409047E159B2C2BF100000000000000000000000000000", true);
    expect(test).toEqual("urn:epc:id:sgtin:95060001343.05.32a%2Fb");
});

test("Decode SGTIN-198 Barcode Format", () => {
    const test = decode("3666C4409047E159B2C2BF100000000000000000000000000000");
    expect(test).toEqual("\x1D0109506000134352\x1D2132a/b");
});

test("Decode SSCC-96 URI", () => {
    const test = decode("311BA1B300CE0A6A83000000", true);
    expect(test).toEqual("urn:epc:id:sscc:952012.03456789123");
});

test("Decode SSCC-96 Barcode Format", () => {
    const test = decode("311BA1B300CE0A6A83000000");
    expect(test).toEqual("\x1D00095201234567891235");
});

test("Decode SGLN-96 URI", () => {
    const test = decode("3276451FD46072000000162E", true);
    expect(test).toEqual("urn:epc:id:sgln:9521141.12345.5678");
});

test("Decode SGLN-96 Barcode Format", () => {
    const test = decode("3276451FD46072000000162E");
    expect(test).toEqual("\x1D2545678\x1D4149521141123454");
});

test("Decode SGLN-195 URI", () => {
    const test = decode("3976451FD46072CD9615F8800000000000000000000000000000", true);
    expect(test).toEqual("urn:epc:id:sgln:9521141.12345.32a%2Fb");
});

test("Decode SGLN-195 Barcode Format", () => {
    const test = decode("3976451FD46072CD9615F8800000000000000000000000000000");
    expect(test).toEqual("\x1D25432a/b\x1D4149521141123454");
});

test("Decode unrecognized EPC", () => {
    const test = decode("006604409047014007500015");
    expect(test).toEqual("006604409047014007500015");
});

test("Decode non hex value", () => {
    const test = decode("300123456789ABCDEFGHIJ");
    expect(test).toEqual("300123456789ABCDEFGHIJ");
});
