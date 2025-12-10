import { BasePrinter } from "@point_of_sale/app/utils/printer/base_printer";
import { _t } from "@web/core/l10n/translation";
import { getTemplate } from "@web/core/templates";
import { createElement, append, createTextNode } from "@web/core/utils/xml";

const STATUS_ROLL_PAPER_HAS_RUN_OUT = 0x00080000;
const STATUS_ROLL_PAPER_HAS_ALMOST_RUN_OUT = 0x00020000;
const ERROR_CODE_PRINTER_NOT_REACHABLE = "PRINTER_NOT_REACHABLE";

function ePOSPrint(children) {
    let ePOSLayout = getTemplate("point_of_sale.ePOSLayout");
    if (!ePOSLayout) {
        throw new Error("'ePOSLayout' not loaded");
    }
    ePOSLayout = ePOSLayout.cloneNode(true);
    const [eposPrintEl] = ePOSLayout.getElementsByTagName("epos-print");
    append(eposPrintEl, children);
    // IMPORTANT: Need to remove `xmlns=""` in the image and cut elements.
    // > Otherwise, the print request will succeed but it the printer device won't actually do the printing.
    return ePOSLayout.innerHTML.replaceAll(`xmlns=""`, "");
}

/**
 * Sends print request to ePos printer that is directly connected to the local network.
 */
export class EpsonPrinter extends BasePrinter {
    setup({ ip }) {
        super.setup(...arguments);

        const protocol = odoo.use_lna ? "http:" : window.location.protocol;
        this.url = protocol + "//" + ip;
        this.address = this.url + "/cgi-bin/epos/service.cgi?devid=local_printer";
    }

    /**
     * @override
     * Create the raster data from a canvas
     */
    processCanvas(canvas) {
        const rasterData = this.canvasToRaster(canvas);
        const encodedData = this.encodeRaster(rasterData);
        return ePOSPrint([
            createElement(
                "image",
                {
                    width: canvas.width,
                    height: canvas.height,
                    align: "center",
                },
                [createTextNode(encodedData)]
            ),
            createElement("cut", { type: "feed" }),
        ]);
    }

    /**
     * @override
     */
    openCashbox() {
        const pulse = ePOSPrint([createElement("pulse")]);
        this.sendPrintingJob(pulse);
    }

    /**
     * @override
     */
    async sendPrintingJob(img) {
        const params = {
            method: "POST",
            body: img,
            signal: AbortSignal.timeout(15000),
        };

        if (odoo.use_lna) {
            params.targetAddressSpace = "local";
        }

        try {
            const res = await fetch(this.address, params);
            const body = await res.text();
            const parser = new DOMParser();
            const parsedBody = parser.parseFromString(body, "application/xml");
            const response = parsedBody.querySelector("response");
            return {
                result: response.getAttribute("success") === "true",
                errorCode: response.getAttribute("code"),
                status: parseInt(response.getAttribute("status")) || 0,
                canRetry: true,
            };
        } catch {
            return {
                result: false,
                canRetry: true,
                errorCode: ERROR_CODE_PRINTER_NOT_REACHABLE,
            };
        }
    }

