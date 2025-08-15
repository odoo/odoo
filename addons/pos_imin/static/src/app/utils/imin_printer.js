import { BasePrinter } from "@point_of_sale/app/utils/printer/base_printer";
import { _t } from "@web/core/l10n/translation";

/* global IminPrinter */
export class IminPrinterAdapter extends BasePrinter {
    setup() {
        super.setup(...arguments);
        this.iminPrinter = new IminPrinter();
        (async () => {
            if (await this.isAvailable) {
                this.printerConnPromise = this.iminPrinter.connect();
            }
        })();
    }

    get isAvailable() {
        return new Promise((resolve) => {
            const Socket = window.WebSocket || window.MozWebSocket;
            try {
                const ws = new Socket(
                    this.iminPrinter.protocol +
                        this.iminPrinter.address +
                        ":" +
                        this.iminPrinter.port +
                        this.iminPrinter.prefix
                );
                ws.onopen = function () {
                    ws.close();
                    resolve(true);
                };
                ws.onerror = function () {
                    resolve(false);
                };
            } catch (e) {
                console.error("Error checking printer availability:", e);
                resolve(false);
            }
        });
    }

    get printerStatus() {
        return (async () => {
            await this.printerConnPromise;
            return this.iminPrinter.getPrinterStatus();
        })();
    }

    /**
     * @override
     */
    processCanvas(canvas) {
        return canvas.toDataURL("image/jpeg");
    }

    /**
     * @override
     */
    async sendPrintingJob(img) {
        try {
            const status = await this.printerStatus;
            if (status.value !== 0) {
                return { successful: false, errorCode: status.value };
            }
            await this.iminPrinter.printSingleBitmap(img);
            this.iminPrinter.printAndLineFeed();
            this.iminPrinter.printAndLineFeed();
            this.iminPrinter.printAndLineFeed();
            return { successful: true };
        } catch (error) {
            console.error("Printing job failed:", error);
            return { successful: false, errorCode: error.message, canRetry: true };
        }
    }

    /**
     * @override
     */
    openCashbox() {
        return (async () => {
            await this.printerConnPromise; // Ensure the printer is connected
            this.iminPrinter.openCashBox();
        })();
    }

    /**
     * @override
     */
    getResultsError(printResult) {
        const errorCode = printResult.errorCode;
        // https://oss-sg.imin.sg/docs/en/JSPrinterSDK.html
        let message;
        switch (errorCode) {
            case -1:
            case 1:
                message = _t("The printer is not connected or powered on");
                break;
            case 3:
                message = _t("Print head open");
                break;
            case 7:
                message = _t("No paper feed");
                break;
            case 8:
                message = _t("Paper running out");
                break;
            case 99:
            default:
                message = _t("An unknown error occurred: %s", errorCode);
                break;
        }
        return {
            successful: false,
            errorCode: errorCode,
            message: {
                title: _t("Printing failed"),
                body: message,
            },
            canRetry: printResult.canRetry || false,
        };
    }
}
