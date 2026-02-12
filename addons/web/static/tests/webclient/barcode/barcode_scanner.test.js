import { expect, test } from "@odoo/hoot";
import { animationFrame, press } from "@odoo/hoot-dom";
import { Deferred } from "@odoo/hoot-mock";
import {
    contains,
    makeMockEnv,
    mountWithCleanup,
    patchWithCleanup,
} from "@web/../tests/web_test_helpers";

import { browser } from "@web/core/browser/browser";
import { scanBarcode } from "@web/core/barcode/barcode_dialog";
import { BarcodeVideoScanner } from "@web/core/barcode/barcode_video_scanner";
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

    patchWithCleanup(BarcodeVideoScanner.prototype, {
        async isVideoReady() {
            const result = await super.isVideoReady(...arguments);
            videoReady.resolve();
            return result;
        },
        onResize(overlayInfo) {
            expect.step(overlayInfo);
            return super.onResize(...arguments);
        },
    });

    const firstBarcodeFound = scanBarcode(env);
    await videoReady;
    await animationFrame();
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
    await animationFrame();
    const secondValueScanned = await secondBarcodeFound;
    expect(secondValueScanned).toBe(secondBarcodeValue, {
        message: `The detected barcode (${secondValueScanned}) should be the same as generated (${secondBarcodeValue})`,
    });

    expect.verifySteps([
        { x: 25, y: 100, width: 200, height: 50 },
        { x: 0, y: 0, width: 250, height: 250 },
        { x: 0, y: 0, width: 250, height: 250 },
    ]);
});

test("BarcodeVideoScanner onReady props", async () => {
    function mockUserMedia() {
        const canvas = document.createElement("canvas");
        const ctx = canvas.getContext("2d");
        const stream = canvas.captureStream();
        canvas.width = 250;
        canvas.height = 250;
        ctx.strokeStyle = "black";
        ctx.fillStyle = "white";
        ctx.fillRect(0, 0, canvas.width, canvas.height);
        return stream;
    }
    // Simulate an environment with a camera/webcam.
    patchWithCleanup(browser.navigator, {
        mediaDevices: {
            getUserMedia: mockUserMedia,
        },
    });
    const resolvedOnReadyPromise = new Promise((resolve) => {
        mountWithCleanup(BarcodeVideoScanner, {
            props: {
                facingMode: "environment",
                onReady: () => resolve(true),
                onResult: () => {},
                onError: () => {},
            },
        });
    });
    expect(await resolvedOnReadyPromise).toBe(true);
});

test("Closing barcode scanner before camera loads should not throw an error", async () => {
    const env = await makeMockEnv();
    await mountWithCleanup(WebClient, { env });
    const cameraReady = new Deferred();

    patchWithCleanup(browser.navigator, {
        mediaDevices: {
            async getUserMedia() {
                await cameraReady;
                const canvas = document.createElement("canvas");
                return canvas.captureStream();
            },
        },
    });

    scanBarcode(env);

    await animationFrame();
    expect(".o-barcode-modal").toHaveCount(1)

    await press("escape");

    await animationFrame();
    expect(".o-barcode-modal").toHaveCount(0)

    cameraReady.resolve();

    await animationFrame()
    expect(".o_error_dialog").toHaveCount(0)
});

test("Closing barcode scanner while video is loading should not cause errors", async () => {
    const env = await makeMockEnv();
    await mountWithCleanup(WebClient, { env });

    patchWithCleanup(browser.navigator, {
        mediaDevices: {
            async getUserMedia() {
                const canvas = document.createElement("canvas");
                return canvas.captureStream();
            },
        },
    });

    scanBarcode(env);

    await animationFrame();
    expect(".o-barcode-modal").toHaveCount(1)

    await press("escape");

    await animationFrame();
    expect(".o-barcode-modal").toHaveCount(0)

    await animationFrame()
    expect(".o_error_dialog").toHaveCount(0)
});
