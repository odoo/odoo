import { BasePrinter } from "@point_of_sale/app/utils/printer/base_printer";
import { _t } from "@web/core/l10n/translation";
import { getTemplate } from "@web/core/templates";
import { createElement, append, createTextNode } from "@web/core/utils/xml";
import { getLNATargetAddressSpace } from "../init_lna";
import { getOnNotified } from "@point_of_sale/utils";
import { uuid } from "@web/core/utils/strings";

const STATUS_ROLL_PAPER_HAS_RUN_OUT = 0x00080000;
const STATUS_ROLL_PAPER_HAS_ALMOST_RUN_OUT = 0x00020000;
const ERROR_CODE_PRINTER_NOT_REACHABLE = "PRINTER_NOT_REACHABLE";

// Documentation: https://files.support.epson.com/pdf/pos/bulk/tm-int_sdp_um_e_reve.pdf
const EPSON_ERRORS = {
    EPTR_AUTOMATICAL: _t("Continuous printing of high-density printing caused a printing error."),
    EPTR_CUTTER: _t("The cutter has a foreign matter, please check the cutter mechanism."),
    EPTR_MECHANICAL: _t("Mechanical error, please check the printer."),
    EPTR_UNRECOVERABLE: _t("Low voltage unrecoverable error occurred, please check the printer."),
    EX_BADPORT: _t("The device is not connected, please check the printer power / connection."),
    EX_TIMEOUT: _t("Print timeout occurred, please try again."),
};

/**
 * We need to remove all `xmlns=""` in the DOM otherwise, the print
 * request will succeed but nothing will be printed
 */
function ePOSPrint(children, template, jobId) {
    let ePOSLayout = getTemplate(template);
    ePOSLayout = ePOSLayout.cloneNode(true);
    const [eposPrintEl] = ePOSLayout.getElementsByTagName("epos-print");
    append(eposPrintEl, children);
    if (jobId) {
        const [printJobId] = ePOSLayout.getElementsByTagName("printjobid");
        append(printJobId, jobId);
    }
    return ePOSLayout.innerHTML.replaceAll(`xmlns=""`, "");
}

/**
 * Transform a (potentially colored) canvas into a monochrome raster image.
 * We will use Floyd-Steinberg dithering.
 */
function canvasToRaster(canvas) {
    const {
        data: pixels,
        width,
        height,
    } = canvas.getContext("2d").getImageData(0, 0, canvas.width, canvas.height);
    const raster = new Uint8Array(Math.ceil((width * height) / 8));

    // Floyd-Steinberg only ever propagates error to the current and next
    // rows, so we only need to keep two rows of error terms around instead
    // of one for the whole image (which can get very tall for long receipts).
    let currentRowErrors = new Float32Array(width);
    let nextRowErrors = new Float32Array(width);

    for (let y = 0; y < height; y++) {
        for (let x = 0; x < width; x++) {
            const i = y * width + x;
            const idx = i * 4;

            // Compute grayscale level. Those coefficients were found online
            // as R, G and B have different impacts on the darkness
            // perception (e.g. pure blue is darker than red or green).
            let level = pixels[idx] * 0.299 + pixels[idx + 1] * 0.587 + pixels[idx + 2] * 0.114;

            // Propagate the error from neighbor pixels
            level = Math.min(255, Math.max(0, level + currentRowErrors[x]));

            const isBlack = level < 128;
            if (isBlack) {
                // This pixel should be black
                raster[i >> 3] |= 0x80 >> i % 8;
            }

            const error = level - (isBlack ? 0 : 255);
            if (!error) {
                continue;
            }

            // Propagate the error to the following pixels, based on
            // Floyd-Steinberg dithering.
            if (x + 1 < width) {
                // Pixel on the right
                currentRowErrors[x + 1] += (7 / 16) * error;
            }
            if (x > 0) {
                // Pixel on the bottom left
                nextRowErrors[x - 1] += (3 / 16) * error;
            }
            // Pixel below
            nextRowErrors[x] += (5 / 16) * error;
            if (x + 1 < width) {
                // Pixel on the bottom right
                nextRowErrors[x + 1] += (1 / 16) * error;
            }
        }

        [currentRowErrors, nextRowErrors] = [nextRowErrors, currentRowErrors];
        nextRowErrors.fill(0);
    }

    return raster;
}

/**
 * Create the raster data from a canvas
 */
export function processCanvas(canvas, template = "point_of_sale.ePOSLayout", jobId) {
    const encodedData = canvasToRaster(canvas).toBase64();
    return ePOSPrint(
        [
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
        ],
        template,
        jobId
    );
}

/**
 * Sends print request to ePos printer that is directly connected to the local network.
 */
