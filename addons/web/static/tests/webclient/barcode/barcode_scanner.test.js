import { expect, test } from "@odoo/hoot";
import { Deferred } from "@odoo/hoot-mock";
import {
    contains,
    makeMockEnv,
    mountWithCleanup,
    patchWithCleanup,
} from "@web/../tests/web_test_helpers";

import { browser } from "@web/core/browser/browser";
import { BarcodeDialog, scanBarcode } from "@web/webclient/barcode/barcode_scanner";
import { WebClient } from "@web/webclient/webclient";

/* global ZXing */

test("Barcode scanner crop overlay", async () => {
    const env = await makeMockEnv();
    await mountWithCleanup(WebClient, { env });

    const firstBarcodeValue = "Odoo";
    const secondBarcodeValue = "OCDTEST";

    let barcodeToGenerate = firstBarcodeValue;
    let videoReady = new Deferred();

    function mockUserMedia() {
        const canvas = document.createElement("canvas");
        const ctx = canvas.getContext("2d");
        const stream = canvas.captureStream();

        const multiFormatWriter = new ZXing.MultiFormatWriter();
        const bitMatrix = multiFormatWriter.encode(
            barcodeToGenerate,
            ZXing.BarcodeFormat.QR_CODE,
            250,
            250,
            null
        );
        canvas.width = bitMatrix.width;
        canvas.height = bitMatrix.height;
        ctx.strokeStyle = "black";
        ctx.fillStyle = "white";
        ctx.fillRect(0, 0, canvas.width, canvas.height);
        for (let x = 0; x < bitMatrix.width; x++) {
            for (let y = 0; y < bitMatrix.height; y++) {
                if (bitMatrix.get(x, y)) {
                    ctx.beginPath();
                    ctx.rect(x, y, 1, 1);
                    ctx.stroke();
                }
            }
        }
        return stream;
    }
    // simulate an environment with a camera/webcam
    patchWithCleanup(browser.navigator, {
        mediaDevices: {
            getUserMedia: mockUserMedia,
        },
    });

    patchWithCleanup(BarcodeDialog.prototype, {
        async isVideoReady() {
            await super.isVideoReady(...arguments);
            videoReady.resolve();
        },
        onResize(overlayInfo) {
            expect.step(JSON.stringify(overlayInfo));
            return super.onResize(...arguments);
        },
    });

    const firstBarcodeFound = scanBarcode(env);
    await videoReady;
    await contains(".o_crop_icon").dragAndDrop(".o_crop_container", {
        relative: true,
        position: {
            x: 0,
            y: 0,
        },
    });

    const firstValueScanned = await firstBarcodeFound;
    expect(firstValueScanned).toBe(firstBarcodeValue, {
        message: `The detected barcode (${firstValueScanned}) should be the same as generated (${firstBarcodeValue})`,
    });

    // Do another scan barcode to the test position of the overlay saved in the locale storage
    // Reset all values for the second test
    barcodeToGenerate = secondBarcodeValue;
    videoReady = new Deferred();

    const secondBarcodeFound = scanBarcode(env);
    await videoReady;
    const secondValueScanned = await secondBarcodeFound;
    expect(secondValueScanned).toBe(secondBarcodeValue, {
        message: `The detected barcode (${secondValueScanned}) should be the same as generated (${secondBarcodeValue})`,
    });

    expect([
        JSON.stringify({ x: 25, y: 100, width: 200, height: 50 }),
        JSON.stringify({ x: 0, y: 0, width: 250, height: 250 }),
        JSON.stringify({ x: 0, y: 0, width: 250, height: 250 }),
    ]).toVerifySteps({
        message:
            "We should haves three resize event; one for the default position, another one for the all frame and the last one must be the same as the saved second position",
    });
});