    /**
     * Transform a (potentially colored) canvas into a monochrome raster image.
     * We will use Floyd-Steinberg dithering.
     */
    canvasToRaster(canvas) {
        const imageData = canvas.getContext("2d").getImageData(0, 0, canvas.width, canvas.height);
        const pixels = imageData.data;
        const width = imageData.width;
        const height = imageData.height;
        const errors = Array.from(Array(width), (_) => Array(height).fill(0));
        const rasterData = new Array(width * height).fill(0);

        for (let y = 0; y < height; y++) {
            for (let x = 0; x < width; x++) {
                let oldColor, newColor;

                // Compute grayscale level. Those coefficients were found online
                // as R, G and B have different impacts on the darkness
                // perception (e.g. pure blue is darker than red or green).
                const idx = (y * width + x) * 4;
                oldColor = pixels[idx] * 0.299 + pixels[idx + 1] * 0.587 + pixels[idx + 2] * 0.114;

                // Propagate the error from neighbor pixels
                oldColor += errors[x][y];
                oldColor = Math.min(255, Math.max(0, oldColor));

                if (oldColor < 128) {
                    // This pixel should be black
                    newColor = 0;
                    rasterData[y * width + x] = 1;
                } else {
                    // This pixel should be white
                    newColor = 255;
                    rasterData[y * width + x] = 0;
                }

                // Propagate the error to the following pixels, based on
                // Floyd-Steinberg dithering.
                const error = oldColor - newColor;
                if (error) {
                    if (x < width - 1) {
                        // Pixel on the right
                        errors[x + 1][y] += (7 / 16) * error;
                    }
                    if (x > 0 && y < height - 1) {
                        // Pixel on the bottom left
                        errors[x - 1][y + 1] += (3 / 16) * error;
                    }
                    if (y < height - 1) {
                        // Pixel below
                        errors[x][y + 1] += (5 / 16) * error;
                    }
                    if (x < width - 1 && y < height - 1) {
                        // Pixel on the bottom right
                        errors[x + 1][y + 1] += (1 / 16) * error;
                    }
                }
            }
        }

        return rasterData.join("");
    }

    /**
     * Base 64 encode a raster image
     */
    encodeRaster(rasterData) {
        let encodedData = "";
        for (let i = 0; i < rasterData.length; i += 8) {
            const sub = rasterData.substr(i, 8);
            encodedData += String.fromCharCode(parseInt(sub, 2));
        }
        return btoa(encodedData);
    }

    /**
     * @override
     */
    getActionError() {
        const printRes = super.getResultsError();
        if (window.location.protocol === "https:") {
            printRes.message.body += _t(
                "If you are on a secure server (HTTPS) please make sure you manually accepted the certificate by accessing %s. ",
                this.url
            );
        }
        return printRes;
    }

    hasStatus(status, attribute) {
        //The status is a bit field
        return (status & attribute) === attribute;
    }

    /**
     * @override
     */
    getResultsError(printResult) {
        const errorCode = printResult.errorCode;
        const status = printResult.status;
        let message;
        // https://download4.epson.biz/sec_pubs/pos/reference_en/epos_print/ref_epos_print_xml_en_xmlforcontrollingprinter_response.html
        if (errorCode === "DeviceNotFound") {
            message = _t(
                "Check the printer configuration for the 'Device ID' setting.\nIt should be set to: local_printer"
            );
        } else if (errorCode === ERROR_CODE_PRINTER_NOT_REACHABLE) {
            message = _t("The printer is not reachable.");
        } else if (errorCode === "EPTR_COVER_OPEN") {
            message = _t("Printer cover is open. Please close it and try again!");
        } else if (
            errorCode === "EPTR_REC_EMPTY" ||
            this.hasStatus(status, STATUS_ROLL_PAPER_HAS_RUN_OUT)
        ) {
            message = _t("It seems that the printer runs out of paper.");
        } else {
            message = _t(
                "The following error code was given by the printer: %s \nTo find more details on the error reason, please search online for: Epson Server Direct Print %s ",
                errorCode,
                errorCode
            );
        }
        return {
            successful: false,
            errorCode: errorCode,
            status: status,
            message: {
                title: _t("Printing failed"),
                body: message,
            },
            canRetry: printResult.canRetry || false,
        };
    }

    getResultWarningCode(printResult) {
        const status = printResult?.status;
        if (!status) {
            return undefined;
        }
        if (this.hasStatus(status, STATUS_ROLL_PAPER_HAS_ALMOST_RUN_OUT)) {
            return "ROLL_PAPER_HAS_ALMOST_RUN_OUT";
        }
        return undefined;
    }
}