export class EpsonPrinter extends BasePrinter {
    setup({ printer }) {
        super.setup(...arguments);
        this.printer_ip = printer.printer_ip;
        if (this.use_lna) {
            this.lnaTargetAddressSpace = getLNATargetAddressSpace(this.address);
        }
        this.timeout = printer.timeout || 15000;
    }

    get address() {
        const protocol = this.use_lna ? "http:" : "https:";
        return `${protocol}//${this.printer_ip}/cgi-bin/epos/service.cgi?devid=local_printer&timeout=${this.timeout}`;
    }

    get STYLE_MAPPING() {
        const base = super.STYLE_MAPPING;
        return {
            ...base,
            tm_u22_76: { maxWidth: 200, fontSize: 12 },
            tm_u22_70: { maxWidth: 180, fontSize: 12 },
            tm_u22_58: { maxWidth: 150, fontSize: 12 },
            tm_u33_76: { maxWidth: 400, fontSize: 22 },
            tm_u33_70: { maxWidth: 380, fontSize: 22 },
            tm_p60_60: { maxWidth: 375, fontSize: 22 },
            tm_l100_40: { maxWidth: 240, fontSize: 14 },
        };
    }

    openCashbox() {
        const pulse = ePOSPrint([createElement("pulse")]);
        this.sendPrintingJob(pulse);
    }

    prepareImage(img, template, jobId) {
        return img instanceof HTMLCanvasElement ? processCanvas(img, template, jobId) : img;
    }

    /**
     * @override
     */
    async sendPrintingJob(img) {
        const processed = this.prepareImage(img, "point_of_sale.ePOSLayout");

        const params = {
            method: "POST",
            body: processed,
            signal: AbortSignal.timeout(this.timeout),
        };

        if (this.use_lna) {
            params.targetAddressSpace = this.lnaTargetAddressSpace;
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
        return (status & attribute) === attribute;
    }

    /**
     * @override
     */
    getResultsError(printResult) {
        const errorCode = printResult.errorCode;
        const status = printResult.status;
        const hasStatus = this.hasStatus(status, STATUS_ROLL_PAPER_HAS_RUN_OUT);
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
        } else if (errorCode === "EPTR_REC_EMPTY" || hasStatus) {
            message = _t("It seems that the printer runs out of paper.");
        } else if (errorCode in EPSON_ERRORS) {
            message = EPSON_ERRORS[errorCode];
        } else {
            message = _t(
                "The following error code was given by the printer: %s \nTo find more details on the error reason, please search online for: Epson ePoS error %s ",
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

export class PollingPrinter extends EpsonPrinter {
    // Documentation: https://files.support.epson.com/pdf/pos/bulk/tm-int_sdp_um_e_reve.pdf
    setup({ printer, posData, bus }) {
        super.setup(...arguments);
        this.posData = posData;
        this.pendingPrintJobs = new Map();
        getOnNotified(bus, "POLLING_PRINTER");
        posData.connectWebSocket("POLLING_PRINTER", this.pollingPrinterNotification.bind(this));
    }

    pollingPrinterNotification(response) {
        if (response.some((r) => !r.printJobId)) {
            for (const [printJobId, resolve] of this.pendingPrintJobs) {
                resolve({ success: "false", errorCode: "ERROR_CODE_PRINTER_OLD_FIRMWARE" });
                this.pendingPrintJobs.delete(printJobId);
            }
            return;
        }
        for (const jobResult of response) {
            const resolve = this.pendingPrintJobs.get(jobResult.printJobId);
            if (resolve) {
                resolve(jobResult);
                this.pendingPrintJobs.delete(jobResult.printJobId);
            }
        }
    }

    async sendPrintingJob(img) {
        const printJobId = uuid();
        const processed = this.prepareImage(img, "point_of_sale.PollingPrinterLayout", printJobId);

        const { promise: printerResponsePromise, resolve: resolvePrinterResponse } =
            Promise.withResolvers();
        this.pendingPrintJobs.set(printJobId, resolvePrinterResponse);
        const fallbackTimeout = setTimeout(() => {
            this.pendingPrintJobs.delete(printJobId);
            resolvePrinterResponse({ result: false, errorCode: ERROR_CODE_PRINTER_NOT_REACHABLE });
        }, this.timeout);

        try {
            await this.posData.orm.call("pos.printer", "push_polling_printer_receipt", [
                this.id,
                processed,
            ]);
            const printerResponse = await printerResponsePromise;
            return {
                result: printerResponse.success === "true" && !printerResponse.errorCode,
                errorCode: printerResponse.errorCode,
                canRetry: true,
            };
        } catch {
            return {
                result: false,
                errorCode: "ERROR_CODE_REQUEST_BACKEND",
                canRetry: true,
            };
        } finally {
            clearTimeout(fallbackTimeout);
            this.pendingPrintJobs.delete(printJobId);
        }
    }
}
