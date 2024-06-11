/** @odoo-module **/
/* global ZXing */

import { browser } from "@web/core/browser/browser";
import {
    makeDeferred,
    nextTick,
    patchWithCleanup,
    triggerEvent,
} from "@web/../tests/helpers/utils";
import { registry } from "@web/core/registry";
import { uiService } from "@web/core/ui/ui_service";
import { hotkeyService } from "@web/core/hotkeys/hotkey_service";

import { scanBarcode, BarcodeDialog } from "@web/webclient/barcode/barcode_scanner";
import { createWebClient } from "@web/../tests/webclient/helpers";
import { dialogService } from "@web/core/dialog/dialog_service";
import { overlayService } from "@web/core/overlay/overlay_service";

QUnit.module("Barcode scanner", {});

QUnit.test("Barcode scanner crop overlay", async (assert) => {
    registry.category("services").add("ui", uiService);
    registry.category("services").add("hotkey", hotkeyService);
    registry.category("services").add("dialog", dialogService);
    registry.category("services").add("overlay", overlayService);

    const { env } = await createWebClient({});
    const firstBarcodeValue = "Odoo";
    const secondBarcodeValue = "O-CMD-TEST";

    let barcodeToGenerate = firstBarcodeValue;
    let videoReady = makeDeferred();

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
    patchWithCleanup(
        browser,
        Object.assign({}, browser, {
            navigator: {
                mediaDevices: {
                    getUserMedia: mockUserMedia,
                },
            },
        })
    );

    patchWithCleanup(BarcodeDialog.prototype, {
        async isVideoReady() {
            return super.isVideoReady(...arguments).then(() => {
                videoReady.resolve();
            });
        },
        onResize(overlayInfo) {
            assert.step(JSON.stringify(overlayInfo));
            return super.onResize(...arguments);
        },
    });

    const firstBarcodeFound = scanBarcode(env);
    await videoReady;
    // Needed due to the change on the props in the Crop component
    await nextTick();
    const cropIconSelector = ".o_crop_icon";
    const cropIcon = document.querySelector(cropIconSelector);
    const cropOverlay = document.querySelector(".o_crop_overlay");
    const cropContainer = document.querySelector(".o_crop_container");
    const cropIconPosition = cropIcon.getBoundingClientRect();
    const cropOverlayPosition = cropOverlay.getBoundingClientRect();
    await triggerEvent(cropContainer, cropIconSelector, "touchstart", {
        touches: [
            {
                identifier: 0,
                clientX: cropIconPosition.x + cropIconPosition.width / 2,
                clientY: cropIconPosition.y + cropIconPosition.height / 2,
                target: cropIcon,
            },
        ],
    });
    await triggerEvent(cropContainer, cropIconSelector, "touchmove", {
        touches: [
            {
                identifier: 0,
                clientX: cropOverlayPosition.right,
                clientY: cropOverlayPosition.bottom,
                target: cropIcon,
            },
        ],
    });
    await triggerEvent(cropContainer, cropIconSelector, "touchend", {});
    const firstValueScanned = await firstBarcodeFound;
    assert.strictEqual(
        firstValueScanned,
        firstBarcodeValue,
        `The detected barcode should be the same as generated (${firstBarcodeValue})`
    );

    // Do another scan barcode to the test position of the overlay saved in the locale storage
    // Reset all values for the second test
    barcodeToGenerate = secondBarcodeValue;
    videoReady = makeDeferred();

    const secondBarcodeFound = scanBarcode(env);
    await videoReady;
    const secondValueScanned = await secondBarcodeFound;
    assert.strictEqual(
        secondValueScanned,
        secondBarcodeValue,
        `The detected barcode should be the same as generated (${secondBarcodeValue})`
    );

    assert.verifySteps(
        [
            JSON.stringify({ x: 25, y: 100, width: 200, height: 50 }),
            JSON.stringify({ x: 0, y: 0, width: 250, height: 250 }),
            JSON.stringify({ x: 0, y: 0, width: 250, height: 250 }),
        ],
        "We should haves three resize event; one for the default position, another one for the all frame and the last one must be the same as the saved second position"
    );
});
