/* global BarcodeDetector */

import { browser } from "@web/core/browser/browser";
import { delay } from "@web/core/utils/concurrency";
import { loadJS } from "@web/core/assets";
import { isVideoElementReady, buildZXingBarcodeDetector } from "./ZXingBarcodeDetector";
import { CropOverlay } from "./crop_overlay";
import { Component, onMounted, onWillStart, onWillUnmount, useRef, useState } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";

export class BarcodeVideoScanner extends Component {
    static template = "web.BarcodeVideoScanner";
    static components = {
        CropOverlay,
    };
    static props = {
        cssClass: { type: String, optional: true },
        facingMode: {
            type: String,
            validate: (fm) => ["environment", "left", "right", "user"].includes(fm),
        },
        close: { type: Function, optional: true },
        onResult: Function,
        onError: Function,
        delayBetweenScan: { type: Number, optional: true },
    };
    static defaultProps = {
        cssClass: "w-100 h-100",
    };
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
        this.scanPaused = false;
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
                this.props.onError(new Error(errorMessage));
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
        while (!isVideoElementReady(this.videoPreviewRef.el)) {
            await delay(10);
        }
        this.state.isReady = true;
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
     * Attempt to detect codes in the current camera preview's frame
     */
    async detectCode() {
        if (this.scanPaused) {
            return;
        }
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
                this.barcodeDetected(code.rawValue);
                break;
            }
        } catch (err) {
            this.props.onError(err);
        }
    }

    barcodeDetected(barcode) {
        if (this.props.delayBetweenScan && !this.scanPaused) {
            this.scanPaused = true;
            setTimeout(() => {
                this.scanPaused = false;
            }, this.props.delayBetweenScan);
        }
        this.props.onResult(barcode);
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

/**
 * Check for BarcodeScanner support
 * @returns {boolean}
 */
export function isBarcodeScannerSupported() {
    return Boolean(browser.navigator.mediaDevices && browser.navigator.mediaDevices.getUserMedia);
}
