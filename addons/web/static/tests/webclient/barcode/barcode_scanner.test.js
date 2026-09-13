// @ts-check

import { expect, test } from "@odoo/hoot";
import { animationFrame, click, press, waitFor } from "@odoo/hoot-dom";
import { advanceTime, Deferred } from "@odoo/hoot-mock";
import { Component, useState, xml } from "@odoo/owl";
import {
    contains,
    makeMockEnv,
    mountWebClient,
    mountWithCleanup,
    patchWithCleanup,
} from "@web/../tests/web_test_helpers";
import { scanBarcode } from "@web/components/barcode/barcode_dialog";
import { BarcodeVideoScanner } from "@web/components/barcode/barcode_video_scanner";
import { makeZXingBarcodeDetector } from "@web/components/barcode/ZXingBarcodeDetector";
import { browser } from "@web/core/browser/browser";

import * as ZXing from "zxing-library";

test("Barcode scanner crop overlay", async () => {
    const env = await makeMockEnv();
    await mountWebClient({ env });

    const firstBarcodeValue = "Odoo";
    const secondBarcodeValue = "OCDTEST";

    let barcodeToGenerate = firstBarcodeValue;
    let videoReady = new Deferred();

    async function mockUserMedia() {
        const canvas = document.createElement("canvas");
        const ctx = /** @type {CanvasRenderingContext2D} */ (canvas.getContext("2d"));
        const stream = canvas.captureStream();

        const multiFormatWriter = new ZXing.MultiFormatWriter();
        const bitMatrix = multiFormatWriter.encode(
            barcodeToGenerate,
            ZXing.BarcodeFormat.QR_CODE,
            250,
            250,
            null,
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
    patchWithCleanup(browser.navigator, {
        mediaDevices: /** @type {any} */ ({
            getUserMedia: mockUserMedia,
        }),
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
    async function mockUserMedia() {
        const canvas = document.createElement("canvas");
        const ctx = /** @type {CanvasRenderingContext2D} */ (canvas.getContext("2d"));
        const stream = canvas.captureStream();
        canvas.width = 250;
        canvas.height = 250;
        ctx.strokeStyle = "black";
        ctx.fillStyle = "white";
        ctx.fillRect(0, 0, canvas.width, canvas.height);
        return stream;
    }
    patchWithCleanup(browser.navigator, {
        mediaDevices: /** @type {any} */ ({
            getUserMedia: mockUserMedia,
        }),
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
    await mountWebClient({ env });
    const cameraReady = new Deferred();

    patchWithCleanup(browser.navigator, {
        mediaDevices: /** @type {any} */ ({
            async getUserMedia() {
                await cameraReady;
                const canvas = document.createElement("canvas");
                return canvas.captureStream();
            },
        }),
    });

    scanBarcode(env);

    await waitFor(".o-barcode-modal");
    expect(".o-barcode-modal").toHaveCount(1);

    await press("escape");

    await animationFrame();
    expect(".o-barcode-modal").toHaveCount(0);

    cameraReady.resolve();

    await animationFrame();
    expect(".o_error_dialog").toHaveCount(0);
});

test("Closing the barcode dialog manually resolves the scan promise with null", async () => {
    const env = await makeMockEnv();
    await mountWebClient({ env });

    patchWithCleanup(browser.navigator, {
        mediaDevices: /** @type {any} */ ({
            async getUserMedia() {
                const canvas = document.createElement("canvas");
                return canvas.captureStream();
            },
        }),
    });

    const escScan = scanBarcode(env);
    for (let i = 0; i < 6; i++) {
        console.error(
            "DBG frame",
            i,
            document.querySelectorAll(".modal").length,
            document.querySelectorAll(".o_home_menu").length,
            document.querySelectorAll(".o_action_manager > *").length,
        );
        await animationFrame();
    }
    await waitFor(".o-barcode-modal");
    expect(".o-barcode-modal").toHaveCount(1);

    await press("escape");

    await animationFrame();
    expect(".o-barcode-modal").toHaveCount(0);
    expect(await escScan).toBe(null);

    const closeButtonScan = scanBarcode(env);

    await waitFor(".o-barcode-modal");
    expect(".o-barcode-modal").toHaveCount(1);

    await click(".o-barcode-modal .modal-header button[aria-label='Close']");

    await animationFrame();
    expect(".o-barcode-modal").toHaveCount(0);
    expect(await closeButtonScan).toBe(null);
});

test("Closing barcode scanner while video is loading should not cause errors", async () => {
    const env = await makeMockEnv();
    await mountWebClient({ env });

    patchWithCleanup(browser.navigator, {
        mediaDevices: /** @type {any} */ ({
            async getUserMedia() {
                const canvas = document.createElement("canvas");
                return canvas.captureStream();
            },
        }),
    });

    scanBarcode(env);

    await waitFor(".o-barcode-modal");
    expect(".o-barcode-modal").toHaveCount(1);

    await press("escape");

    await animationFrame();
    expect(".o-barcode-modal").toHaveCount(0);

    await animationFrame();
    expect(".o_error_dialog").toHaveCount(0);
});

function mockBlankCamera() {
    patchWithCleanup(browser.navigator, {
        mediaDevices: /** @type {any} */ ({
            getUserMedia() {
                const canvas = document.createElement("canvas");
                canvas.width = 250;
                canvas.height = 250;
                const ctx = /** @type {CanvasRenderingContext2D} */ (
                    canvas.getContext("2d")
                );
                ctx.fillStyle = "white";
                ctx.fillRect(0, 0, canvas.width, canvas.height);
                return canvas.captureStream();
            },
        }),
    });
}

/** @param {() => any} onDetect */
function mockDetector(onDetect) {
    class ScriptedDetector {
        static async getSupportedFormats() {
            return ["qr_code"];
        }
        async detect() {
            return onDetect();
        }
    }
    patchWithCleanup(browser, { BarcodeDetector: ScriptedDetector });
}

async function mountScanner(/** @type {any} */ props) {
    const ready = new Deferred();
    await mountWithCleanup(BarcodeVideoScanner, {
        props: {
            facingMode: "environment",
            onReady: () => ready.resolve(),
            onResult: () => {},
            onError: () => {},
            ...props,
        },
    });
    await ready;
    return ready;
}

test("the scan loop gives up after five consecutive detector failures", async () => {
    mockBlankCamera();
    let attempts = 0;
    mockDetector(() => {
        attempts++;
        throw new Error("detector unavailable");
    });

    /** @type {any[]} */
    const errors = [];
    await mountScanner({ onError: (/** @type {any} */ e) => errors.push(e) });

    for (let i = 0; i < 8; i++) {
        await advanceTime(100);
    }
    expect(errors.length).toBe(1);
    expect(attempts).toBe(5);

    const settled = attempts;
    await advanceTime(500);
    expect(attempts).toBe(settled);
});

test("a successful read clears the failure count", async () => {
    mockBlankCamera();
    let attempts = 0;
    mockDetector(() => {
        attempts++;
        if (attempts === 5) {
            return [];
        }
        throw new Error("transient");
    });

    /** @type {any[]} */
    const errors = [];
    await mountScanner({ onError: (/** @type {any} */ e) => errors.push(e) });

    // Startup may schedule the first frame after the first clock advance.
    for (let i = 0; i < 12 && attempts < 9; i++) {
        await advanceTime(100);
    }
    expect(attempts).toBe(9);
    expect(errors).toEqual([]);
});

test("leaving while the camera is still starting releases it and reports nothing", async () => {
    /** @type {any[]} */
    const stopped = [];
    const track = {
        stop: () => stopped.push("stop"),
        getSettings: () => ({ width: 100, height: 100 }),
        getCapabilities: () => ({}),
    };
    const permissionPrompt = new Deferred();
    patchWithCleanup(browser.navigator, {
        mediaDevices: /** @type {any} */ ({ getUserMedia: () => permissionPrompt }),
    });
    mockDetector(() => []);

    /** @type {any[]} */
    const errors = [];
    /** @type {{ scanning: boolean }} */
    let hostState = { scanning: true };
    class Host extends Component {
        static props = ["*"];
        static components = { BarcodeVideoScanner };
        static template = xml`
            <t t-if="state.scanning">
                <BarcodeVideoScanner facingMode="'environment'"
                    onResult="() => {}" onError.bind="onError"/>
            </t>`;
        setup() {
            this.state = hostState = useState(hostState);
        }
        onError(/** @type {any} */ error) {
            errors.push(error.message);
        }
    }
    await mountWithCleanup(Host);

    hostState.scanning = false;
    await animationFrame();
    permissionPrompt.resolve({
        getTracks: () => [track],
        getVideoTracks: () => [track],
    });
    await animationFrame();
    await advanceTime(500);

    expect(errors).toEqual([]);
    expect(stopped).toEqual(["stop"]);
});

test("a crop window too small to hold a symbol falls back to the whole frame", async () => {
    /** @type {any[]} */
    const sources = [];
    const Detector = makeZXingBarcodeDetector(makeFakeZXing());
    const detector = /** @type {any} */ (new Detector({ formats: ["qr_code"] }));
    detector.ctx = {
        drawImage: (/** @type {any[]} */ ...a) => sources.push(a.slice(1, 5)),
    };
    const video = makeFakeVideo(640, 480);

    detector.setCropArea({ x: 320, y: 240, width: 0, height: 0 });
    await detector.detect(video);
    expect(sources.at(-1)).toEqual([0, 0, 640, 480]);

    detector.setCropArea({ x: 0, y: 0, width: 640, height: 480 });
    await detector.detect(video);
    expect(sources.at(-1)).toEqual([0, 0, 640, 480]);

    detector.setCropArea({ x: 100, y: 80, width: 400, height: 300 });
    await detector.detect(video);
    expect(sources.at(-1)).toEqual([100, 80, 400, 300]);
});

test("the bounding box spans every result point, not the first two", async () => {
    const points = [
        { x: 30, y: 200 },
        { x: 30, y: 40 },
        { x: 190, y: 40 },
    ];
    const Detector = makeZXingBarcodeDetector(
        makeFakeZXing({ resultPoints: points, text: "Odoo" }),
    );
    const detector = /** @type {any} */ (new Detector({ formats: ["qr_code"] }));
    detector.ctx = { drawImage: () => {} };

    const [{ boundingBox, rawValue }] = await detector.detect(makeFakeVideo(640, 480));
    expect(rawValue).toBe("Odoo");
    expect([
        boundingBox.x,
        boundingBox.y,
        boundingBox.width,
        boundingBox.height,
    ]).toEqual([30, 40, 160, 160]);
});

/** @param {{ resultPoints?: any[], text?: string }} [found] */
function makeFakeZXing(found) {
    return {
        BarcodeFormat: new Proxy({}, { get: (_t, k) => `fmt:${String(k)}` }),
        DecodeHintType: { POSSIBLE_FORMATS: 1, TRY_HARDER: 2 },
        MultiFormatReader: class {
            setHints() {}
            decodeWithState() {
                if (!found) {
                    const err = new Error("no symbol");
                    err.name = "NotFoundException";
                    throw err;
                }
                return {
                    resultPoints: found.resultPoints,
                    getText: () => found.text,
                    getBarcodeFormat: () => "fmt:QR_CODE",
                };
            }
        },
        HTMLCanvasElementLuminanceSource: class {},
        BinaryBitmap: class {},
        HybridBinarizer: class {},
    };
}

/**
 * @param {number} width
 * @param {number} height
 */
function makeFakeVideo(width, height) {
    const video = document.createElement("video");
    Object.defineProperty(video, "readyState", { value: 4 });
    Object.defineProperty(video, "videoWidth", { value: width });
    Object.defineProperty(video, "videoHeight", { value: height });
    return video;
}
