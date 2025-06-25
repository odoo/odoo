import { expect, test } from "@odoo/hoot";
import { decode } from "@barcodes_gs1_nomenclature/epc_service";

test.tags("RFID");

test("Decode SGTIN-96", async () => {
    let test = await decode("3066C4409047E140075BCD15");
    expect(test).toEqual("urn:epc:id:sgtin:95060001343.05.123456789");
});

test("Decode SGTIN-198", async () => {
    let test = await decode("3666C4409047E159B2C2BF100000000000000000000000000000");
    expect(test).toEqual("urn:epc:id:sgtin:95060001343.05.32a%2Fb");
});

test("Decode SSCC-96", async () => {
    let test = await decode("311BA1B300CE0A6A83000000");
    expect(test).toEqual("urn:epc:id:sscc:952012.03456789123");
});

test("Decode SGLN-96", async () => {
    let test = await decode("3276451FD46072000000162E");
    expect(test).toEqual("urn:epc:id:sgln:9521141.12345.5678");
});

test("Decode SGLN-195", async () => {
    let test = await decode("3976451FD46072CD9615F8800000000000000000000000000000");
    expect(test).toEqual("urn:epc:id:sgln:9521141.12345.32a%2Fb");
});
