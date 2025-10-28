import { BasePrinter } from "@point_of_sale/app/utils/printer/base_printer";
import { logPosMessage } from "@point_of_sale/app/utils/pretty_console_log";
import { _t } from "@web/core/l10n/translation";

const CONSOLE_COLOR = "#28ffeb";

/* global IminPrinter */
export class IminPrinterAdapter extends BasePrinter {
    setup({ fallbackPrinter } = {}) {
        super.setup(...arguments);
        this.fallbackPrinter = fallbackPrinter;
        this.iminPrinter = new IminPrinter();
        this.isConnected = false;
    }

    async connect() {
        this.isConnected = await this.iminPrinter.connect();
    }

    async isAvailable() {
        return new Promise((resolve) => {
            try {
                const ws = new window.WebSocket(
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
            } catch (error) {
                logPosMessage(
                    "IminPrinterAdapter",
                    "isAvailable",
                    "Error checking printer availability: " + error.message,
                    CONSOLE_COLOR,
                    [error]
                );
                resolve(false);
            }
        });
    }

    async printerStatus() {
        if (!this.isConnected) {
            return { value: -1 };
        }
        try {
            return await this.iminPrinter.getPrinterStatus();
        } catch (error) {
            logPosMessage(
                "IminPrinterAdapter",
                "printerStatus",
                "Failed to get printer status: " + error.message,
                CONSOLE_COLOR,
                [error]
            );
            return { value: -1 };
        }
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
    async printReceipt(receipt) {
        const status = await this.printerStatus();
        // We only use the fallback printer if the printer is not connected or not powered on
        if ([-1, 1].includes(status.value) && this.fallbackPrinter) {
            return await this.fallbackPrinter.printReceipt(receipt);
        }
        return await super.printReceipt(receipt);
    }

    /**
     * @override
     */
    async sendPrintingJob(img) {
        try {
            const status = await this.printerStatus();
            if (status.value !== 0) {
                return { result: false, errorCode: status.value, canRetry: true };
            }
            await this.iminPrinter.printSingleBitmap(img);
            this.iminPrinter.printAndLineFeed();
            this.iminPrinter.printAndLineFeed();
            this.iminPrinter.printAndLineFeed();
            return { result: true };
        } catch (error) {
            logPosMessage(
                "IminPrinterAdapter",
                "sendPrintingJob",
                "Printing job failed: " + error.message,
                CONSOLE_COLOR,
                [error]
            );
            return { result: false, errorCode: error.message, canRetry: true };
        }
    }

    /**
     * @override
     */
    openCashbox() {
        if (!this.isConnected) {
            return;
        }
        try {
            this.iminPrinter.openCashBox();
        } catch (error) {
            // Avoid throwing an error when opening the cashbox
            logPosMessage(
                "IminPrinterAdapter",
                "openCashbox",
                "Failed to open cashbox: " + error.message,
                CONSOLE_COLOR,
                [error]
            );
        }
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
                message = _t("The printer is not connected or not powered on");
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
