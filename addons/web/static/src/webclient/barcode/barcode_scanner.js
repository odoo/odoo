/** @odoo-module **/
/* global BarcodeDetector */

import { browser } from "@web/core/browser/browser";
import Dialog from "web.OwlDialog";
import { delay } from "web.concurrency";
import { loadJS, templates } from "@web/core/assets";
import { isVideoElementReady, buildZXingBarcodeDetector } from "./ZXingBarcodeDetector";
import { CropOverlay } from "./crop_overlay";

import {
    App,
    Component,
    EventBus,
    onMounted,
    onWillStart,
    onWillUnmount,
    useRef,
    useState,
} from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
const bus = new EventBus();
const busOk = "BarcodeDialog-Ok";
const busError = "BarcodeDialog-Error";

export class BarcodeDialog extends Component {
    /**
     * @override
     */
    setup() {
        this.videoPreviewRef = useRef("videoPreview");
        this.interval = null;
        this.stream = null;
        this.detector = null;
        this.overlayInfo = {};
        this.zoomRatio = 1;
        this.state = useState({
            isReady: false,
        });

        onWillStart(async () => {
            let DetectorClass;
            // Use Barcode Detection API if available.
            // As support is still bleeding edge (mainly Chrome on Android),
            // also provides a fallback using ZXing library.
            if ("BarcodeDetector" in window) {
                DetectorClass = BarcodeDetector;
            } else {
                await loadJS("/web/static/lib/zxing-library/zxing-library.js");
                DetectorClass = buildZXingBarcodeDetector(window.ZXing);
            }
            const formats = await DetectorClass.getSupportedFormats();
            this.detector = new DetectorClass({ formats });
        });

        onMounted(async () => {
            const constraints = {
                video: { facingMode: this.props.facingMode },
                audio: false,
            };

            try {
                this.stream = await browser.navigator.mediaDevices.getUserMedia(constraints);
            } catch (err) {
                const errors = {
                    NotFoundError: _t("No device can be found."),
                    NotAllowedError: _t("Odoo needs your authorization first."),
                };
                const errorMessage =
                    _t("Could not start scanning. ") + (errors[err.name] || err.message);
                this.onError(new Error(errorMessage));
                return;
            }
            this.videoPreviewRef.el.srcObject = this.stream;
            await this.isVideoReady();
            const { height, width } = getComputedStyle(this.videoPreviewRef.el);
            const divWidth = width.slice(0, -2);
            const divHeight = height.slice(0, -2);
            const tracks = this.stream.getVideoTracks();
            if (tracks.length) {
                const [track] = tracks;
                const settings = track.getSettings();
                this.zoomRatio = Math.min(divWidth / settings.width, divHeight / settings.height);
            }
            this.interval = setInterval(this.detectCode.bind(this), 100);
        });

        onWillUnmount(() => {
            clearInterval(this.interval);
            this.interval = null;
            if (this.stream) {
                this.stream.getTracks().forEach((track) => track.stop());
                this.stream = null;
            }
        });
    }

    isZXingBarcodeDetector() {
        return this.detector && this.detector.__proto__.constructor.name === "ZXingBarcodeDetector";
    }

    /**
     * Check for camera preview element readiness
     *
     * @returns {Promise} resolves when the video element is ready
     */
    async isVideoReady() {
        // FIXME: even if it shouldn't happened, a timeout could be useful here.
        return new Promise(async (resolve) => {
            while (!isVideoElementReady(this.videoPreviewRef.el)) {
                await delay(10);
            }
            this.state.isReady = true;
            resolve();
        });
    }

    onResize(overlayInfo) {
        this.overlayInfo = overlayInfo;
        if (this.isZXingBarcodeDetector()) {
            // TODO need refactoring when ZXing will support multiple result in one scan
            // https://github.com/zxing-js/library/issues/346
            this.detector.setCropArea(this.adaptValuesWithRatio(this.overlayInfo, true));
        }
    }

    /**
     * Detection success handler
     *
     * @param {string} result found code
     */
    onResult(result) {
        this.props.onClose();
        bus.trigger(busOk, result);
    }

    /**
     * Detection error handler
     *
     * @param {Error} error
     */
    onError(error) {
        this.props.onClose();
        bus.trigger(busError, { error });
    }

    /**
     * Attempt to detect codes in the current camera preview's frame
     */
    async detectCode() {
        try {
            const codes = await this.detector.detect(this.videoPreviewRef.el);
            for (const code of codes) {
                if (!this.isZXingBarcodeDetector() && this.overlayInfo.x && this.overlayInfo.y) {
                    const { x, y, width, height } = this.adaptValuesWithRatio(code.boundingBox);
                    if (
                        x < this.overlayInfo.x ||
                        x + width > this.overlayInfo.x + this.overlayInfo.width ||
                        y < this.overlayInfo.y ||
                        y + height > this.overlayInfo.y + this.overlayInfo.height
                    ) {
                        continue;
                    }
                }
                this.onResult(code.rawValue);
                break;
            }
        } catch (err) {
            this.onError(err);
        }
    }

    adaptValuesWithRatio(object, dividerRatio = false) {
        const newObject = Object.assign({}, object);
        for (const key of Object.keys(newObject)) {
            if (dividerRatio) {
                newObject[key] /= this.zoomRatio;
            } else {
                newObject[key] *= this.zoomRatio;
            }
        }
        return newObject;
    }
}

Object.assign(BarcodeDialog, {
    components: {
        Dialog,
        CropOverlay,
    },
    template: "web.BarcodeDialog",
});

/**
 * Check for BarcodeScanner support
 * @returns {boolean}
 */
export function isBarcodeScannerSupported() {
    return browser.navigator.mediaDevices && browser.navigator.mediaDevices.getUserMedia;
}

/**
 * Opens the BarcodeScanning dialog and begins code detection using the device's camera.
 *
 * @returns {Promise<string>} resolves when a {qr,bar}code has been detected
 */
export async function scanBarcode(facingMode = "environment") {
    const promise = new Promise((resolve, reject) => {
        bus.on(busOk, null, resolve);
        bus.on(busError, null, reject);
    });
    const appForBarcodeDialog = new App(BarcodeDialog, {
        env: owl.Component.env,
        dev: owl.Component.env.isDebug(),
        templates,
        translatableAttributes: ["data-tooltip"],
        translateFn: _t,
        props: {
            onClose: () => appForBarcodeDialog.destroy(),
            facingMode: facingMode,
        },
    });
    await appForBarcodeDialog.mount(document.body);
    return promise;
}
