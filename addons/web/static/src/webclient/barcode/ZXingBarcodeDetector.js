/** @odoo-module **/

/**
 * Builder for BarcodeDetector-like polyfill class using ZXing library.
 *
 * @param {ZXing} ZXing Zxing library
 * @returns {class} ZxingBarcodeDetector class
 */
export function buildZXingBarcodeDetector(ZXing) {
    const ZXingFormats = new Map([
        ["aztec", ZXing.BarcodeFormat.AZTEC],
        ["code_39", ZXing.BarcodeFormat.CODE_39],
        ["code_128", ZXing.BarcodeFormat.CODE_128],
        ["data_matrix", ZXing.BarcodeFormat.DATA_MATRIX],
        ["ean_8", ZXing.BarcodeFormat.EAN_8],
        ["ean_13", ZXing.BarcodeFormat.EAN_13],
        ["itf", ZXing.BarcodeFormat.ITF],
        ["pdf417", ZXing.BarcodeFormat.PDF_417],
        ["qr_code", ZXing.BarcodeFormat.QR_CODE],
        ["upc_a", ZXing.BarcodeFormat.UPC_A],
        ["upc_e", ZXing.BarcodeFormat.UPC_E],
    ]);

    const allSupportedFormats = Array.from(ZXingFormats.keys());

    /**
     * ZXingBarcodeDetector class
     *
     * BarcodeDetector-like polyfill class using ZXing library.
     * API follows the Shape Detection Web API (specifically Barcode Detection).
     */
    class ZXingBarcodeDetector {
        /**
         * @param {object} opts
         * @param {Array} opts.formats list of codes' formats to detect
         */
        constructor(opts = {}) {
            const formats = opts.formats || allSupportedFormats;
            const hints = new Map([
                [
                    ZXing.DecodeHintType.POSSIBLE_FORMATS,
                    formats.map((format) => ZXingFormats.get(format)),
                ],
                // Enable Scanning at 90 degrees rotation
                // https://github.com/zxing-js/library/issues/291
                [ZXing.DecodeHintType.TRY_HARDER, true],
            ]);
            this.reader = new ZXing.MultiFormatReader();
            this.reader.setHints(hints);
        }

        /**
         * Detect codes in image.
         *
         * @param {HTMLVideoElement} video source video element
         * @returns {Promise<Array>} array of detected codes
         */
        async detect(video) {
            if (!(video instanceof HTMLVideoElement)) {
                throw new DOMException(
                    "imageDataFrom() requires an HTMLVideoElement",
                    "InvalidArgumentError"
                );
            }
            if (!isVideoElementReady(video)) {
                throw new DOMException("HTMLVideoElement is not ready", "InvalidStateError");
            }
            const canvas = document.createElement("canvas");

            let barcodeArea;
            if (this.cropArea && (this.cropArea.x || this.cropArea.y)) {
                barcodeArea = this.cropArea;
            } else {
                barcodeArea = {
                    x: 0,
                    y: 0,
                    width: video.videoWidth,
                    height: video.videoHeight,
                };
            }
            canvas.width = barcodeArea.width;
            canvas.height = barcodeArea.height;

            const ctx = canvas.getContext("2d");

            ctx.drawImage(
                video,
                barcodeArea.x,
                barcodeArea.y,
                barcodeArea.width,
                barcodeArea.height,
                0,
                0,
                barcodeArea.width,
                barcodeArea.height
            );

            const luminanceSource = new ZXing.HTMLCanvasElementLuminanceSource(canvas);
            const binaryBitmap = new ZXing.BinaryBitmap(new ZXing.HybridBinarizer(luminanceSource));
            try {
                const result = this.reader.decode(binaryBitmap);
                const { resultPoints } = result;
                const boundingBox = DOMRectReadOnly.fromRect({
                    x: resultPoints[0].x,
                    y: resultPoints[0].y,
                    height: Math.max(1, Math.abs(resultPoints[1].y - resultPoints[0].y)),
                    width: Math.max(1, Math.abs(resultPoints[1].x - resultPoints[0].x)),
                });
                const cornerPoints = resultPoints;
                const format = Array.from(ZXingFormats).find(
                    ([k, val]) => val === result.getBarcodeFormat()
                );
                const rawValue = result.getText();
                return [
                    {
                        boundingBox,
                        cornerPoints,
                        format,
                        rawValue,
                    },
                ];
            } catch (err) {
                if (err.name === "NotFoundException") {
                    return [];
                }
                throw err;
            }
        }

        setCropArea(cropArea) {
            this.cropArea = cropArea;
        }
    }

    /**
     * Supported codes formats
     *
     * @static
     * @returns {Promise<string[]>}
     */
    ZXingBarcodeDetector.getSupportedFormats = async () => allSupportedFormats;

    return ZXingBarcodeDetector;
}

/**
 * Check for HTMLVideoElement readiness.
 *
 * See https://developer.mozilla.org/en-US/docs/Web/API/HTMLMediaElement/readyState
 */
const HAVE_NOTHING = 0;
const HAVE_METADATA = 1;
export function isVideoElementReady(video) {
    return ![HAVE_NOTHING, HAVE_METADATA].includes(video.readyState);
}
